#!/usr/bin/env python3
"""
리니지2 공식 홈페이지 공지 크롤러 (REST API 직접 호출 방식)
- Playwright 불필요: api-community.plaync.com REST API 사용
- 게시판 페이지네이션은 ?page=N 아닌 cursor 기반 (previousArticleId)
- 본서버:   GET /lin2/board/{boardId}/article (첫 배치)
            GET /lin2/board/{boardId}/article/search/moreArticle (이후 배치)
- 각성서버: 동일하나 game prefix가 lin2_awkn (HTML boardConfig.apiPath에서 확인)
"""

import json
import re
import subprocess
import sys
import time
import urllib.request
import urllib.parse
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

sys.stdout.reconfigure(errors='replace')


# ── 설정 ─────────────────────────────────────────────────────────────────────
_API_COMMUNITY = "https://api-community.plaync.com/"
BOARD_URL_PATTERN = "https://lineage2.plaync.com/board/{board_alias}/view?articleId={article_id}"

NOTICES_DIR = Path("notices")

BOARDS = [
    {
        "name":        "본서버",
        "board_id":    "l2update",
        "api_base":    _API_COMMUNITY + "lin2/",
        "output_file": NOTICES_DIR / "l2_notices_본서버.txt",
    },
    {
        "name":        "각성서버",
        "board_id":    "l2awknupdate",
        "api_base":    _API_COMMUNITY + "lin2_awkn/",   # lin2_awkn: 각성서버 게임 prefix
        "output_file": NOTICES_DIR / "l2_notices_각성서버.txt",
    },
]

CRAWLED_IDS_FILE = NOTICES_DIR / "crawled_ids.json"

BATCH_SIZE = 15          # 한 번에 가져올 기사 수
MAX_CONSECUTIVE_KNOWN = 5  # 연속 N배치 신규 0건이면 수집 완료로 판단
PUSH_INTERVAL = 50       # N배치마다 git push


# ── HTTP ─────────────────────────────────────────────────────────────────────
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Content-Type": "application/json",
    "Accept-Language": "ko-KR,ko;q=0.9",
    "Referer": "https://lineage2.plaync.com/",
    "Origin": "https://lineage2.plaync.com",
}


def _get(url: str, params: dict | None = None) -> dict:
    if params:
        url = url + "?" + urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
    req = urllib.request.Request(url, headers=_HEADERS)
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8", errors="replace"))


# ── HTML → 텍스트 변환 ────────────────────────────────────────────────────────
class _TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self._parts: list[str] = []

    def handle_data(self, data: str) -> None:
        text = data.strip()
        if text:
            self._parts.append(text)

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag in ("br", "p", "div", "li", "h1", "h2", "h3", "h4", "tr"):
            self._parts.append("\n")

    def get_text(self) -> str:
        return re.sub(r"\n{3,}", "\n\n", "\n".join(self._parts)).strip()


def html_to_text(html: str) -> str:
    parser = _TextExtractor()
    parser.feed(html)
    return parser.get_text()


