from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.engines.hero_rating import METHOD_VERSION, TITLES, analyze_skill_text
from app.models import (
    GameplayCatalogEntry, Hero, HeroAnalysis, HeroAnalysisVersion, HeroDataSource,
    HeroMatchup, HeroPowerSpike, HeroRating, HeroRecommendedBuild, HeroSkill,
    HeroStrength, HeroSynergy, HeroWeakness, Item,
)
from app.services.gameplay_data import sync_gameplay_catalog, sync_hero_builds, sync_relationships


DETAIL_FILE = Path(__file__).resolve().parents[3] / "data" / "imports" / "official_hero_details.json"
PATCH_VERSION = "official-2026.10.15"

ALIASES = {
    "valhein": ["vanhein", "van", "thợ săn ác quỷ"],
    "nakroth": ["nak", "lưỡi đao phán xét"],
    "butterfly": ["butter", "bướm"],
    "ngo-khong": ["wukong", "tề thiên"],
    "dieu-thuyen": ["dieu thuyen"],
    "trieu-van": ["trieu van"],
    "lu-bo": ["lu bo"],
    "telannas": ["tel", "tel annas"],
    "elandorr": ["elandorr", "eland orr"],
}

WEAKNESS_TITLES = {
    "damage": "Sát thương cơ bản hạn chế", "durability": "Khả năng chống chịu thấp",
    "mobility": "Thiếu cơ động", "crowd_control": "Ít khống chế chủ động",
    "sustain": "Khả năng hồi phục hạn chế", "burst": "Khó dồn sát thương nhanh",
    "teamfight": "Ảnh hưởng giao tranh tổng hạn chế", "split_push": "Đẩy lẻ không nổi bật",
    "pickoff": "Khả năng bắt lẻ hạn chế", "protection": "Ít công cụ bảo vệ đồng đội",
    "objective_control": "Kiểm soát mục tiêu không nổi bật",
}


def _upsert_analysis(db: Session, hero: Hero, result: dict) -> HeroAnalysis:
    analysis = db.scalar(select(HeroAnalysis).where(HeroAnalysis.hero_id == hero.id))
    roles = [role.role for role in hero.roles]
    if not analysis:
        analysis = HeroAnalysis(hero_id=hero.id, patch_version=PATCH_VERSION)
        db.add(analysis)
    analysis.aliases = ALIASES.get(hero.slug, [])
    analysis.primary_role = roles[0] if roles else None
    analysis.secondary_role = roles[1] if len(roles) > 1 else None
    analysis.damage_type = result["damage_type"]
    analysis.range_type = "ranged" if set(roles).intersection({"Xạ thủ", "Pháp sư"}) else "melee"
    analysis.special_mechanics = result["special_mechanics"]
    analysis.data_status = "complete" if result["known_dimensions"] == result["total_dimensions"] else "official_partial_analysis" if result["known_dimensions"] else "official_source_only"
    analysis.confidence = result["confidence"]
    analysis.method_version = METHOD_VERSION
    analysis.patch_version = PATCH_VERSION
    return analysis


def _upsert_rating(db: Session, hero: Hero, result: dict) -> HeroRating:
    rating = db.scalar(select(HeroRating).where(
        HeroRating.hero_id == hero.id,
        HeroRating.method_version == METHOD_VERSION,
        HeroRating.patch_version == PATCH_VERSION,
    ))
    if not rating:
        rating = HeroRating(hero_id=hero.id, method_version=METHOD_VERSION, patch_version=PATCH_VERSION)
        db.add(rating)
    for key, value in result["ratings"].items():
        setattr(rating, key, value)
    rating.explanations = result["explanations"]
    rating.evidence = result["evidence"]
    rating.confidence = result["confidence"]
    rating.provenance = "derived_from_official_skills"
    return rating


