"""Import the verified Garena gameplay catalog and derive auditable recommendations.

Catalog rows are official source material. Hero builds and synergy rows are explicitly
algorithmic derivatives and keep evidence/source metadata so the UI never presents them
as official Garena recommendations.
"""
from __future__ import annotations

import json
import unicodedata
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from statistics import mean

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.engines.hero_rating import METHOD_VERSION, matchup_from_ratings
from app.models import (
    GameplayCatalogEntry,
    Hero,
    HeroMatchup,
    HeroRating,
    HeroRecommendedBuild,
    HeroSynergy,
    Item,
)


CATALOG_FILE = Path(__file__).resolve().parents[3] / "data" / "imports" / "official_gameplay_catalog.json"
PATCH_VERSION = "official-2026.10.19"
BUILD_METHOD = "hero-build-v2"
SYNERGY_METHOD = "hero-synergy-v2"
MATCHUP_METHOD = "matchup-v1"


def _normal(value: str | None) -> str:
    value = (value or "").replace("đ", "d").replace("Đ", "D")
    return "".join(
        char for char in unicodedata.normalize("NFD", value.casefold())
        if unicodedata.category(char) != "Mn"
    )


def _date(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)


def _roles_for_equipment(category: str, description: str) -> list[str]:
    category_key = _normal(category)
    text = _normal(description)
    roles: set[str] = set()
    if category_key == "cong":
        roles.update(("Xạ thủ", "Sát thủ", "Đấu sĩ"))
    elif category_key == "phep":
        roles.update(("Pháp sư", "Trợ thủ"))
    elif category_key == "thu":
        roles.update(("Đỡ đòn", "Đấu sĩ", "Trợ thủ"))
    elif category_key == "tro thu":
        roles.update(("Trợ thủ", "Đỡ đòn"))
    elif category_key == "giay":
        roles.update(("Xạ thủ", "Sát thủ", "Đấu sĩ", "Pháp sư", "Trợ thủ", "Đỡ đòn"))
    if "sat thuong phep" in text or "cong phep" in text:
        roles.add("Pháp sư")
    if "toc danh" in text or "chi mang" in text:
        roles.add("Xạ thủ")
    return sorted(roles)


def _counter_tags(description: str) -> list[str]:
    text = _normal(description)
    tags = []
    for needle, label in (
        ("hoi mau", "hồi phục"),
        ("hut mau", "hồi phục"),
        ("khien", "dồn sát thương"),
        ("khang phep", "sát thương phép"),
        ("giam toc danh", "tốc đánh"),
    ):
        if needle in text and label not in tags:
            tags.append(label)
    return tags


def sync_gameplay_catalog(db: Session) -> dict:
    if not CATALOG_FILE.exists():
        return {"status": "missing", "catalog_entries": 0, "active_items": 0}
    payload = json.loads(CATALOG_FILE.read_text(encoding="utf-8"))
    groups = {
        "equipment": payload.get("equipment", []),
        "rune": payload.get("runes", []),
        "talent": payload.get("talents", []),
        "enchantment_family": payload.get("enchantment_families", []),
        "enchantment": payload.get("enchantments", []),
    }
    imported = 0
    for kind, records in groups.items():
        for record in records:
            key = str(record["external_key"])
            row = db.scalar(select(GameplayCatalogEntry).where(
                GameplayCatalogEntry.kind == kind,
                GameplayCatalogEntry.external_key == key,
            ))
            if not row:
                row = GameplayCatalogEntry(kind=kind, external_key=key)
                db.add(row)
            row.slug = record.get("slug") or key
            row.name = record["name"]
            row.category = record.get("category") or record.get("family")
            row.level = record.get("level")
            row.image_url = record.get("image_url")
            row.description = record.get("description") or ""
            row.attributes = record.get("attributes") or {}
            row.source_url = record.get("source_url") or payload.get("sources", {}).get(kind, {}).get("url", "")
            row.content_hash = record.get("content_hash") or ""
            row.fetched_at = _date(record.get("fetched_at"))
            row.verified = True
            imported += 1

    # Only current, final-tier official equipment is eligible for a six-item build.
    for item in db.scalars(select(Item)):
        item.is_active = False
    active_items = 0
    for record in payload.get("equipment", []):
        slug = record.get("slug") or str(record["external_key"])
        item = db.scalar(select(Item).where(Item.slug == slug))
        if not item:
            item = db.scalar(select(Item).where(Item.name == record["name"]))
        if not item:
            item = Item(slug=slug, name=record["name"], category=record.get("category") or "Khác", cost=0, patch_version=PATCH_VERSION)
            db.add(item)
        attrs = dict(record.get("attributes") or {})
        attrs.update({
            "attack": attrs.get("physical_attack", 0),
            "health": attrs.get("max_health", 0),
            "_image_url": record.get("image_url"),
            "_source_url": record.get("source_url"),
            "_level": record.get("level"),
        })
        item.slug = slug
        item.name = record["name"]
        item.category = record.get("category") or "Khác"
        item.cost = int(record.get("cost") or 0)
        item.attributes = attrs
        item.passive = record.get("description") or None
        item.roles = _roles_for_equipment(item.category, item.passive or "")
        item.counters = _counter_tags(item.passive or "")
        item.patch_version = PATCH_VERSION
        item.is_active = record.get("level") == "Cấp 3"
        active_items += int(item.is_active)
    db.flush()
    return {"status": "ok", "catalog_entries": imported, "active_items": active_items}


