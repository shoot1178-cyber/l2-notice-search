#!/usr/bin/env python3
"""
notices/ 폴더의 모든 txt 파일을 파싱해 notices/index.json 생성
GitHub Actions 에서 크롤러 실행 후 이 스크립트를 실행한다.
"""

import json
import re
from datetime import datetime, timezone
from pathlib import Path


def parse_notice_file(filepath: Path) -> list[dict]:
    text = filepath.read_text(encoding="utf-8", errors="replace")
    sections = re.split(r"={4,}", text)
    notices = []

    for i, section in enumerate(sections):
        section = section.strip()
        if not section:
            continue

        title = ""
        date = ""
        server = ""
        url = ""
        content_lines: list[str] = []
        in_content = False

        for line in section.splitlines():
            if line.startswith("제목:"):
                title = line[3:].strip()
            elif line.startswith("날짜:"):
                date = line[3:].strip()
            elif line.startswith("서버:"):
                server = line[3:].strip()
            elif line.startswith("URL:"):
                url = line[4:].strip()
            elif line.startswith("내용:"):
                in_content = True
                rest = line[3:].strip()
                if rest:
                    content_lines.append(rest)
            elif in_content:
                content_lines.append(line)

        if not title:
            continue

        content = "\n".join(content_lines).strip()
        preview = (content[:200] + "...") if len(content) > 200 else content

        notices.append({
            "id": f"{filepath.stem}_{i}",
            "title": title,
            "date": date,
            "server": server or "본서버",
            "url": url,
            "content": content,
            "preview": preview,
        })

    return notices


def parse_date(d: str) -> datetime:
    for fmt in ["%Y.%m.%d", "%Y-%m-%d", "%Y/%m/%d"]:
        try:
            return datetime.strptime(d, fmt)
        except ValueError:
            pass
    return datetime.min


def main() -> None:
    notices_dir = Path("notices")
    notices_dir.mkdir(exist_ok=True)

    all_notices: list[dict] = []
    txt_files = sorted(notices_dir.glob("*.txt"))

    if not txt_files:
        print("⚠️  notices/ 폴더에 txt 파일이 없습니다.")
    else:
        for txt_file in txt_files:
            print(f"파싱: {txt_file.name}")
            notices = parse_notice_file(txt_file)
            all_notices.extend(notices)
            print(f"  → {len(notices)}건")

    # 날짜 내림차순 정렬 (최신 → 오래된)
    all_notices.sort(key=lambda n: parse_date(n["date"]), reverse=True)

    index = {
        "lastUpdated": datetime.now(timezone.utc).isoformat(),
        "total": len(all_notices),
        "notices": all_notices,
    }

    output = notices_dir / "index.json"
    output.write_text(
        json.dumps(index, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"\n✅ notices/index.json 생성 완료: {len(all_notices)}건")


if __name__ == "__main__":
    main()
