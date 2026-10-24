"""Deterministic, auditable derivations layered on official catalog text.

None of the outputs in this module are official Garena recommendations.  Every
record carries its evidence and is deliberately capped below expert-review
confidence.
"""
from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass

from .hero_rating import normalize


KNOWLEDGE_METHOD_VERSION = "hero-knowledge-v1"
BUILD_METHOD_VERSION = "hero-build-v1"
SYNERGY_METHOD_VERSION = "hero-synergy-v1"


def _skill_text(skills: list[dict]) -> str:
    return " ".join(skill.get("description", "") for skill in skills)


def _matching_skill_evidence(skills: list[dict], patterns: tuple[str, ...]) -> list[str]:
    evidence = []
    for skill in skills:
        normalized = normalize(skill.get("description", ""))
        if any(re.search(pattern, normalized) for pattern in patterns):
            evidence.append(f"{skill.get('name', 'Kỹ năng')}: {skill.get('description', '').strip()}")
    return evidence


def derive_weaknesses(skills: list[dict], ratings: dict[str, float | None]) -> list[dict]:
    """Return constraints directly stated by skills, then an honest data gap.

    Absence of a keyword is never turned into a categorical gameplay claim.
    The fallback rows explicitly say "chưa xác minh" and have low/zero
    confidence, which lets the UI provide coverage without fabricating facts.
    """

    rules = [
        {
            "key": "stationary_or_channelled_cast",
            "title": "Có thời điểm phải đứng yên hoặc niệm chú",
            "patterns": (r"dung yen", r"giu nguyen vi tri", r"khong the di chuyen", r"niem chu", r"van cong", r"tu luc"),
            "explanation": "Mô tả kỹ năng nêu trực tiếp thời gian đứng yên, niệm chú hoặc tụ lực; đối thủ có thể tận dụng cửa sổ này nếu cơ chế miễn nhiễm không được nêu kèm.",
            "confidence": 0.72,
        },
        {
            "key": "interruptible_or_cancellable_cast",
            "title": "Kỹ năng có điều kiện bị hủy hoặc ngắt",
            "patterns": (r"ngat chieu", r"bi danh ngat", r"huy chieu", r"co the huy", r"se huy", r"ngat quang"),
            "explanation": "Mô tả chính thức nói kỹ năng có thể bị hủy/ngắt hoặc tự hủy khi thao tác khác; đây là rủi ro thi triển có điều kiện.",
            "confidence": 0.78,
        },
        {
            "key": "setup_or_stack_dependency",
            "title": "Một phần hiệu lực cần tích lũy hoặc đánh trúng trước",
            "patterns": (r"cong don", r"tich du", r"dat du", r"du \d+", r"sau \d+ lan", r"moi don danh thu"),
            "explanation": "Một cơ chế mạnh chỉ kích hoạt sau số lần đánh trúng, dấu ấn hoặc cộng dồn được mô tả; hiệu lực không xuất hiện ngay từ lần tác động đầu tiên.",
            "confidence": 0.68,
        },
        {
            "key": "health_cost",
            "title": "Có kỹ năng tiêu hao máu bản thân",
            "patterns": (r"tieu hao .*mau", r"mat .*mau .*ban than", r"tieu hao \d+%.*mau"),
            "explanation": "Mô tả chính thức nêu chi phí máu; sử dụng sai thời điểm có thể làm giảm biên an toàn của tướng.",
            "confidence": 0.82,
        },
    ]
    results = []
    for rule in rules:
        evidence = _matching_skill_evidence(skills, rule["patterns"])
        if evidence:
            results.append({
                "weakness_key": rule["key"], "title": rule["title"],
                "explanation": rule["explanation"], "evidence": evidence,
                "confidence": rule["confidence"], "provenance": "derived_from_explicit_official_skill_constraint",
            })

    if results:
        return results

    skill_names = [skill.get("name", "Kỹ năng") for skill in skills]
    if ratings.get("mobility") is None:
        return [{
            "weakness_key": "unverified_escape_tool",
            "title": "Chưa xác minh công cụ thoát thân từ mô tả kỹ năng",
            "explanation": "Bốn mô tả kỹ năng không khớp nhóm cơ chế lướt/dịch chuyển/tăng tốc/nhảy. Đây là khoảng trống bằng chứng, không phải khẳng định tướng hoàn toàn kém cơ động.",
            "evidence": [f"Đã kiểm tra mô tả: {', '.join(skill_names)}; không có từ khóa cơ động đã định nghĩa."],
            "confidence": 0.25, "provenance": "absence_observation_not_gameplay_fact",
        }]
    if ratings.get("durability") is None:
        return [{
            "weakness_key": "unverified_damage_mitigation",
            "title": "Chưa xác minh cơ chế tự giảm thiểu sát thương",
            "explanation": "Mô tả kỹ năng không khớp lá chắn/miễn thương/giảm sát thương/miễn tử/tăng giáp. Đây chỉ là quan sát phạm vi dữ liệu, không thay thế chỉ số chống chịu cơ bản.",
            "evidence": [f"Đã kiểm tra mô tả: {', '.join(skill_names)}; không có từ khóa giảm thiểu sát thương đã định nghĩa."],
            "confidence": 0.25, "provenance": "absence_observation_not_gameplay_fact",
        }]
    return [{
        "weakness_key": "insufficient_specific_weakness_evidence",
        "title": "Chưa đủ dữ liệu để xác minh nhược điểm đặc thù",
        "explanation": "Nguồn chính thức hiện có mô tả kỹ năng nhưng không cung cấp đầy đủ tầm đánh, thời gian khung hình, năng lượng, chỉ số cơ bản và dữ liệu trận đấu để kết luận một nhược điểm riêng.",
        "evidence": ["Phạm vi nguồn: mô tả bốn kỹ năng chính thức."],
        "confidence": 0.0, "provenance": "insufficient_official_evidence",
    }]


