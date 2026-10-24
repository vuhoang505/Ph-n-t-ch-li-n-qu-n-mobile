"""Thu thập tên/mô tả kỹ năng công khai từ hồ sơ tướng Garena.

Có cache tiếp tục, nghỉ giữa các request và không truy cập endpoint ẩn.
Không suy luận hoặc ghi dữ liệu chiến thuật trong bước thu thập.
"""
from __future__ import annotations

import hashlib
import html
import json
import re
import time
import argparse
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ROSTER_FILE = ROOT / "data" / "imports" / "official_roster.json"
OUTPUT_FILE = ROOT / "data" / "imports" / "official_hero_details.json"
USER_AGENT = "AOV-Strategy-AI/0.2 official-data-sync"


def clean_html(value: str) -> str:
    value = re.sub(r"<br\s*/?>", "\n", value, flags=re.I)
    value = re.sub(r"<[^>]+>", " ", value)
    return " ".join(html.unescape(value).replace("\xa0", " ").split())


def parse_skills(document: str) -> list[dict]:
    section = re.search(r'<section class="hero__skills">(?P<body>.*?)</section>', document, re.S)
    if not section:
        return []
    pattern = re.compile(
        r'<div class="hero__skills--detail[^"\n]*" id="heroSkill-(?P<order>\d+)">\s*'
        r'<h3>(?P<name>.*?)</h3>\s*<article>(?P<description>.*?)</article>',
        re.S,
    )
    skills = []
    for match in pattern.finditer(section.group("body")):
        description = clean_html(match.group("description"))
        skills.append({
            "order": int(match.group("order")),
            "name": clean_html(match.group("name")),
            "description": description,
            "skill_type": "passive" if description.casefold().startswith("nội tại") else "active",
        })
    return skills


def fetch(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return response.read().decode("utf-8")
        except (urllib.error.URLError, TimeoutError) as exc:
            last_error = exc
            time.sleep(1.0 + attempt)
    raise RuntimeError(f"Cannot fetch {url}: {last_error}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Dong bo mo ta ky nang tu ho so tuong Garena cong khai.")
    parser.add_argument("--force", action="store_true", help="Tai lai tat ca ho so thay vi dung cache.")
    args = parser.parse_args()
    roster = json.loads(ROSTER_FILE.read_text(encoding="utf-8"))["heroes"]
    cached = {}
    if OUTPUT_FILE.exists():
        cached_payload = json.loads(OUTPUT_FILE.read_text(encoding="utf-8"))
        cached = {row["slug"]: row for row in cached_payload.get("heroes", [])}
    results = []
    failures = []
    for index, hero in enumerate(roster, start=1):
        existing = cached.get(hero["slug"])
        if existing and existing.get("skills") and not args.force:
            results.append(existing)
            continue
        try:
            document = fetch(hero["profile_url"])
            skills = parse_skills(document)
            record = {
                "slug": hero["slug"],
                "name": hero["name"],
                "source_url": hero["profile_url"],
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "content_hash": hashlib.sha256(document.encode("utf-8")).hexdigest(),
                "skills": skills,
                "data_status": "official_skills" if skills else "official_profile_without_skills",
            }
            if not skills and existing and existing.get("skills"):
                results.append(existing)
                failures.append({"slug": hero["slug"], "reason": "no_skill_section_kept_cache"})
            else:
                results.append(record)
                if not skills:
                    failures.append({"slug": hero["slug"], "reason": "no_skill_section"})
        except Exception as exc:  # tiếp tục để báo cáo tướng lỗi, không che giấu
            failures.append({"slug": hero["slug"], "reason": str(exc)})
            if existing and existing.get("skills"):
                results.append(existing)
            else:
                results.append({
                    "slug": hero["slug"], "name": hero["name"], "source_url": hero["profile_url"],
                    "fetched_at": datetime.now(timezone.utc).isoformat(), "content_hash": None,
                    "skills": [], "data_status": "fetch_failed",
                })
        if index % 10 == 0:
            print(f"Fetched {index}/{len(roster)} profiles", flush=True)
        time.sleep(0.15)
    payload = {
        "source": "Garena Liên Quân Mobile - Học viện/Tướng",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "heroes": sorted(results, key=lambda row: row["name"]),
        "failures": failures,
    }
    OUTPUT_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Saved {len(results)} profiles; failures={len(failures)}", flush=True)


if __name__ == "__main__":
    main()