def _item_score(hero: Hero, item: Item) -> float:
    attrs = item.attributes or {}
    roles = {role.role for role in hero.roles}
    damage_type = _normal(hero.damage_type)
    score = 10.0 + (18.0 if roles.intersection(item.roles or []) else 0.0)
    physical = float(attrs.get("physical_attack", 0))
    magic = float(attrs.get("magic_power", 0))
    defense = float(attrs.get("armor", 0)) + float(attrs.get("magic_defense", 0))
    health = float(attrs.get("max_health", 0))
    if "physical" in damage_type or roles.intersection({"Xạ thủ", "Sát thủ"}):
        score += min(28, physical / 7 + float(attrs.get("attack_speed", 0)) / 5)
    if "magic" in damage_type or "Pháp sư" in roles:
        score += min(28, magic / 10 + float(attrs.get("magic_pierce", 0)) / 8)
    if roles.intersection({"Đỡ đòn", "Trợ thủ"}):
        score += min(30, defense / 20 + health / 180)
    if "Đấu sĩ" in roles:
        score += min(20, physical / 12 + health / 250 + defense / 35)
    return round(score, 2)


def _select_arcana(catalog: dict, hero: Hero) -> dict:
    roles = {role.role for role in hero.roles}
    damage_type = _normal(hero.damage_type)
    terms = (
        ("cong phep", "xuyen giap phep") if "magic" in damage_type or "Pháp sư" in roles
        else ("cong vat ly", "xuyen giap", "toc danh")
    )
    selected = {}
    for color in ("Đỏ", "Tím", "Xanh"):
        rows = [row for row in catalog.get("runes", []) if row.get("category") == color]
        rows.sort(key=lambda row: (
            4 * int(row.get("level") == "Cấp III")
            + sum(term in _normal(row.get("description")) for term in terms)
        ), reverse=True)
        if rows:
            selected[color] = {
                "name": rows[0]["name"], "external_key": rows[0]["external_key"],
                "image_url": rows[0].get("image_url"), "description": rows[0].get("description") or "",
                "level": rows[0].get("level"), "count": 10,
            }
    return selected


def _select_enchantments(catalog: dict, hero: Hero) -> dict:
    roles = {role.role for role in hero.roles}
    if roles.intersection({"Trợ thủ", "Đỡ đòn"}):
        family = "Rừng nguyên sinh"
    elif roles.intersection({"Xạ thủ", "Pháp sư"}):
        family = "Tháp quang minh"
    else:
        family = "Vực hỗn mang"
    rows = [row for row in catalog.get("enchantments", []) if row.get("category") == family]
    priorities = (
        ("hoi", "khien", "phong ngu", "mien thuong") if roles.intersection({"Trợ thủ", "Đỡ đòn"})
        else ("sat thuong", "xuyen", "chi mang", "cong")
    )
    selected = []
    for tier in ("Bậc 1", "Bậc 2", "Bậc 3"):
        tier_rows = [row for row in rows if row.get("level") == tier]
        tier_rows.sort(key=lambda row: sum(term in _normal(
            f"{row.get('description', '')} {(row.get('attributes') or {}).get('head', '')}"
        ) for term in priorities), reverse=True)
        if tier_rows:
            row = tier_rows[0]
            selected.append({
                "name": row["name"], "external_key": row["external_key"],
                "image_url": row.get("image_url"), "description": row.get("description") or "",
                "level": row.get("level"),
            })
    return {"family": family, "entries": selected}