def _upsert_explanations(db: Session, hero: Hero, result: dict) -> None:
    for key, score in result["ratings"].items():
        if key not in TITLES or score is None or score < 55:
            continue
        row = db.scalar(select(HeroStrength).where(
            HeroStrength.hero_id == hero.id,
            HeroStrength.attribute_key == key,
            HeroStrength.patch_version == PATCH_VERSION,
        ))
        if not row:
            row = HeroStrength(hero_id=hero.id, attribute_key=key, patch_version=PATCH_VERSION, title=TITLES[key], explanation="")
            db.add(row)
        evidence = result["evidence"].get(key, [])
        row.title = TITLES[key]
        row.explanation = f"Mô tả kỹ năng chính thức có bằng chứng về {', '.join(evidence)}; điểm thuật toán {score}/100."
        row.evidence = evidence
        row.confidence = result["confidence"]
        row.provenance = "derived_from_official_skills"
    for index, weakness in enumerate(hero.weaknesses or []):
        key = f"expert_{index}"
        row = db.scalar(select(HeroWeakness).where(
            HeroWeakness.hero_id == hero.id,
            HeroWeakness.weakness_key == key,
            HeroWeakness.patch_version == PATCH_VERSION,
        ))
        if not row:
            row = HeroWeakness(hero_id=hero.id, weakness_key=key, patch_version=PATCH_VERSION, title=weakness, explanation=weakness)
            db.add(row)
        row.title = weakness
        row.explanation = f"Đánh giá chuyên gia khởi tạo: {weakness}. Cần quản trị viên đối chiếu theo phiên bản."
        row.evidence = []
        row.confidence = 0.45
        row.provenance = "expert_pending_review"

    # Exhaustive official skill descriptions also support limited negative
    # evidence. These rows never turn an unknown numeric rating into a score.
    derived: list[tuple[str, str, str, list[str]]] = []
    skills_text = " ".join(skill.description for skill in hero.skills).casefold()
    roles = {role.role for role in hero.roles}
    if result["ratings"].get("mobility") is None:
        derived.append((
            "kit_no_mobility", "Bộ kỹ năng thiếu cơ chế cơ động rõ ràng",
            "Không phát hiện lướt, nhảy hoặc dịch chuyển trong mô tả kỹ năng chính thức; cần giữ vị trí cẩn thận.",
            ["không có bằng chứng cơ chế lướt/dịch chuyển trong toàn bộ mô tả kỹ năng"],
        ))
    if result["ratings"].get("durability") is None and roles.intersection({"Xạ thủ", "Pháp sư", "Sát thủ"}):
        derived.append((
            "kit_no_defense", "Ít công cụ phòng thủ chủ động",
            "Không phát hiện lá chắn, miễn thương hoặc giảm sát thương trong mô tả kỹ năng; dễ bị dồn sát thương khi sai vị trí.",
            ["không có bằng chứng cơ chế phòng thủ trong toàn bộ mô tả kỹ năng"],
        ))
    if any(term in skills_text for term in ("hướng chỉ định", "định hướng", "phương hướng")):
        derived.append((
            "directional_dependency", "Phụ thuộc độ chính xác kỹ năng định hướng",
            "Mô tả kỹ năng có cơ chế định hướng, nên hiệu quả giảm khi đối thủ né hoặc giữ khoảng cách tốt.",
            ["kỹ năng định hướng trong mô tả chính thức"],
        ))
    if not derived and not (hero.weaknesses or []):
        derived.append((
            "insufficient_weakness", "Chưa đủ dữ liệu để kết luận điểm yếu đặc thù",
            "Nguồn chính thức mô tả bộ kỹ năng nhưng chưa cung cấp đủ chỉ số hoặc điều kiện để kết luận an toàn.",
            [],
        ))
    for key, title, explanation, evidence in derived:
        row = db.scalar(select(HeroWeakness).where(
            HeroWeakness.hero_id == hero.id,
            HeroWeakness.weakness_key == key,
            HeroWeakness.patch_version == PATCH_VERSION,
        ))
        if not row:
            row = HeroWeakness(
                hero_id=hero.id, weakness_key=key, patch_version=PATCH_VERSION,
                title=title, explanation=explanation,
            )
            db.add(row)
        row.title = title
        row.explanation = explanation
        row.evidence = evidence
        row.confidence = 0.55 if evidence else 0
        row.provenance = "derived_negative_evidence" if evidence else "insufficient"