def derive_phase_scores(skills: list[dict], expert_phase: str | None = None) -> dict[str, dict]:
    phases = {
        phase: {
            "score": None,
            "analysis": {
                "status": "insufficient",
                "explanation": "Mô tả kỹ năng không đủ để định lượng sức mạnh theo giai đoạn này; cần dữ liệu cấp độ, trang bị và trận đấu có phiên bản.",
                "evidence": [],
            },
            "confidence": 0.0,
            "provenance": "insufficient_official_evidence",
        }
        for phase in ("early", "mid", "late")
    }
    if expert_phase in phases:
        phases[expert_phase] = {
            "score": 75.0,
            "analysis": {
                "status": "expert_pending_review",
                "explanation": "Nhãn giai đoạn từ bộ dữ liệu chuyên gia khởi tạo; không phải chỉ số chính thức của Garena.",
                "evidence": [f"power_phase={expert_phase} trong starter_data.json"],
            },
            "confidence": 0.45,
            "provenance": "expert_pending_review",
        }

    scaling_patterns = (r"tang theo cap tuong", r"moi cap tuong", r"giam theo cap", r"vinh vien")
    evidence = _matching_skill_evidence(skills, scaling_patterns)
    if evidence:
        current = phases["late"]
        if current["score"] is None:
            phases["late"] = {
                "score": 65.0,
                "analysis": {
                    "status": "derived_partial",
                    "explanation": "Mô tả chính thức có cơ chế tăng trực tiếp theo cấp tướng hoặc tích lũy vĩnh viễn; điểm chỉ biểu thị tín hiệu tăng tiến, không phải sức mạnh meta.",
                    "evidence": evidence,
                },
                "confidence": 0.45,
                "provenance": "derived_from_explicit_official_scaling_text",
            }
        else:
            current["analysis"]["evidence"].extend(evidence)
    return phases


def detect_range_type(skills: list[dict]) -> tuple[str | None, list[str]]:
    text = normalize(_skill_text(skills))
    ranged = any(term in text for term in ("trang thai ban xa", "danh xa", "tam danh xa"))
    melee = any(term in text for term in ("trang thai can chien", "danh ap sat", "che do can chien"))
    if ranged and melee:
        return "hybrid", ["Mô tả chính thức nêu cả trạng thái đánh xa và cận chiến."]
    # A projectile skill alone does not establish the hero's basic range.
    return None, []


