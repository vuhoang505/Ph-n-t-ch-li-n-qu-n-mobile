"""Cache Garena's public equipment, rune, talent and enchantment catalogs.

This collector stores source text and hashes only.  It deliberately does not
claim that any catalog entry is a recommended choice for a hero; that separate
derived step is performed by the backend and remains marked pending review.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import time
import unicodedata
import urllib.error
import urllib.request
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_FILE = ROOT / "data" / "imports" / "official_gameplay_catalog.json"
USER_AGENT = "AOV-Strategy-AI/0.3 official-catalog-sync"
SOURCE_URLS = {
    "equipment": "https://lienquan.garena.vn/hoc-vien/trang-bi/",
    "rune": "https://lienquan.garena.vn/hoc-vien/bang-ngoc/",
    "talent": "https://lienquan.garena.vn/hoc-vien/phu-tro/",
    "enchantment": "https://lienquan.garena.vn/hoc-vien/phu-hieu/",
}
ITEM_CATEGORIES = {"19": "Công", "20": "Phép", "21": "Thủ", "22": "Tốc độ", "23": "Đi rừng", "24": "Trợ thủ"}
ITEM_LEVELS = {"25": "Cấp 1", "26": "Cấp 2", "27": "Cấp 3"}
RUNE_CATEGORIES = {"13": "Đỏ", "14": "Xanh", "15": "Tím"}
RUNE_LEVELS = {"16": "Cấp I", "17": "Cấp II", "18": "Cấp III"}


def slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", normalized.casefold()).strip("-")


def clean(value: str) -> str:
    return " ".join(html.unescape(value).replace("\xa0", " ").split())


class CatalogCardParser(HTMLParser):
    """Small purpose-built parser for Garena's repeated catalog cards."""

    def __init__(self, item_class: str):
        super().__init__(convert_charrefs=True)
        self.item_class = item_class
        self.stack: list[tuple[str, set[str]]] = []
        self.current: dict | None = None
        self.items: list[dict] = []
        self.paragraph: list[str] | None = None

    def handle_starttag(self, tag: str, attrs_list: list[tuple[str, str | None]]) -> None:
        attrs = {key: value or "" for key, value in attrs_list}
        classes = set(attrs.get("class", "").split())
        if self.current is None and self.item_class in classes:
            self.current = {
                "html_id": attrs.get("id"), "data_keyword": attrs.get("data-keyword"),
                "data_type": attrs.get("data-type"), "data_level": attrs.get("data-level"),
                "name_parts": [], "title_parts": [], "head_parts": [], "article_parts": [],
                "paragraphs": [], "image_url": None,
            }
        self.stack.append((tag, classes))
        if not self.current:
            return
        if tag == "img" and attrs.get("src") and attrs.get("alt") and not self.current["image_url"]:
            self.current["image_url"] = html.unescape(attrs["src"])
        if tag == "p":
            self.paragraph = []

    def handle_data(self, data: str) -> None:
        if not self.current or not data.strip():
            return
        text = clean(data)
        classes = {item for _, values in self.stack for item in values}
        if any(value.endswith("__item--name") for value in classes):
            self.current["name_parts"].append(text)
        if any(value.endswith("__skill--title") for value in classes):
            self.current["title_parts"].append(text)
        if any(value.endswith("__skill--head") for value in classes):
            self.current["head_parts"].append(text)
        if any(tag == "article" for tag, _ in self.stack):
            self.current["article_parts"].append(text)
        if self.paragraph is not None:
            self.paragraph.append(text)

    def handle_endtag(self, tag: str) -> None:
        if not self.stack:
            return
        index = next((i for i in range(len(self.stack) - 1, -1, -1) if self.stack[i][0] == tag), len(self.stack) - 1)
        _, classes = self.stack[index]
        if tag == "p" and self.current and self.paragraph is not None:
            paragraph = clean(" ".join(self.paragraph))
            if paragraph:
                self.current["paragraphs"].append(paragraph)
            self.paragraph = None
        del self.stack[index:]
        if self.current and self.item_class in classes:
            row = self.current
            row["name"] = clean(" ".join(row.pop("name_parts")))
            row["title"] = clean(" ".join(row.pop("title_parts")))
            row["head"] = clean(" ".join(row.pop("head_parts")))
            row["article"] = clean(" ".join(row.pop("article_parts")))
            self.items.append(row)
            self.current = None
            self.paragraph = None