def _select_talent(catalog: dict, hero: Hero, position: str) -> str | None:
    available = {row["name"] for row in catalog.get("talents", [])}
    roles = {role.role for role in hero.roles}
    preferred = (
        "TRỪNG TRỊ" if _normal(position) == "rung"
        else "CẤP CỨU" if roles.intersection({"Trợ thủ", "Đỡ đòn"})
        else "TỐC BIẾN"
    )
    return preferred if preferred in available else next(iter(sorted(available)), None)


@lru_cache(maxsize=1)
def _load_catalog() -> dict:
    if not CATALOG_FILE.exists():
        return {}
    return json.loads(CATALOG_FILE.read_text(encoding="utf-8"))


def recommend_loadout(hero: Hero, position: str, phase: str, playstyle: str) -> dict:
    """Return a complete loadout derived from the local gameplay catalog."""
    catalog = _load_catalog()
    if not catalog:
        return {"status": "unavailable", "arcana": [], "enchantment": None, "talent": None}
    arcana = _select_arcana(catalog, hero)
    enchantment = _select_enchantments(catalog, hero)
    talent_name = _select_talent(catalog, hero, position)
    talent_row = next((row for row in catalog.get("talents", []) if row.get("name") == talent_name), None)
    return {
        "status": "ok",
        "arcana": [{"color": color, **row} for color, row in arcana.items()],
        "enchantment": enchantment,
        "talent": ({
            "name": talent_row["name"], "external_key": talent_row["external_key"],
            "image_url": talent_row.get("image_url"), "description": talent_row.get("description") or "",
        } if talent_row else None),
        "summary": f"Cấu hình {position.lower()} · {playstyle} · {phase}, gồm 30 viên ngọc Cấp III, 3 bậc phù hiệu và 1 phép bổ trợ.",
    }


def sync_hero_builds(db: Session) -> int:
    if not CATALOG_FILE.exists():
        return 0
    catalog = json.loads(CATALOG_FILE.read_text(encoding="utf-8"))
    items = list(db.scalars(select(Item).where(Item.is_active.is_(True))))
    count = 0
    for hero in db.scalars(select(Hero).order_by(Hero.id)):
        positions = hero.positions or ["Chưa xác định"]
        selected = sorted(items, key=lambda item: _item_score(hero, item), reverse=True)[:6]
        for position in positions:
            row = db.scalar(select(HeroRecommendedBuild).where(
                HeroRecommendedBuild.hero_id == hero.id,
                HeroRecommendedBuild.position == position,
                HeroRecommendedBuild.situation == "default",
                HeroRecommendedBuild.patch_version == PATCH_VERSION,
            ))
            if not row:
                row = HeroRecommendedBuild(
                    hero_id=hero.id, position=position, situation="default",
                    explanation="", patch_version=PATCH_VERSION,
                )
                db.add(row)
            row.item_ids = [item.id for item in selected]
            row.arcana = _select_arcana(catalog, hero)
            row.enchantments = _select_enchantments(catalog, hero)
            row.talent = _select_talent(catalog, hero, position)
            row.explanation = (
                "Bộ gợi ý do thuật toán xếp hạng từ vai trò, loại sát thương và thuộc tính "
                "trang bị Cấp 3 trong danh mục Garena; cần điều chỉnh theo đội hình thực tế."
            )
            row.data_status = "derived_pending_review"
            row.evidence = [item.slug for item in selected]
            row.confidence = 0.62 if len(selected) == 6 else 0.35
            row.provenance = "derived_from_official_catalog"
            row.method_version = BUILD_METHOD
            row.source_url = catalog.get("sources", {}).get("equipment", {}).get("url")
            count += 1
    db.flush()
    return count


def _rating_dict(rating: HeroRating) -> dict[str, float | None]:
    return {key: getattr(rating, key) for key in (
        "damage", "durability", "mobility", "crowd_control", "sustain", "burst",
        "teamfight", "split_push", "pickoff", "protection", "objective_control",
        "early_game", "mid_game", "late_game", "difficulty",
    )}