def derive_synergy(hero_a: dict, hero_b: dict) -> dict | None:
    """Score only explicit, complementary capability pairs."""

    signals: list[tuple[float, str, list[str]]] = []
    for controller, finisher in ((hero_a, hero_b), (hero_b, hero_a)):
        control = controller["ratings"].get("crowd_control")
        damage = max(value for value in (
            finisher["ratings"].get("damage"), finisher["ratings"].get("burst"),
            finisher["ratings"].get("teamfight"),
        ) if value is not None) if any(value is not None for value in (
            finisher["ratings"].get("damage"), finisher["ratings"].get("burst"), finisher["ratings"].get("teamfight")
        )) else None
        if control is not None and damage is not None and control >= 32 and damage >= 38:
            evidence = controller["evidence"].get("crowd_control", []) + (
                finisher["evidence"].get("burst", []) or finisher["evidence"].get("damage", []) or finisher["evidence"].get("teamfight", [])
            )
            signals.append((min(control, damage), f"{controller['name']} có cơ chế khống chế tạo cửa sổ để {finisher['name']} áp dụng sát thương đã được mô tả.", evidence))

        protection = controller["ratings"].get("protection")
        finisher_damage = finisher["ratings"].get("damage")
        if protection is not None and finisher_damage is not None and protection >= 32 and finisher_damage >= 38:
            evidence = controller["evidence"].get("protection", []) + finisher["evidence"].get("damage", [])
            signals.append((min(protection, finisher_damage), f"{controller['name']} có cơ chế bảo vệ đồng đội, bổ trợ cho khả năng gây sát thương của {finisher['name']}.", evidence))

    if not signals:
        return None
    signals.sort(key=lambda row: row[0], reverse=True)
    score = round(min(82.0, 50.0 + sum(row[0] - 25 for row in signals[:3]) / len(signals[:3]) * 0.45), 1)
    confidence = round(min(0.70, 0.30 + 0.10 * len(signals[:3]) + (hero_a["confidence"] + hero_b["confidence"]) * 0.12), 2)
    return {
        "score": score, "confidence": confidence,
        "reason": " ".join(row[1] for row in signals[:3]),
        "evidence": list(dict.fromkeys(value for row in signals[:3] for value in row[2])),
        "conditions": ["Suy luận từ cơ chế kỹ năng; hiệu quả thực tế còn phụ thuộc vị trí, thời điểm chiêu và phối hợp người chơi."],
        "data_status": "derived_pending_review", "provenance": "complementarity_from_official_skill_text",
        "method_version": SYNERGY_METHOD_VERSION,
    }


def select_synergy_pairs(profiles: list[dict], per_hero: int = 3) -> list[tuple[int, int, dict]]:
    candidates = []
    for index, hero_a in enumerate(profiles):
        for hero_b in profiles[index + 1:]:
            result = derive_synergy(hero_a, hero_b)
            if result:
                candidates.append((hero_a["id"], hero_b["id"], result))
    selected: dict[tuple[int, int], tuple[int, int, dict]] = {}
    by_hero: dict[int, list[tuple[int, int, dict]]] = defaultdict(list)
    for row in candidates:
        by_hero[row[0]].append(row)
        by_hero[row[1]].append(row)
    for rows in by_hero.values():
        for row in sorted(rows, key=lambda value: (value[2]["score"], value[2]["confidence"], -value[0], -value[1]), reverse=True)[:per_hero]:
            selected[(row[0], row[1])] = row
    return sorted(selected.values(), key=lambda row: (row[0], row[1]))