ATTRIBUTE_PATTERNS = {
    "magic_pierce": r"([+-]?\s*\d+(?:[.,]\d+)?)\s*%?\s*xuyên giáp phép",
    "armor_pierce": r"([+-]?\s*\d+(?:[.,]\d+)?)\s*%?\s*xuyên giáp(?! phép)",
    "physical_attack": r"([+-]?\s*\d+(?:[.,]\d+)?)\s*%?\s*công vật lý",
    "magic_power": r"([+-]?\s*\d+(?:[.,]\d+)?)\s*%?\s*công phép",
    "magic_defense": r"([+-]?\s*\d+(?:[.,]\d+)?)\s*%?\s*giáp phép",
    "armor": r"([+-]?\s*\d+(?:[.,]\d+)?)\s*%?\s*giáp(?! phép)",
    "max_health": r"([+-]?\s*\d+(?:[.,]\d+)?)\s*%?\s*máu tối đa",
    "attack_speed": r"([+-]?\s*\d+(?:[.,]\d+)?)\s*%\s*tốc đánh",
    "critical_chance": r"([+-]?\s*\d+(?:[.,]\d+)?)\s*%\s*(?:tỷ lệ )?chí mạng",
    "lifesteal": r"([+-]?\s*\d+(?:[.,]\d+)?)\s*%\s*hút máu",
    "movement_speed": r"([+-]?\s*\d+(?:[.,]\d+)?)\s*%?\s*tốc chạy",
    "cooldown_reduction": r"([+-]?\s*\d+(?:[.,]\d+)?)\s*%\s*giảm hồi chiêu",
}


def parse_attributes(description: str) -> dict[str, float]:
    # Only parse the leading explicit stat block.  Numbers in passive effects
    # are kept in source text but are not mislabelled as permanent attributes.
    base = re.split(r"\b(?:nội tại|kích hoạt|bị động)\b", description, maxsplit=1, flags=re.I)[0]
    values: dict[str, float] = {}
    for key, pattern in ATTRIBUTE_PATTERNS.items():
        match = re.search(pattern, base, re.I)
        if match:
            values[key] = float(match.group(1).replace(" ", "").replace(",", "."))
    return values


def _hash_entry(name: str, description: str, source_url: str) -> str:
    return hashlib.sha256(f"{name}\n{description}\n{source_url}".encode("utf-8")).hexdigest()


