#!/usr/bin/env python3
"""
리니지2 공식 홈페이지 전체 공지 크롤러
대상: 본서버 / 각성서버 / L2노트
저장 위치: notices/ 폴더
"""

import asyncio
import json
import random
import re
from datetime import datetime
from pathlib import Path

from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError


# ── 설정 ─────────────────────────────────────────────────────────────────────
BASE_URL = "https://lineage2.plaync.com"

NOTICES_DIR = Path("notices")

BOARDS = [
    {
        "name":        "본서버",
        "url":         "https://lineage2.plaync.com/board/l2notice/list",
        "board_id":    "l2notice",
        "output_file": NOTICES_DIR / "l2_notices_본서버.txt",
    },
    {
        "name":        "각성서버",
        "url":         "https://lineage2.plaync.com/board/l2awknnotice/list",
        "board_id":    "l2awknnotice",
        "output_file": NOTICES_DIR / "l2_notices_각성서버.txt",
    },
    {
        "name":        "L2노트",
        "url":         "https://lineage2.plaync.com/board/l2note/list",
        "board_id":    "l2note",
        "output_file": NOTICES_DIR / "l2_notices_l2note.txt",
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


def prepend_to_file(filepath: Path, text: str) -> None:
    filepath.parent.mkdir(exist_ok=True)
    existing = ""
    if filepath.exists():
        with open(filepath, "r", encoding="utf-8") as f:
            existing = f.read()
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(text + existing)


async def delay(lo: float = 1.0, hi: float = 2.0) -> None:
    await asyncio.sleep(random.uniform(lo, hi))


# ── 목록 수집 ─────────────────────────────────────────────────────────────────
async def collect_article_links(page, board_url: str, board_id: str, known_ids: set) -> list[dict]:
    results = []
    page_num = 1

    while True:
        list_url = board_url if page_num == 1 else f"{board_url}?page={page_num}"
        print(f"  📄 목록 {page_num}페이지 로딩: {list_url}")

        try:
            await page.goto(list_url, wait_until="networkidle", timeout=30_000)
        except PlaywrightTimeoutError:
            print(f"  ⚠️  {page_num}페이지 타임아웃 — 목록 수집 중단")
            break

        await page.wait_for_timeout(2_000)

        rows = []
        for sel in LIST_ROW_SELECTORS:
            rows = await page.query_selector_all(sel)
            if rows:
                break

        if not rows:
            links = await page.query_selector_all(f"a[href*='/{board_id}/view']")
            if not links:
                links = await page.query_selector_all(f"a[href*='/{board_id}/']")

            found_known = False
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
                results.append({"title": title, "date": "", "url": full_url, "article_id": aid})

            if found_known or not links:
                break
        else:
            found_known = False
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
                results.append({"title": title, "date": date, "url": full_url, "article_id": aid})

            if found_known:
                print("  🔵 기존 공지 발견 — 수집 중단")
                break

        print(f"  ✅ {page_num}페이지 완료 (누적 {len(results)}개)")

        has_next = await _has_next_page(page, page_num)
        if not has_next:
            print("  🏁 마지막 페이지 도달")
            break

        page_num += 1
        await delay(1.0, 2.0)

    return results


async def _has_next_page(page, current: int) -> bool:
    selectors = [
        ".paging .next:not(.disabled):not([aria-disabled='true'])",
        ".pagination .next:not(.disabled)",
        ".btn-next:not(:disabled)",
        ".page-next:not(.disabled)",
        f"a[href*='page={current + 1}']",
        f".paging a[data-page='{current + 1}']",
        f"button[data-page='{current + 1}']",
    ]
    for sel in selectors:
        el = await page.query_selector(sel)
        if el:
            return True
    return False


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

    try:
        articles = await collect_article_links(page, board["url"], board_id, known_ids)

        if not articles:
            print(f"  [{name}] 새 공지 없음")
            return 0

        print(f"\n  [{name}] 새 공지 {len(articles)}건 본문 수집 시작")
        new_blocks: list[str] = []

        for idx, art in enumerate(articles, 1):
            print(f"  [{name}] {idx}/{len(articles)} — {art['title'][:45]}...")
            content = await fetch_content(page, art["url"])

            new_blocks.append(format_notice(
                title=art["title"],
                date=art["date"],
                server=name,
                url=art["url"],
                content=content,
            ))

            crawled_ids.setdefault(board_id, [])
            if art["article_id"] not in crawled_ids[board_id]:
                crawled_ids[board_id].append(art["article_id"])

            await delay(1.0, 2.0)

        prepend_to_file(out_file, "".join(new_blocks))
        print(f"  [{name}] ✅ {len(new_blocks)}건 저장 → {out_file}")
        return len(new_blocks)

    finally:
        await page.close()


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