def _item_score(profile: dict, item: dict) -> tuple[float, list[str]]:
    attrs = item.get("attributes") or {}
    roles = set(profile["roles"])
    damage_type = profile.get("damage_type")
    score = 5.0
    reasons = []
    physical = float(attrs.get("physical_attack", 0))
    magic = float(attrs.get("magic_power", 0))
    defense = float(attrs.get("armor", 0)) + float(attrs.get("magic_defense", 0))
    health = float(attrs.get("max_health", 0))
    attack_speed = float(attrs.get("attack_speed", 0))
    if damage_type in {"physical", "mixed", "true"} and physical:
        score += min(24, physical / 5)
        reasons.append("khớp tín hiệu sát thương vật lý")
    if damage_type in {"magic", "mixed"} and magic:
        score += min(24, magic / 10)
        reasons.append("khớp tín hiệu sát thương phép")
    if roles & {"Đỡ đòn", "Trợ thủ", "Đấu sĩ"} and (defense or health):
        score += min(24, defense / 30 + health / 150)
        reasons.append("bổ sung chống chịu phù hợp vai trò")
    if "Xạ thủ" in roles and (attack_speed or attrs.get("critical_chance")):
        score += min(22, attack_speed / 2 + float(attrs.get("critical_chance", 0)))
        reasons.append("bổ sung tốc đánh/chí mạng cho vai trò Xạ thủ")
    if "Pháp sư" in roles and item.get("category") == "Phép":
        score += 12
    if profile["ratings"].get("durability") is not None and (defense or health):
        score += 5
    if profile["ratings"].get("mobility") is not None and attrs.get("movement_speed"):
        score += 4
    if item.get("category") == "Trợ thủ" and roles & {"Trợ thủ", "Đỡ đòn"}:
        score += 20
        reasons.append("thuộc danh mục Trợ thủ chính thức")
    if item.get("category") == "Đi rừng" and "Rừng" in profile["positions"]:
        score += 22
        reasons.append("thuộc danh mục Đi rừng chính thức")
    return score, reasons or ["chỉ số bổ sung từ danh mục chính thức; độ phù hợp cần duyệt"]


def _select_equipment(profile: dict, equipment: list[dict]) -> tuple[list[dict], list[str]]:
    level_three = [row for row in equipment if row.get("level") == "Cấp 3" and row.get("cost")]
    ranked = sorted(((*_item_score(profile, row), row) for row in level_three), key=lambda value: (value[0], value[2]["name"]), reverse=True)
    selected: list[tuple[float, list[str], dict]] = []
    required_category = "Đi rừng" if "Rừng" in profile["positions"] else "Trợ thủ" if set(profile["roles"]) & {"Trợ thủ"} else None
    if required_category:
        match = next((row for row in ranked if row[2]["category"] == required_category), None)
        if match:
            selected.append(match)
    movement = next((row for row in ranked if row[2]["category"] == "Tốc độ"), None)
    if movement and movement[2]["external_key"] not in {value[2]["external_key"] for value in selected}:
        selected.append(movement)
    for row in ranked:
        if len(selected) >= 6:
            break
        if row[2]["external_key"] not in {value[2]["external_key"] for value in selected}:
            selected.append(row)
    evidence = [f"{row['name']}: {', '.join(reasons)}" for _, reasons, row in selected]
    return [row for _, _, row in selected], evidence


def _rune_score(profile: dict, rune: dict) -> float:
    attrs = rune.get("attributes") or {}
    roles = set(profile["roles"])
    score = 1.0
    if profile.get("damage_type") in {"physical", "mixed", "true"}:
        score += float(attrs.get("physical_attack", 0)) * 2 + float(attrs.get("armor_pierce", 0))
    if profile.get("damage_type") in {"magic", "mixed"}:
        score += float(attrs.get("magic_power", 0)) + float(attrs.get("magic_pierce", 0))
    if "Xạ thủ" in roles:
        score += float(attrs.get("attack_speed", 0)) + float(attrs.get("critical_chance", 0))
    if roles & {"Đỡ đòn", "Trợ thủ"}:
        score += float(attrs.get("max_health", 0)) / 10 + float(attrs.get("armor", 0)) + float(attrs.get("magic_defense", 0))
    score += float(attrs.get("movement_speed", 0)) + float(attrs.get("cooldown_reduction", 0))
    return score


def _select_arcana(profile: dict, runes: list[dict]) -> dict:
    result = []
    for color in ("Đỏ", "Tím", "Xanh"):
        options = [row for row in runes if row.get("level") == "Cấp III" and row.get("category") == color]
        if not options:
            continue
        selected = max(options, key=lambda row: (_rune_score(profile, row), row["name"]))
        result.append({
            "color": color, "entry_key": selected["external_key"], "name": selected["name"],
            "quantity": 10, "reason": "Chọn bằng quy tắc khớp loại sát thương/vai trò với thuộc tính ngọc được Garena công bố.",
        })
    return {"data_status": "derived_pending_review", "source_url": "https://lienquan.garena.vn/hoc-vien/bang-ngoc/", "sets": result}


