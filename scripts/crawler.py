#!/usr/bin/env python3
"""
리니지2 공식 홈페이지 공지 크롤러
대상: 본서버 / 각성서버 (말하는섬은 본서버 게시판에서 제목으로 분류)
저장 위치: notices/ 폴더
"""

import asyncio
import json
import random
import re
import subprocess
from datetime import datetime
from pathlib import Path

from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError


# ── 설정 ─────────────────────────────────────────────────────────────────────
BASE_URL = "https://lineage2.plaync.com"

NOTICES_DIR = Path("notices")

BOARDS = [
    {
        "name":        "본서버",
        "url":         "https://lineage2.plaync.com/board/l2update/list",
        "board_id":    "l2update",
        "output_file": NOTICES_DIR / "l2_notices_본서버.txt",
    },
    {
        "name":        "각성서버",
        "url":         "https://lineage2.plaync.com/board/l2awknupdate/list",
        "board_id":    "l2awknupdate",
        "output_file": NOTICES_DIR / "l2_notices_각성서버.txt",
    },
]

CRAWLED_IDS_FILE = NOTICES_DIR / "crawled_ids.json"

LIST_ROW_SELECTORS = [
    ".board-list tbody tr",
    "table.board-list tr",
    ".list-wrap li",
    ".notice-list li",
    ".article-list li",
    ".post-list .post-item",
    "ul.list li",
]

TITLE_SELECTORS = [
    ".title",
    ".subject",
    "td.title",
    ".post-title",
    ".article-title",
    "a",
]

DATE_SELECTORS = [
    ".date",
    ".reg-date",
    "td.date",
    "time",
    ".created",
    ".post-date",
]

CONTENT_SELECTORS = [
    ".view-content",
    ".article-content",
    ".post-content",
    ".board-content",
    ".content-area",
    "#articleContent",
    ".article-body",
    ".view-body",
    ".ql-editor",
    ".note-editable",
    "[class*='view'][class*='content']",
    "[class*='article'][class*='content']",
    "article",
    "main",
]

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)