# ── 상태 관리 ──────────────────────────────────────────────────────────────────
def load_crawled_ids() -> dict:
    if CRAWLED_IDS_FILE.exists():
        with open(CRAWLED_IDS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_crawled_ids(data: dict) -> None:
    NOTICES_DIR.mkdir(exist_ok=True)
    with open(CRAWLED_IDS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ── Git ───────────────────────────────────────────────────────────────────────
def git_push_checkpoint(message: str) -> None:
    print(f"  [Git] push 시도: {message}")
    try:
        files = [str(CRAWLED_IDS_FILE)] + [str(b["output_file"]) for b in BOARDS]
        subprocess.run(["git", "add"] + files, check=True, timeout=30)
        result = subprocess.run(
            ["git", "commit", "-m", message],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode != 0 and "nothing to commit" in (result.stdout + result.stderr):
            print("  [Git] 변경사항 없음 - push 생략")
            return
        result.check_returncode()
        subprocess.run(["git", "push"], check=True, timeout=60)
        print(f"  [Git] push 완료: {message}")
    except subprocess.CalledProcessError as e:
        print(f"  [Git] push 실패 (무시): {e}")
    except subprocess.TimeoutExpired:
        print("  [Git] push 타임아웃 (무시)")


# ── 유틸 ─────────────────────────────────────────────────────────────────────
def classify_server(board_name: str, title: str) -> str:
    if board_name == "각성서버":
        return "각성서버"
    if "[말하는섬]" in title:
        return "말하는섬"
    return "본서버"


def format_notice(title: str, date: str, server: str, url: str, content: str) -> str:
    return (
        "================\n"
        f"제목: {title}\n"
        f"날짜: {date}\n"
        f"서버: {server}\n"
        f"URL: {url}\n"
        "내용:\n"
        f"{content}\n"
        "================\n\n"
    )


def parse_date(timestamps: dict) -> str:
    for key in ("postedAt", "publishedAt", "postDateTime"):
        val = timestamps.get(key, "")
        if val:
            m = re.match(r"(\d{4})-(\d{2})-(\d{2})", val)
            if m:
                return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    return ""


# ── API 래퍼 ──────────────────────────────────────────────────────────────────
def fetch_article_list(api_base: str, board_id: str, cursor: str | None) -> dict:
    """기사 목록 한 배치 가져오기 (cursor=None이면 최신부터)."""
    if cursor is None:
        return _get(f"{api_base}board/{board_id}/article")
    return _get(
        f"{api_base}board/{board_id}/article/search/moreArticle",
        params={
            "moreDirection": "BEFORE",
            "previousArticleId": cursor,
            "moreSize": BATCH_SIZE,
        },
    )


def fetch_article_content(api_base: str, board_id: str, article_id: str) -> str:
    """기사 본문 HTML을 텍스트로 변환하여 반환."""
    try:
        data = _get(f"{api_base}board/{board_id}/article/{article_id}")
        html = data.get("article", {}).get("content", {}).get("content", "")
        return html_to_text(html) if html else "[본문 없음]"
    except Exception as e:
        return f"[본문 로드 실패: {e}]"


# ── 공통 저장 헬퍼 ───────────────────────────────────────────────────────────
def _save_articles(
    items: list,
    api_base: str,
    board_id: str,
    board_name: str,
    out_file,
    known_ids: set,
    crawled_ids: dict,
) -> int:
    """신규 기사만 파일에 추가하고 known_ids/crawled_ids 갱신. 저장 건수 반환."""
    new_articles = [it for it in items if it.get("id") not in known_ids]
    if not new_articles:
        return 0

    out_file.parent.mkdir(exist_ok=True)
    with open(out_file, "a", encoding="utf-8") as f:
        for idx, item in enumerate(new_articles, 1):
            article_id = item.get("id", "")
            title = item.get("title", "")
            date = parse_date(item.get("timestamps", {}))
            url = BOARD_URL_PATTERN.format(board_alias=board_id, article_id=article_id)
            server = classify_server(board_name, title)

            print(f"    [{idx}/{len(new_articles)}] {title[:50]}")
            content = fetch_article_content(api_base, board_id, article_id)
            f.write(format_notice(title, date, server, url, content))

            crawled_ids.setdefault(board_id, [])
            if article_id not in crawled_ids[board_id]:
                crawled_ids[board_id].append(article_id)
            known_ids.add(article_id)
            save_crawled_ids(crawled_ids)
            time.sleep(0.5)

    return len(new_articles)


# ── 메인 크롤러 ───────────────────────────────────────────────────────────────
def crawl_board(board: dict, crawled_ids: dict) -> int:
    """
    한 게시판을 cursor 기반으로 크롤링.

    상태 (crawled_ids.json):
      {board_id}_cursor   : 이어서 수집할 가장 오래된 기사 ID (None = 전체 완료)
      {board_id}_complete : 전체 이력 수집 완료 여부

    두 페이즈:
      Phase 1 (항상 실행): 최신부터 스캔 → 새 공지 포착.
                           MAX_CONSECUTIVE_KNOWN 배치 연속 신규 0건이면 종료.
      Phase 2 (미완료 시): 저장된 cursor부터 과거로 이어서 수집.
    """
    name = board["name"]
    board_id = board["board_id"]
    api_base = board["api_base"]
    out_file = board["output_file"]
    cursor_key = f"{board_id}_cursor"
    complete_key = f"{board_id}_complete"

    print(f"\n{'=' * 55}")
    print(f"  [{name}] 크롤링 시작")
    print(f"{'=' * 55}")

    known_ids: set = set(crawled_ids.get(board_id, []))
    bulk_cursor: str | None = crawled_ids.get(cursor_key)
    is_complete: bool = crawled_ids.get(complete_key, False)

    print(f"  기존 수집 ID: {len(known_ids)}개, cursor: {bulk_cursor}, complete: {is_complete}")

    total_new = 0
    batches_since_push = 0

    # ── Phase 1: 최신 공지 확인 (항상 실행) ──────────────────────────────────
    # complete 여부와 무관하게 매 실행마다 상단부터 스캔해 새 공지를 포착한다.
    print(f"\n  [Phase 1] 최신 공지 확인")
    p1_cursor: str | None = None
    p1_consecutive_known = 0

    while p1_consecutive_known < MAX_CONSECUTIVE_KNOWN:
        try:
            data = fetch_article_list(api_base, board_id, p1_cursor)
        except Exception as e:
            print(f"  [오류] 목록 로드 실패: {e}")
            break

        items = data.get("contentList", [])
        has_more = data.get("hasMore", False)

        if not items:
            print("  Phase 1: 빈 배치 - 전체 수집 완료")
            is_complete = True
            crawled_ids[cursor_key] = None
            crawled_ids[complete_key] = True
            save_crawled_ids(crawled_ids)
            break

        saved = _save_articles(items, api_base, board_id, name, out_file, known_ids, crawled_ids)
        print(f"  Phase 1 cursor={str(p1_cursor)[:16] if p1_cursor else 'None'}: "
              f"{len(items)}건 / 신규 {saved}건")

        if saved:
            p1_consecutive_known = 0
            total_new += saved
        else:
            p1_consecutive_known += 1

        p1_cursor = items[-1].get("id")

        if not has_more:
            print("  Phase 1: hasMore=False - 전체 수집 완료")
            is_complete = True
            crawled_ids[cursor_key] = None
            crawled_ids[complete_key] = True
            save_crawled_ids(crawled_ids)
            break

        time.sleep(0.3)

    if total_new > 0:
        git_push_checkpoint(f"crawler: [{name}] Phase1 완료 ({total_new}건)")
        batches_since_push = 0

    # ── Phase 2: 과거 이력 이어서 수집 (미완료 시) ───────────────────────────
    if not is_complete:
        print(f"\n  [Phase 2] 과거 이력 수집 (cursor: {str(bulk_cursor)[:20] if bulk_cursor else 'None'})")
        cursor = bulk_cursor
        p2_consecutive_known = 0
        p2_new = 0

        while True:
            try:
                data = fetch_article_list(api_base, board_id, cursor)
            except Exception as e:
                print(f"  [오류] 목록 로드 실패: {e}")
                break

            items = data.get("contentList", [])
            has_more = data.get("hasMore", False)

            if not items:
                print("  Phase 2: 빈 배치 - 전체 수집 완료")
                is_complete = True
                crawled_ids[cursor_key] = None
                crawled_ids[complete_key] = True
                save_crawled_ids(crawled_ids)
                break

            saved = _save_articles(items, api_base, board_id, name, out_file, known_ids, crawled_ids)
            print(f"  Phase 2 cursor={str(cursor)[:16] if cursor else 'None'}: "
                  f"{len(items)}건 / 신규 {saved}건 / hasMore={has_more}")

            if saved:
                p2_consecutive_known = 0
                p2_new += saved
                total_new += saved
            else:
                p2_consecutive_known += 1

            cursor = items[-1].get("id")
            crawled_ids[cursor_key] = cursor
            save_crawled_ids(crawled_ids)

            batches_since_push += 1
            if batches_since_push >= PUSH_INTERVAL:
                git_push_checkpoint(f"crawler: [{name}] Phase2 배치 완료 (총 {total_new}건)")
                batches_since_push = 0

            if not has_more:
                print("  Phase 2: hasMore=False - 전체 수집 완료")
                is_complete = True
                crawled_ids[cursor_key] = None
                crawled_ids[complete_key] = True
                save_crawled_ids(crawled_ids)
                break

            if p2_consecutive_known >= MAX_CONSECUTIVE_KNOWN:
                print(f"  {MAX_CONSECUTIVE_KNOWN}배치 연속 신규 0건 - cursor 저장 후 대기")
                break

            time.sleep(0.5)

        if p2_new > 0 and batches_since_push > 0:
            git_push_checkpoint(f"crawler: [{name}] Phase2 완료 ({p2_new}건)")

    print(f"\n  [{name}] 완료: 총 {total_new}건 저장")
    return total_new


def main() -> None:
    NOTICES_DIR.mkdir(exist_ok=True)
    crawled_ids = load_crawled_ids()
    total = 0

    print("=" * 55)
    print("  리니지2 공지 크롤러 (REST API 방식)")
    print(f"  시작: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 55)

    for board in BOARDS:
        count = crawl_board(board, crawled_ids)
        total += count
        time.sleep(1.0)

    save_crawled_ids(crawled_ids)

    print(f"\n{'=' * 55}")
    print(f"  크롤링 완료! 총 새 공지: {total}건")
    print(f"  완료: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 55)


if __name__ == "__main__":
    main()