def parse_documents(documents: dict[str, str], fetched_at: str) -> dict:
    equipment_parser = CatalogCardParser("st-items__item")
    equipment_parser.feed(documents["equipment"])
    rune_parser = CatalogCardParser("st-runes__item")
    rune_parser.feed(documents["rune"])
    talent_parser = CatalogCardParser("st-extra-skills__item")
    talent_parser.feed(documents["talent"])
    family_parser = CatalogCardParser("st-badges__item")
    family_parser.feed(documents["enchantment"])
    enchantment_parser = CatalogCardParser("st-badges__skill")
    enchantment_parser.feed(documents["enchantment"])

    equipment = []
    for card in equipment_parser.items:
        name = card["name"]
        paragraphs = card["paragraphs"]
        cost_text = paragraphs[0] if paragraphs else ""
        description = "\n".join(paragraphs[1:]) if len(paragraphs) > 1 else card["article"]
        cost_match = re.search(r"\d+", cost_text.replace(".", ""))
        level_id = card["data_level"]
        category_id = card["data_type"]
        row = {
            "external_key": slugify(name), "slug": slugify(name), "name": name,
            "image_url": card["image_url"], "category_id": category_id,
            "category": ITEM_CATEGORIES.get(category_id, "Chưa phân loại"),
            "level_id": level_id, "level": ITEM_LEVELS.get(level_id, "Chưa xác định"),
            "cost": int(cost_match.group()) if cost_match else None,
            "description": description, "attributes": parse_attributes(description),
            "source_url": SOURCE_URLS["equipment"], "fetched_at": fetched_at,
        }
        row["content_hash"] = _hash_entry(name, description, row["source_url"])
        equipment.append(row)

    runes = []
    for card in rune_parser.items:
        name = card["name"]
        description = card["article"] or "\n".join(card["paragraphs"])
        row = {
            "external_key": slugify(name), "slug": slugify(name), "name": name,
            "image_url": card["image_url"], "category_id": card["data_type"],
            "category": RUNE_CATEGORIES.get(card["data_type"], "Chưa phân loại"),
            "level_id": card["data_level"], "level": RUNE_LEVELS.get(card["data_level"], "Chưa xác định"),
            "description": description, "attributes": parse_attributes(description),
            "source_url": SOURCE_URLS["rune"], "fetched_at": fetched_at,
        }
        row["content_hash"] = _hash_entry(name, description, row["source_url"])
        runes.append(row)

    talents = []
    for card in talent_parser.items:
        name = card["name"]
        description = "\n".join(card["paragraphs"]) or card["article"]
        row = {
            "external_key": slugify(name), "slug": slugify(name), "name": name,
            "image_url": card["image_url"], "category": "Phụ trợ", "level": None,
            "description": description, "attributes": {},
            "source_url": SOURCE_URLS["talent"], "fetched_at": fetched_at,
        }
        row["content_hash"] = _hash_entry(name, description, row["source_url"])
        talents.append(row)

    families = []
    for card in family_parser.items:
        name = card["name"]
        # The first two paragraphs belong to the family; later paragraphs are
        # nested skill descriptions and are represented separately below.
        description = "\n".join(card["paragraphs"][:2])
        external_key = card["html_id"] or slugify(name)
        row = {
            "external_key": external_key, "slug": slugify(name), "name": name,
            "image_url": card["image_url"], "category": "Nhánh phù hiệu", "level": None,
            "description": description, "attributes": {},
            "source_url": SOURCE_URLS["enchantment"], "fetched_at": fetched_at,
        }
        row["content_hash"] = _hash_entry(name, description, row["source_url"])
        families.append(row)

    enchantments = []
    for card in enchantment_parser.items:
        name = card["title"]
        description = card["article"] or (card["paragraphs"][-1] if card["paragraphs"] else "")
        external_key = card["html_id"] or slugify(name)
        group_match = re.search(r"group(\d+)", external_key)
        # The last head fragment is the official family name.
        head_parts = card["head"].split()
        family = next((row["name"] for row in families if external_key.startswith(row["external_key"])), None)
        row = {
            "external_key": external_key, "slug": slugify(name), "name": name,
            "image_url": card["image_url"], "category": family or "Phù hiệu",
            "level": f"Bậc {group_match.group(1)}" if group_match else None,
            "description": description, "attributes": {"head": card["head"]},
            "source_url": SOURCE_URLS["enchantment"], "fetched_at": fetched_at,
        }
        row["content_hash"] = _hash_entry(name, description, row["source_url"])
        enchantments.append(row)

    return {
        "source": "Garena Liên Quân Mobile - Học viện/Gameplay",
        "generated_at": fetched_at,
        "scope": "Danh mục chính thức; không phải build hoặc khuyến nghị tướng chính thức.",
        "sources": {
            kind: {"url": url, "fetched_at": fetched_at, "content_hash": hashlib.sha256(documents[kind].encode("utf-8")).hexdigest()}
            for kind, url in SOURCE_URLS.items()
        },
        "equipment": equipment,
        "runes": runes,
        "talents": talents,
        "enchantment_families": families,
        "enchantments": enchantments,
    }


def fetch(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return response.read().decode("utf-8")
        except (urllib.error.URLError, TimeoutError) as exc:
            last_error = exc
            time.sleep(1 + attempt)
    raise RuntimeError(f"Cannot fetch {url}: {last_error}")


def validate(payload: dict) -> None:
    minimums = {"equipment": 50, "runes": 50, "talents": 5, "enchantment_families": 3, "enchantments": 20}
    errors = [f"{key}={len(payload[key])} (<{minimum})" for key, minimum in minimums.items() if len(payload[key]) < minimum]
    if errors:
        raise RuntimeError("Nguồn trả về danh mục thiếu; không ghi đè cache: " + ", ".join(errors))
    for key in minimums:
        identifiers = [row["external_key"] for row in payload[key]]
        if len(identifiers) != len(set(identifiers)):
            raise RuntimeError(f"Danh mục {key} có external_key trùng; dừng để kiểm tra parser.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=OUTPUT_FILE)
    args = parser.parse_args()
    documents = {kind: fetch(url) for kind, url in SOURCE_URLS.items()}
    fetched_at = datetime.now(timezone.utc).isoformat()
    payload = parse_documents(documents, fetched_at)
    validate(payload)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    counts = {key: len(payload[key]) for key in ("equipment", "runes", "talents", "enchantment_families", "enchantments")}
    print(f"Saved official gameplay catalog to {args.output}: {counts}")


if __name__ == "__main__":
    main()