def _upsert_power_spikes(db: Session, hero: Hero, result: dict) -> None:
    phase_map = {"early": "early_game", "mid": "mid_game", "late": "late_game"}
    for phase, key in phase_map.items():
        row = db.scalar(select(HeroPowerSpike).where(
            HeroPowerSpike.hero_id == hero.id,
            HeroPowerSpike.phase == phase,
            HeroPowerSpike.patch_version == PATCH_VERSION,
        ))
        if not row:
            row = HeroPowerSpike(hero_id=hero.id, phase=phase, patch_version=PATCH_VERSION)
            db.add(row)
        row.score = result["ratings"].get(key)
        row.analysis = {"explanation": result["explanations"].get(key, "Chưa đủ dữ liệu.")}
        row.confidence = 0.62 if row.score is not None else 0
        row.provenance = "derived_from_official_skills" if row.score is not None else "insufficient"


def sync_official_details(db: Session, force: bool = False) -> dict:
    if not DETAIL_FILE.exists():
        return {"total": 0, "synced": 0, "analyzed": 0, "missing": 0}
    payload = json.loads(DETAIL_FILE.read_text(encoding="utf-8"))
    expected = len(payload["heroes"])
    version_name = f"{PATCH_VERSION}:{METHOD_VERSION}"
    version_count = db.scalar(select(func.count()).select_from(HeroAnalysisVersion).where(
        HeroAnalysisVersion.version == version_name
    )) or 0
    build_count = db.scalar(select(func.count(func.distinct(HeroRecommendedBuild.hero_id)))) or 0
    if not force and version_count == expected and build_count == expected:
        return {
            "total": expected, "synced": expected, "analyzed": expected,
            "missing": 0, "skipped": True, "reason": "data_version_unchanged",
        }
    synced = analyzed = missing = 0
    for record in payload["heroes"]:
        hero = db.scalar(select(Hero).where(Hero.slug == record["slug"]))
        if not hero:
            missing += 1
            continue
        skills = record.get("skills", [])
        for skill in skills:
            row = db.scalar(select(HeroSkill).where(
                HeroSkill.hero_id == hero.id,
                HeroSkill.order_index == skill["order"],
            ))
            if not row:
                row = HeroSkill(hero_id=hero.id, order_index=skill["order"], name=skill["name"], skill_type=skill["skill_type"], description=skill["description"])
                db.add(row)
            else:
                row.name = skill["name"]
                row.skill_type = skill["skill_type"]
                row.description = skill["description"]
        source = db.scalar(select(HeroDataSource).where(
            HeroDataSource.hero_id == hero.id,
            HeroDataSource.source_url == record["source_url"],
            HeroDataSource.content_hash == record.get("content_hash"),
        ))
        if not source:
            fetched_at = datetime.fromisoformat(record["fetched_at"]) if record.get("fetched_at") else None
            db.add(HeroDataSource(
                hero_id=hero.id, source_url=record["source_url"], source_kind="garena_official_profile",
                fetched_at=fetched_at, content_hash=record.get("content_hash"), verified=bool(skills),
                fields=["name", "roles", "image", "skills"],
            ))
        result = analyze_skill_text(
            skills,
            expert_difficulty=hero.difficulty if hero.patch_version.startswith("bootstrap-") and hero.difficulty > 0 else None,
            expert_phase=hero.power_phase if hero.patch_version.startswith("bootstrap-") and hero.power_phase != "unknown" else None,
            roles=[role.role for role in hero.roles],
        )
        hero.difficulty = max(1, min(10, round(result["ratings"]["difficulty"] / 10)))
        hero.power_phase = max(
            ("early", "mid", "late"),
            key=lambda phase: result["ratings"][f"{phase}_game"],
        )
        tactical_scores = {key: value for key, value in result["ratings"].items() if key in TITLES and value is not None}
        hero.strengths = [TITLES[key] for key, _ in sorted(tactical_scores.items(), key=lambda item: item[1], reverse=True)[:3]]
        hero.weaknesses = [WEAKNESS_TITLES[key] for key, _ in sorted(tactical_scores.items(), key=lambda item: item[1])[:2]]
        _upsert_analysis(db, hero, result)
        _upsert_rating(db, hero, result)
        _upsert_explanations(db, hero, result)
        _upsert_power_spikes(db, hero, result)
        version = db.scalar(select(HeroAnalysisVersion).where(
            HeroAnalysisVersion.hero_id == hero.id,
            HeroAnalysisVersion.version == version_name,
        ))
        if not version:
            db.add(HeroAnalysisVersion(
                hero_id=hero.id, version=version_name,
                status="needs_review",
                summary={"official_skills": len(skills), "known_ratings": result["known_dimensions"], "confidence": result["confidence"]},
            ))
        synced += 1
        if result["known_dimensions"]:
            analyzed += 1
    db.flush()
    catalog_report = sync_gameplay_catalog(db)
    builds = sync_hero_builds(db)
    relationship_report = sync_relationships(db)
    db.commit()
    return {
        "total": len(payload["heroes"]), "synced": synced, "analyzed": analyzed,
        "missing": missing, "catalog": catalog_report, "builds": builds,
        **relationship_report,
    }