# ── 유틸리티 ──────────────────────────────────────────────────────────────────
def load_crawled_ids() -> dict:
    if CRAWLED_IDS_FILE.exists():
        with open(CRAWLED_IDS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_crawled_ids(data: dict) -> None:
    NOTICES_DIR.mkdir(exist_ok=True)
    with open(CRAWLED_IDS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def git_push_checkpoint(message: str) -> None:
    """crawled_ids.json + 공지 텍스트 파일을 git add/commit/push — Actions 타임아웃 시 진행상황 보존."""
    print(f"  🚀 Git push 시도: {message}")
    try:
        files_to_add = [str(CRAWLED_IDS_FILE)] + [str(b["output_file"]) for b in BOARDS]
        subprocess.run(["git", "add"] + files_to_add, check=True, timeout=30)
        result = subprocess.run(
            ["git", "commit", "-m", message],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode != 0 and "nothing to commit" in (result.stdout + result.stderr):
            print("  ℹ️  커밋할 변경사항 없음 — push 생략")
            return
        result.check_returncode()
        subprocess.run(["git", "push"], check=True, timeout=60)
        print(f"  ✅ Git push 완료: {message}")
    except subprocess.CalledProcessError as e:
        print(f"  ⚠️  Git push 실패 (무시): {e}")
    except subprocess.TimeoutExpired:
        print("  ⚠️  Git push 타임아웃 (무시)")


def extract_article_id(href: str) -> str | None:
    patterns = [
        r"articleId=(\d+)",
        r"/view/(\d+)",
        r"article[_-]?[Ii]d=(\d+)",
        r"[?&]id=(\d+)",
    ]
    for p in patterns:
        m = re.search(p, href)
        if m:
            return m.group(1)
    return None


def classify_server(board_name: str, title: str) -> str:
    if board_name == "각성서버":
        return "각성서버"
    if "[말하는섬]" in title:
        return "말하는섬"
    return "본서버"


def extract_date_from_text(text: str) -> str:
    m = re.search(r'(\d{4})년\s*(\d{1,2})월\s*(\d{1,2})일', text)
    if m:
        return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
    return ""


def extract_date_from_title(title: str) -> str:
    m = re.search(r'(\d{1,2})월\s*(\d{1,2})일', title)
    if m:
        year = datetime.now().year
        return f"{year}-{int(m.group(1)):02d}-{int(m.group(2)):02d}"
    return ""


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


async def delay(lo: float = 1.0, hi: float = 2.0) -> None:
    await asyncio.sleep(random.uniform(lo, hi))


# ── 단일 목록 페이지 수집 ──────────────────────────────────────────────────────
async def collect_one_page(
    page, board_url: str, board_id: str, page_num: int, known_ids: set
) -> tuple[list[dict], bool]:
    """
    목록 한 페이지에서 새 공지 링크를 추출한다.
    반환: (articles, has_known)
      - articles: 이 페이지의 신규 공지 목록 (known_ids에 없는 것)
      - has_known: 이미 크롤링한 ID가 하나라도 있으면 True
        → articles=[], has_known=False 이면 진짜 빈 페이지 (게시판 끝)
    """
    list_url = board_url if page_num == 1 else f"{board_url}?page={page_num}"
    print(f"  📄 목록 {page_num}페이지 로딩: {list_url}")

    try:
        await page.goto(list_url, wait_until="networkidle", timeout=30_000)
    except PlaywrightTimeoutError:
        print(f"  ⚠️  {page_num}페이지 타임아웃 — 목록 수집 중단")
        return [], False

    await page.wait_for_timeout(2_000)

    rows = []
    for sel in LIST_ROW_SELECTORS:
        rows = await page.query_selector_all(sel)
        if rows:
            break

    articles: list[dict] = []
    found_known = False

    if not rows:
        links = await page.query_selector_all(f"a[href*='/{board_id}/view']")
        if not links:
            links = await page.query_selector_all(f"a[href*='/{board_id}/']")

        for a in links:
            href = await a.get_attribute("href") or ""
            aid = extract_article_id(href)
            if not aid:
                continue
            if aid in known_ids:
                found_known = True
                continue
            title = (await a.inner_text()).strip()
            full_url = (BASE_URL + href) if href.startswith("/") else href
            articles.append({"title": title, "date": "", "url": full_url, "article_id": aid})
    else:
        for row in rows:
            a_tag = await row.query_selector(f"a[href*='/{board_id}/']")
            if not a_tag:
                a_tag = await row.query_selector("a")
            if not a_tag:
                continue

            href = await a_tag.get_attribute("href") or ""
            aid = extract_article_id(href)
            if not aid:
                continue

            if aid in known_ids:
                found_known = True
                continue

            title = ""
            for tsel in TITLE_SELECTORS:
                t_el = await row.query_selector(tsel)
                if t_el:
                    title = (await t_el.inner_text()).strip()
                    if title:
                        break
            if not title:
                title = (await a_tag.inner_text()).strip()

            date = ""
            for dsel in DATE_SELECTORS:
                d_el = await row.query_selector(dsel)
                if d_el:
                    date = (await d_el.inner_text()).strip()
                    if date:
                        break

            full_url = (BASE_URL + href) if href.startswith("/") else href
            articles.append({"title": title, "date": date, "url": full_url, "article_id": aid})

    return articles, found_known


# ── 본문 수집 ─────────────────────────────────────────────────────────────────
async def fetch_content(page, url: str) -> str:
    try:
        await page.goto(url, wait_until="networkidle", timeout=30_000)
        await page.wait_for_timeout(2_000)
    except PlaywrightTimeoutError:
        return "[로드 타임아웃]"
    except Exception as e:
        return f"[로드 오류: {e}]"

    for sel in CONTENT_SELECTORS:
        el = await page.query_selector(sel)
        if el:
            text = (await el.inner_text()).strip()
            if text:
                return text

    body = await page.query_selector("body")
    if body:
        return (await body.inner_text()).strip()
    return "[본문 추출 실패]"


# ── 메인 ─────────────────────────────────────────────────────────────────────
async def crawl_board(context, board: dict, crawled_ids: dict) -> int:
    """p1부터 끝까지 순서대로 긁되, 이미 수집한 ID는 건너뜀. 200페이지마다 push."""
    name = board["name"]
    board_id = board["board_id"]
    out_file = board["output_file"]

    print(f"\n{'='*55}")
    print(f"  [{name}] 크롤링 시작")
    print(f"{'='*55}")

    known_ids: set = set(crawled_ids.get(board_id, []))
    page = await context.new_page()
    await page.add_init_script(
        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    )

    PUSH_INTERVAL = 200
    total_new = 0
    pages_since_push = 0

    try:
        page_num = 1
        while True:
            articles, has_known = await collect_one_page(
                page, board["url"], board_id, page_num, known_ids
            )

            if not articles and not has_known:
                print("  🏁 빈 페이지 — 게시판 끝")
                break

            if articles:
                print(f"  [{name}] p{page_num} — {len(articles)}건 본문 수집")
                out_file.parent.mkdir(exist_ok=True)
                with open(out_file, "a", encoding="utf-8") as f:
                    for idx, art in enumerate(articles, 1):
                        print(f"  [{name}] p{page_num} {idx}/{len(articles)} — {art['title'][:45]}...")
                        content = await fetch_content(page, art["url"])

                        date = art["date"]
                        if not date:
                            date = extract_date_from_text(content)
                        if not date:
                            date = extract_date_from_title(art["title"])

                        f.write(format_notice(
                            title=art["title"],
                            date=date,
                            server=classify_server(name, art["title"]),
                            url=art["url"],
                            content=content,
                        ))

                        crawled_ids.setdefault(board_id, [])
                        if art["article_id"] not in crawled_ids[board_id]:
                            crawled_ids[board_id].append(art["article_id"])
                        known_ids.add(art["article_id"])
                        total_new += 1
                        await delay(1.0, 2.0)

                save_crawled_ids(crawled_ids)
                print(f"  [{name}] 💾 p{page_num} 저장 완료 (총 {total_new}건)")

            pages_since_push += 1
            if pages_since_push >= PUSH_INTERVAL:
                git_push_checkpoint(f"crawler: [{name}] p{page_num} 완료 (총 {total_new}건)")
                pages_since_push = 0

            page_num += 1
            await delay(1.0, 2.0)

        if total_new > 0 and pages_since_push > 0:
            git_push_checkpoint(f"crawler: [{name}] 완료 (총 {total_new}건)")

    finally:
        await page.close()

    print(f"  [{name}] ✅ {total_new}건 저장 → {out_file}")
    return total_new


async def main() -> None:
    NOTICES_DIR.mkdir(exist_ok=True)
    crawled_ids = load_crawled_ids()
    total = 0

    print("=" * 55)
    print("  리니지2 공지 크롤러")
    print(f"  시작: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 55)

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-blink-features=AutomationControlled"],
        )
        context = await browser.new_context(
            user_agent=USER_AGENT,
            locale="ko-KR",
            extra_http_headers={"Accept-Language": "ko-KR,ko;q=0.9"},
        )

        try:
            for board in BOARDS:
                count = await crawl_board(context, board, crawled_ids)
                total += count
                await delay(2.0, 3.5)
        finally:
            await context.close()
            await browser.close()

    save_crawled_ids(crawled_ids)

    print(f"\n{'='*55}")
    print(f"  크롤링 완료! 총 새 공지: {total}건")
    print(f"  완료: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 55)


if __name__ == "__main__":
    asyncio.run(main())