def _synergy(left: HeroRating, right: HeroRating) -> tuple[float, list[str]] | None:
    a, b = _rating_dict(left), _rating_dict(right)
    pairs = (
        ("khống chế + sát thương", a["crowd_control"], b["damage"]),
        ("sát thương + khống chế", a["damage"], b["crowd_control"]),
        ("bảo vệ + sát thương", a["protection"], b["damage"]),
        ("sát thương + bảo vệ", a["damage"], b["protection"]),
        ("chống chịu + giao tranh", a["durability"], b["teamfight"]),
        ("giao tranh + chống chịu", a["teamfight"], b["durability"]),
        ("cơ động + bắt lẻ", a["mobility"], b["pickoff"]),
        ("bắt lẻ + cơ động", a["pickoff"], b["mobility"]),
    )
    usable = [(label, (float(x) + float(y)) / 2) for label, x, y in pairs if x is not None and y is not None]
    if len(usable) < 2:
        return None
    usable.sort(key=lambda pair: pair[1], reverse=True)
    return round(mean(value for _, value in usable), 1), [label for label, _ in usable[:3]]


def sync_relationships(db: Session) -> dict:
    ratings = list(db.scalars(select(HeroRating).where(
        HeroRating.patch_version == "official-2026.10.15",
        HeroRating.method_version == METHOD_VERSION,
    ).order_by(HeroRating.hero_id)))
    by_hero = {row.hero_id: row for row in ratings}
    candidates: dict[int, list[tuple[float, int, list[str]]]] = {hero_id: [] for hero_id in by_hero}
    for index, left in enumerate(ratings):
        for right in ratings[index + 1:]:
            result = _synergy(left, right)
            if result:
                score, evidence = result
                candidates[left.hero_id].append((score, right.hero_id, evidence))
                candidates[right.hero_id].append((score, left.hero_id, evidence))
    selected_pairs: dict[tuple[int, int], tuple[float, list[str]]] = {}
    for hero_id, rows in candidates.items():
        for score, other_id, evidence in sorted(rows, reverse=True)[:3]:
            key = tuple(sorted((hero_id, other_id)))
            if key not in selected_pairs or score > selected_pairs[key][0]:
                selected_pairs[key] = (score, evidence)
    for (left_id, right_id), (score, evidence) in selected_pairs.items():
        row = db.scalar(select(HeroSynergy).where(
            HeroSynergy.hero_a_id == left_id,
            HeroSynergy.hero_b_id == right_id,
            HeroSynergy.patch_version == PATCH_VERSION,
        ))
        if not row:
            row = HeroSynergy(hero_a_id=left_id, hero_b_id=right_id, score=score, reason="", patch_version=PATCH_VERSION)
            db.add(row)
        row.score = score
        row.confidence = round(min(by_hero[left_id].confidence, by_hero[right_id].confidence) * 0.75, 2)
        row.reason = "Bổ sung lẫn nhau ở: " + ", ".join(evidence) + "."
        row.evidence = evidence
        row.conditions = ["Hiệu quả phụ thuộc vị trí, tài nguyên và thời điểm tung kỹ năng."]
        row.data_status = "derived_partial"
        row.provenance = "derived_from_official_skill_ratings"
        row.method_version = SYNERGY_METHOD

    matchup_count = 0
    for left in ratings:
        for right in ratings:
            if left.hero_id == right.hero_id:
                continue
            result = matchup_from_ratings(_rating_dict(left), _rating_dict(right))
            if result["advantage_score"] is None:
                continue
            row = db.scalar(select(HeroMatchup).where(
                HeroMatchup.hero_id == left.hero_id,
                HeroMatchup.opponent_id == right.hero_id,
                HeroMatchup.method_version == MATCHUP_METHOD,
                HeroMatchup.patch_version == PATCH_VERSION,
            ))
            if not row:
                row = HeroMatchup(
                    hero_id=left.hero_id, opponent_id=right.hero_id,
                    method_version=MATCHUP_METHOD, patch_version=PATCH_VERSION,
                )
                db.add(row)
            row.advantage_score = result["advantage_score"]
            row.reasons = result["reasons"]
            row.conditions = result["conditions"]
            row.data_status = result["data_status"]
            row.confidence = result["confidence"]
            matchup_count += 1
    db.flush()
    return {"synergies": len(selected_pairs), "matchups": matchup_count}
