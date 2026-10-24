"""Đồng bộ roster và ảnh tướng từ trang Học viện Liên Quân chính thức.

Script chỉ lấy tên, slug, vai trò và URL ảnh công khai. Nó không tạo chỉ số
chiến thuật hay thống kê meta. Chạy từ thư mục gốc dự án.
"""
from __future__ import annotations

import html
import json
import re
import unicodedata
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


SOURCE_URL = "https://lienquan.garena.vn/hoc-vien/"
OUTPUT = Path(__file__).resolve().parents[1] / "data" / "imports" / "official_roster.json"
ROLE_MAP = {
    "28": "Đấu sĩ",
    "29": "Pháp sư",
    "30": "Trợ thủ",
    "31": "Đỡ đòn",
    "32": "Sát thủ",
    "33": "Xạ thủ",
}
POSITION_MAP = {
    "Đấu sĩ": ["Caesar"],
    "Pháp sư": ["Giữa"],
    "Trợ thủ": ["Trợ thủ"],
    "Đỡ đòn": ["Trợ thủ", "Caesar"],
    "Sát thủ": ["Rừng"],
    "Xạ thủ": ["Rồng"],
}


def slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", normalized.lower()).strip("-")


def parse_roster(document: str) -> list[dict]:
    pattern = re.compile(
        r'<a\s+href="(?P<href>[^"]+/tuong-skin/d/(?P<url_slug>[^/]+)/)"'
        r'[^>]*class="st-heroes__item"[^>]*data-keyword="(?P<keyword>[^"]*)"'
        r'[^>]*data-type="(?P<types>[^"]*)"[^>]*>.*?'
        r'<img\s+src="(?P<image>[^"]+)"\s+alt="(?P<name>[^"]+)"',
        re.DOTALL,
    )
    heroes: dict[str, dict] = {}
    for match in pattern.finditer(document):
        name = html.unescape(match.group("name")).strip()
        slug = match.group("url_slug").strip() or slugify(name)
        role_ids = re.findall(r"\d+", match.group("types"))
        roles = [ROLE_MAP[value] for value in role_ids if value in ROLE_MAP]
        positions = list(dict.fromkeys(position for role in roles for position in POSITION_MAP[role]))
        # Trang chính thức có thể liệt kê nhiều biến thể của cùng một tướng
        # (ví dụ Flowborn). Database lưu một hồ sơ chiến thuật trên mỗi tên.
        heroes.setdefault(name.casefold(), {
            "slug": slug,
            "name": name,
            "image_url": html.unescape(match.group("image")),
            "profile_url": html.unescape(match.group("href")),
            "roles": roles,
            "positions_inferred_from_roles": positions,
        })
    return sorted(heroes.values(), key=lambda row: row["name"])


def main() -> None:
    request = urllib.request.Request(SOURCE_URL, headers={"User-Agent": "AOV-Strategy-AI/0.1 data-sync"})
    with urllib.request.urlopen(request, timeout=30) as response:
        document = response.read().decode("utf-8")
    roster = parse_roster(document)
    if len(roster) < 100:
        raise RuntimeError(f"Nguồn chỉ trả về {len(roster)} tướng; dừng để tránh ghi dữ liệu thiếu.")
    payload = {
        "source": {
            "name": "Học viện Liên Quân Mobile - danh sách tướng chính thức",
            "url": SOURCE_URL,
            "source_type": "official_roster",
            "verified": True,
            "retrieved_at": datetime.now(timezone.utc).isoformat(),
        },
        "scope": "Tên, vai trò, ảnh và liên kết hồ sơ; không gồm điểm chiến thuật hoặc tỷ lệ meta.",
        "heroes": roster,
    }
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Saved {len(roster)} heroes to {OUTPUT}")


if __name__ == "__main__":
    main()
