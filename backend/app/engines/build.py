from statistics import mean

from .analysis_adapter import profile_for
from .scoring import evidence_attr_dict, role_names


def recommend_items(hero, enemies, items, phase: str, playstyle: str) -> dict:
    enemy_attrs = [evidence_attr_dict(enemy) for enemy in enemies]
    physical_values = [row["physical_damage"] for row in enemy_attrs if row["physical_damage"] is not None]
    magic_values = [row["magic_damage"] for row in enemy_attrs if row["magic_damage"] is not None]
    durability_values = [row["durability"] for row in enemy_attrs if row["durability"] is not None]
    physical_threat = mean(physical_values) if physical_values else None
    magic_threat = mean(magic_values) if magic_values else None
    healing_threat = mean(durability_values) if durability_values else None
    roles = role_names(hero)
    scored = []
    for item in items:
        if not item.is_active:
            continue
        data = item.attributes or {}
        score = 30.0
        reasons = []
        if roles.intersection(item.roles or []):
            score += 22
            reasons.append("phù hợp vai trò của tướng")
        armor = float(data.get("armor", 0))
        magic_def = float(data.get("magic_defense", 0))
        attack = float(data.get("attack", 0))
        magic = float(data.get("magic_power", 0))
        health = float(data.get("health", 0))
        if physical_threat is not None:
            score += min(18, armor / 20 * physical_threat / 100)
        if magic_threat is not None:
            score += min(18, magic_def / 15 * magic_threat / 100)
        score += min(16, (attack + magic) / 10)
        score += min(12, health / 100)
        if armor and physical_threat is not None and physical_threat > 58:
            reasons.append("giảm áp lực sát thương vật lý")
        if magic_def and magic_threat is not None and magic_threat > 58:
            reasons.append("giảm áp lực sát thương phép")
        if "hồi phục" in (item.counters or []) and healing_threat is not None and healing_threat > 58:
            score += 14
            reasons.append("hạn chế hồi phục của đối phương")
        if playstyle in {"tấn công", "dồn sát thương"} and (attack or magic):
            score += 8
        if playstyle in {"an toàn", "chống chịu"} and (armor or magic_def or health):
            score += 8
        scored.append((score, item, reasons or ["bổ sung chỉ số ổn định cho bộ trang bị"]))
    selected = sorted(scored, key=lambda row: row[0], reverse=True)[:6]
    missing_evidence = []
    if enemies and physical_threat is None:
        missing_evidence.append("physical_damage")
    if enemies and magic_threat is None:
        missing_evidence.append("magic_damage")
    if enemies and healing_threat is None:
        missing_evidence.append("durability")
    profile = profile_for(hero)
    evidence_coverage = (
        1.0 if not enemies else
        (3 - len(missing_evidence)) / 3
    )
    status = "ok" if selected and not missing_evidence else "partial" if selected else "insufficient"
    return {
        "hero": hero.name,
        "phase": phase,
        "threat_profile": {
            "physical": round(physical_threat, 1) if physical_threat is not None else None,
            "magic": round(magic_threat, 1) if magic_threat is not None else None,
        },
        "items": [
            {
                "id": item.id,
                "name": item.name,
                "image_url": (item.attributes or {}).get("_image_url"),
                "category": item.category,
                "cost": item.cost,
                "attributes": item.attributes if item.attributes else {},
                "score": round(min(100, score), 1),
                "reason": "; ".join(reasons),
                "replace_when": "Thay đổi khi nguồn sát thương hoặc hồi phục chủ đạo của đối phương thay đổi.",
            }
            for score, item, reasons in selected
        ],
        "confidence": round(min(0.9, profile.confidence * (0.65 + evidence_coverage * 0.35)), 2),
        "status": status,
        "missing_evidence": missing_evidence,
        "message": (
            None if status == "ok"
            else "Khuyến nghị dùng dữ liệu vai trò và trang bị đã có; một phần hồ sơ địch chưa đủ bằng chứng."
            if status == "partial"
            else "Chưa đủ dữ liệu vai trò hoặc trang bị để tạo khuyến nghị."
        ),
        "data_source": profile.source,
        "score_kind": "algorithmic",
    }