def analysis_report(db: Session) -> dict:
    heroes = list(db.scalars(select(Hero)))
    analyses = {row.hero_id: row for row in db.scalars(select(HeroAnalysis))}
    ratings = list(db.scalars(select(HeroRating)))
    sources = list(db.scalars(select(HeroDataSource).where(HeroDataSource.verified.is_(True))))
    verified_hero_ids = {row.hero_id for row in sources}
    score_fields = (
        "damage", "durability", "mobility", "crowd_control", "sustain", "burst",
        "teamfight", "split_push", "pickoff", "protection", "objective_control",
        "early_game", "mid_game", "late_game", "difficulty",
    )
    return {
        "total_heroes": len(heroes),
        "official_source_verified": len(verified_hero_ids),
        "analysis_complete": sum(analyses.get(hero.id) is not None and analyses[hero.id].data_status == "complete" for hero in heroes),
        "partial_analysis": sum(analyses.get(hero.id) is not None and analyses[hero.id].data_status == "official_partial_analysis" for hero in heroes),
        "rated_with_evidence": sum(any(getattr(row, field) is not None for field in score_fields) for row in ratings),
        "fully_rated": sum(all(getattr(row, field) is not None for field in score_fields) for row in ratings),
        "official_skills": len(list(db.scalars(select(HeroSkill.id)))),
        "official_catalog_entries": db.scalar(select(func.count()).select_from(GameplayCatalogEntry)) or 0,
        "active_current_items": db.scalar(select(func.count()).select_from(Item).where(Item.is_active.is_(True))) or 0,
        "heroes_with_weakness_review": db.scalar(select(func.count(func.distinct(HeroWeakness.hero_id)))) or 0,
        "heroes_with_builds": db.scalar(select(func.count(func.distinct(HeroRecommendedBuild.hero_id)))) or 0,
        "synergy_pairs": db.scalar(select(func.count()).select_from(HeroSynergy)) or 0,
        "matchup_pairs_with_evidence": db.scalar(select(func.count()).select_from(HeroMatchup).where(HeroMatchup.advantage_score.is_not(None))) or 0,
        "missing_analysis": sum(hero.id not in analyses for hero in heroes),
        "needs_admin_review": sum(analyses.get(hero.id) is None or analyses[hero.id].data_status != "complete" for hero in heroes),
        "method_version": METHOD_VERSION,
        "patch_version": PATCH_VERSION,
    }