def _select_talent(profile: dict, talents: list[dict]) -> dict | None:
    if not talents:
        return None
    preferred = []
    if "Rừng" in profile["positions"]:
        preferred.append("trung-tri")
    if profile["ratings"].get("mobility") is None:
        preferred.append("toc-bien")
    if profile["ratings"].get("burst") is not None:
        preferred.append("boc-pha")
    if set(profile["roles"]) & {"Trợ thủ", "Đỡ đòn"}:
        preferred.extend(("cap-cuu", "suy-nhuoc"))
    preferred.extend(("toc-bien", "thanh-tay"))
    by_slug = {row["slug"]: row for row in talents}
    selected = next((by_slug[key] for key in preferred if key in by_slug), talents[0])
    return {
        "entry_key": selected["external_key"], "name": selected["name"],
        "reason": "Suy luận từ vị trí, vai trò và cơ chế đã nhận diện; không phải phép bổ trợ chính thức được Garena gán cho tướng.",
        "source_url": selected["source_url"], "data_status": "derived_pending_review",
    }


def _select_enchantments(profile: dict, enchantments: list[dict]) -> dict:
    roles = set(profile["roles"])
    family = "Tháp quang minh" if roles & {"Xạ thủ", "Pháp sư"} else "Rừng nguyên sinh" if roles & {"Trợ thủ", "Đỡ đòn"} else "Vực hỗn mang" if roles & {"Đấu sĩ", "Sát thủ"} else "Thành khởi nguyên"
    options = [row for row in enchantments if row.get("category") == family]
    keyword_weights = []
    if profile["ratings"].get("damage") is not None:
        keyword_weights.extend(("sát thương", "công vật lý", "công phép"))
    if profile["ratings"].get("sustain") is not None:
        keyword_weights.extend(("hồi máu", "hút máu"))
    if profile["ratings"].get("durability") is not None:
        keyword_weights.extend(("lá chắn", "miễn thương"))
    path = []
    for level in ("Bậc 1", "Bậc 2", "Bậc 3"):
        tier = [row for row in options if row.get("level") == level]
        if not tier:
            continue
        selected = max(tier, key=lambda row: (sum(normalize(row["description"]).count(normalize(term)) for term in keyword_weights), row["name"]))
        path.append({"level": level, "entry_key": selected["external_key"], "name": selected["name"]})
    return {
        "data_status": "derived_pending_review", "family": family, "primary_path": path,
        "reason": "Nhánh được khớp theo vai trò chính thức; từng ô được xếp bằng từ khóa cơ chế, cần người chơi duyệt theo lối chơi.",
        "source_url": "https://lienquan.garena.vn/hoc-vien/phu-hieu/",
    }


def derive_loadout(profile: dict, catalog: dict) -> dict:
    items, item_evidence = _select_equipment(profile, catalog.get("equipment", []))
    known = sum(value is not None for value in profile["ratings"].values())
    confidence = round(min(0.68, 0.32 + (0.12 if profile.get("damage_type") else 0) + (0.08 if profile["roles"] else 0) + min(0.12, known * 0.015)), 2)
    talent = _select_talent(profile, catalog.get("talents", []))
    return {
        "position": profile["positions"][0] if profile["positions"] else (profile["roles"][0] if profile["roles"] else "Chưa xác định"),
        "situation": "default", "item_keys": [row["external_key"] for row in items],
        "arcana": _select_arcana(profile, catalog.get("runes", [])),
        "enchantments": _select_enchantments(profile, catalog.get("enchantments", [])),
        "talent": talent,
        "explanation": "Loadout được máy suy luận từ vai trò chính thức, mô tả kỹ năng và danh mục gameplay Garena hiện hành; đây không phải build chính thức và cần duyệt theo trận đấu.",
        "evidence": [
            f"Vai trò chính thức: {', '.join(profile['roles']) or 'chưa có'}.",
            f"Loại sát thương nhận diện từ kỹ năng: {profile.get('damage_type') or 'chưa đủ bằng chứng'}.",
            *item_evidence,
        ],
        "confidence": confidence, "data_status": "derived_pending_review",
        "provenance": "derived_from_official_skills_and_gameplay_catalog",
        "method_version": BUILD_METHOD_VERSION,
        "source_url": "https://lienquan.garena.vn/hoc-vien/trang-bi/",
    }
