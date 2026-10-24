from __future__ import annotations

from datetime import datetime
import json as _json
import pathlib as _pathlib
import re

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import InvalidTokenError
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import create_access_token, decode_access_token, hash_password, verify_password
from app.engines.analysis_adapter import load_engine_profiles, profile_for, readiness_payload
from app.engines.build import recommend_items
from app.engines.scoring import composition_analysis, counter_fit, counter_fit_details, rank_candidates
from app.engines.hero_rating import matchup_from_ratings, normalize
from app.engines.strategy import analyze_strategy
from app.engines.macro_engine import analyze_macro_timeline
from app.models import (
    AnalysisHistory, GamePatch, Hero, HeroAnalysis, HeroDataSource, HeroPowerSpike,
    HeroRating, HeroRecommendedBuild, HeroSkill, HeroStrength, HeroSynergy,
    HeroWeakness, Item, MetaStatistic, User,
)
from app.services.hero_analysis import analysis_report, sync_official_details
from app.engines.hero_playbook import build_base_stats, build_combos, build_phase_tips, build_skill_priority
from app.services.gameplay_data import recommend_loadout
from app.services.vision_analysis import analyze_match_image
from app.schemas import (
    BuildRequest,
    CounterRequest,
    DraftRequest,
    LoginRequest,
    MacroTimelineRequest,
    RegisterRequest,
    StrategyRequest,
    TeamCompareRequest,
    TeamGenerateRequest,
)

router = APIRouter(prefix="/api")
security = HTTPBearer(auto_error=False)


def hero_payload(hero: Hero, analysis: HeroAnalysis | None = None) -> dict:
    profile = profile_for(hero)
    readiness = readiness_payload(hero, profile)
    if analysis:
        profile_status = analysis.data_status
    elif profile.source == "official_skill_rating":
        profile_status = "official_partial_analysis"
    elif profile.source == "legacy_tactical_profile":
        profile_status = "tactical_profile"
    else:
        profile_status = "official_roster_only"
    return {
        "id": hero.id,
        "slug": hero.slug,
        "name": hero.name,
        "image_url": hero.image_url,
        "damage_type": hero.damage_type,
        "positions": hero.positions,
        "power_phase": hero.power_phase,
        "difficulty": hero.difficulty,
        "strengths": hero.strengths,
        "weaknesses": hero.weaknesses,
        "patch_version": hero.patch_version,
        "profile_status": profile_status,
        "aliases": analysis.aliases if analysis else [],
        "data_confidence": analysis.confidence if analysis else 0,
        "engine_ready": readiness["engine_ready"],
        "readiness": readiness,
        "roles": [role.role for role in hero.roles],
        "attributes": {
            key: profile.metrics.get(key)
            for key in (
                "physical_damage", "magic_damage", "durability", "crowd_control", "mobility",
                "engage", "protection", "split_push", "wave_clear", "objective_control",
            )
        },
    }


def prepare_heroes(db: Session, heroes: list[Hero]) -> dict[int, HeroAnalysis]:
    """Batch attach transient engine data and return matching analysis rows."""
    unique = {hero.id: hero for hero in heroes}
    if not unique:
        return {}
    analyses = {
        row.hero_id: row
        for row in db.scalars(
            select(HeroAnalysis).where(HeroAnalysis.hero_id.in_(tuple(unique)))
        )
    }
    load_engine_profiles(db, unique.values(), analyses)
    return analyses


def get_heroes(db: Session, ids: list[int], label: str = "tướng") -> list[Hero]:
    if not ids:
        return []
    heroes = list(db.scalars(select(Hero).where(Hero.id.in_(ids))).unique())
    if len(heroes) != len(set(ids)):
        found = {hero.id for hero in heroes}
        missing = sorted(set(ids) - found)
        raise HTTPException(404, f"Không tìm thấy {label}: {missing}")
    order = {hero_id: index for index, hero_id in enumerate(ids)}
    return sorted(heroes, key=lambda hero: order[hero.id])


def get_optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: Session = Depends(get_db),
) -> User | None:
    if not credentials:
        return None
    try:
        payload = decode_access_token(credentials.credentials)
        return db.get(User, int(payload["sub"]))
    except (InvalidTokenError, ValueError, KeyError):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Phiên đăng nhập không hợp lệ")


def require_admin(user: User | None = Depends(get_optional_user)) -> User:
    if not user:
        raise HTTPException(401, "Cần đăng nhập quản trị viên")
    if user.role != "admin":
        raise HTTPException(403, "Tài khoản không có quyền quản trị")
    return user


def rating_payload(row: HeroRating | None) -> dict | None:
    if not row:
        return None
    keys = (
        "damage", "durability", "mobility", "crowd_control", "sustain", "burst",
        "teamfight", "split_push", "pickoff", "protection", "objective_control",
        "early_game", "mid_game", "late_game", "difficulty",
    )
    return {
        "scores": {key: getattr(row, key) for key in keys},
        "explanations": row.explanations,
        "evidence": row.evidence,
        "confidence": row.confidence,
        "provenance": row.provenance,
        "method_version": row.method_version,
        "patch_version": row.patch_version,
        "score_kind": "algorithmic",
    }


def tactical_tier(row: HeroRating | None) -> dict | None:
    if not row:
        return None
    keys = ("damage", "durability", "mobility", "crowd_control", "teamfight", "objective_control")
    values = [float(getattr(row, key)) for key in keys if getattr(row, key) is not None]
    if not values:
        return None
    score = round(sum(values) / len(values), 1)
    tier = "S" if score >= 72 else "A" if score >= 62 else "B" if score >= 52 else "C"
    return {"tier": tier, "score": score, "kind": "algorithmic", "label": "Tier chiến thuật"}


def rating_scores(row: HeroRating) -> dict:
    payload = rating_payload(row)
    return payload["scores"] if payload else {}


def save_history(db: Session, kind: str, request: dict, response: dict, user: User | None = None):
    db.add(AnalysisHistory(
        user_id=user.id if user else None,
        analysis_type=kind,
        input_payload=request,
        output_payload=response,
        patch_version="bootstrap-2026.10",
    ))
    db.commit()


@router.get("/health")
def health(db: Session = Depends(get_db)):
    count = len(list(db.scalars(select(Hero.id))))
    return {"status": "ok", "database": "connected", "heroes": count, "access": "public"}


@router.get("/heroes")
def list_heroes(
    search: str | None = None,
    role: str | None = None,
    position: str | None = None,
    min_difficulty: int | None = Query(None, ge=1, le=10),
    db: Session = Depends(get_db),
):
    statement = select(Hero)
    if search:
        statement = statement.where(or_(Hero.name.ilike(f"%{search}%"), Hero.slug.ilike(f"%{search}%")))
    if position:
        statement = statement.where(Hero.positions.contains(position))
    if min_difficulty:
        statement = statement.where(Hero.difficulty >= min_difficulty)
    heroes = list(db.scalars(statement.order_by(Hero.name)).unique())
    if role:
        heroes = [hero for hero in heroes if role in {item.role for item in hero.roles}]
    analysis_by_hero = prepare_heroes(db, heroes)
    return {"items": [hero_payload(hero, analysis_by_hero.get(hero.id)) for hero in heroes], "total": len(heroes)}


@router.get("/heroes/search")
def search_heroes(
    q: str = Query("", max_length=100),
    role: str | None = None,
    position: str | None = None,
    damage_type: str | None = None,
    max_difficulty: int | None = Query(None, ge=0, le=10),
    limit: int = Query(20, ge=1, le=129),
    db: Session = Depends(get_db),
):
    heroes = list(db.scalars(select(Hero).order_by(Hero.name)).unique())
    analyses = {row.hero_id: row for row in db.scalars(select(HeroAnalysis))}
    load_engine_profiles(db, heroes, analyses)
    needle = normalize(q.strip())
    results = []
    for hero in heroes:
        analysis = analyses.get(hero.id)
        searchable = [hero.name, hero.slug, *(analysis.aliases if analysis else [])]
        if needle and not any(needle in normalize(value) for value in searchable):
            continue
        if role and role not in {item.role for item in hero.roles}:
            continue
        if position and position not in hero.positions:
            continue
        resolved_damage = analysis.damage_type if analysis and analysis.damage_type else hero.damage_type
        if damage_type and resolved_damage != damage_type:
            continue
        if max_difficulty is not None and hero.difficulty > max_difficulty:
            continue
        results.append(hero_payload(hero, analysis))
        if len(results) >= limit:
            break
    return {"items": results, "total": len(results), "query": q}


@router.get("/heroes/{hero_id}")
def hero_detail(hero_id: int, db: Session = Depends(get_db)):
    hero = db.get(Hero, hero_id)
    if not hero:
        raise HTTPException(404, "Không tìm thấy tướng")
    analysis = db.scalar(select(HeroAnalysis).where(HeroAnalysis.hero_id == hero_id))
    load_engine_profiles(db, [hero], {hero_id: analysis} if analysis else {})
    return hero_payload(hero, analysis)


@router.get("/heroes/{hero_id}/analysis")
def hero_analysis_detail(hero_id: int, db: Session = Depends(get_db)):
    hero = db.get(Hero, hero_id)
    if not hero:
        raise HTTPException(404, "Không tìm thấy tướng")
    analysis = db.scalar(select(HeroAnalysis).where(HeroAnalysis.hero_id == hero_id))
    load_engine_profiles(db, [hero], {hero_id: analysis} if analysis else {})
    rating = db.scalar(select(HeroRating).where(HeroRating.hero_id == hero_id).order_by(HeroRating.created_at.desc()))
    skills = list(db.scalars(select(HeroSkill).where(HeroSkill.hero_id == hero_id).order_by(HeroSkill.order_index)))
    strengths = list(db.scalars(select(HeroStrength).where(HeroStrength.hero_id == hero_id)))
    weaknesses = list(db.scalars(select(HeroWeakness).where(HeroWeakness.hero_id == hero_id)))
    spikes = list(db.scalars(select(HeroPowerSpike).where(HeroPowerSpike.hero_id == hero_id)))
    spikes.sort(key=lambda row: {"early": 0, "mid": 1, "late": 2}.get(row.phase, 9))
    return {
        "hero": hero_payload(hero, analysis),
        "analysis": None if not analysis else {
            "damage_type": analysis.damage_type, "range_type": analysis.range_type,
            "special_mechanics": analysis.special_mechanics, "data_status": analysis.data_status,
            "confidence": analysis.confidence, "method_version": analysis.method_version,
            "patch_version": analysis.patch_version,
        },
        "skills": [{"id": row.id, "name": row.name, "type": row.skill_type, "description": row.description, "order": row.order_index} for row in skills],
        "skill_priority": build_skill_priority(skills),
        "combos": build_combos(skills),
        "base_stats": build_base_stats(hero, rating),
        "gameplay_tips": build_phase_tips(hero, rating),
        "ratings": rating_payload(rating),
        "tier": tactical_tier(rating),
        "strengths": [{"title": row.title, "explanation": row.explanation, "evidence": row.evidence, "confidence": row.confidence, "provenance": row.provenance} for row in strengths],
        "weaknesses": [{"title": row.title, "explanation": row.explanation, "evidence": row.evidence, "confidence": row.confidence, "provenance": row.provenance} for row in weaknesses],
        "power_spikes": [{"phase": row.phase, "score": row.score, "analysis": row.analysis, "confidence": row.confidence, "provenance": row.provenance} for row in spikes],
    }


@router.get("/heroes/{hero_id}/ratings")
def hero_ratings(hero_id: int, db: Session = Depends(get_db)):
    if not db.get(Hero, hero_id):
        raise HTTPException(404, "Không tìm thấy tướng")
    row = db.scalar(select(HeroRating).where(HeroRating.hero_id == hero_id).order_by(HeroRating.created_at.desc()))
    return rating_payload(row) or {"status": "insufficient", "message": "Chưa đủ dữ liệu để chấm điểm"}


@router.get("/heroes/{hero_id}/strengths")
def hero_strengths(hero_id: int, db: Session = Depends(get_db)):
    rows = list(db.scalars(select(HeroStrength).where(HeroStrength.hero_id == hero_id)))
    return {"items": [{"title": row.title, "explanation": row.explanation, "evidence": row.evidence, "confidence": row.confidence, "provenance": row.provenance} for row in rows]}


@router.get("/heroes/{hero_id}/weaknesses")
def hero_weaknesses(hero_id: int, db: Session = Depends(get_db)):
    rows = list(db.scalars(select(HeroWeakness).where(HeroWeakness.hero_id == hero_id)))
    return {"items": [{"title": row.title, "explanation": row.explanation, "evidence": row.evidence, "confidence": row.confidence, "provenance": row.provenance} for row in rows], "message": None if rows else "Chưa có điểm yếu đủ căn cứ; cần quản trị viên phân tích."}


@router.get("/heroes/{hero_id}/power-spikes")
def hero_power_spikes(hero_id: int, db: Session = Depends(get_db)):
    rows = list(db.scalars(select(HeroPowerSpike).where(HeroPowerSpike.hero_id == hero_id)))
    rows.sort(key=lambda row: {"early": 0, "mid": 1, "late": 2}.get(row.phase, 9))
    return {"items": [{"phase": row.phase, "score": row.score, "analysis": row.analysis, "confidence": row.confidence, "provenance": row.provenance} for row in rows]}


@router.get("/heroes/{hero_id}/builds")
def hero_builds(hero_id: int, db: Session = Depends(get_db)):
    rows = list(db.scalars(select(HeroRecommendedBuild).where(HeroRecommendedBuild.hero_id == hero_id)))
    item_ids = {item_id for row in rows for item_id in (row.item_ids or [])}
    item_map = {item.id: item for item in db.scalars(select(Item).where(Item.id.in_(item_ids)))} if item_ids else {}
    return {"items": [{
        "position": row.position, "situation": row.situation, "item_ids": row.item_ids,
        "items": [{
            "id": item.id, "name": item.name, "image_url": (item.attributes or {}).get("_image_url"),
            "category": item.category,
        } for item_id in (row.item_ids or []) if (item := item_map.get(item_id))],
        "arcana": row.arcana, "enchantments": row.enchantments, "talent": row.talent,
        "explanation": row.explanation, "data_status": row.data_status,
        "confidence": row.confidence, "provenance": row.provenance,
        "source_url": row.source_url, "patch_version": row.patch_version,
    } for row in rows], "message": None if rows else "Chưa có bộ trang bị đã đối chiếu phiên bản cho tướng này."}


@router.get("/heroes/{hero_id}/synergies")
def hero_synergies(hero_id: int, db: Session = Depends(get_db)):
    rows = list(db.scalars(select(HeroSynergy).where(or_(HeroSynergy.hero_a_id == hero_id, HeroSynergy.hero_b_id == hero_id))))
    return {"items": [{"partner_id": row.hero_b_id if row.hero_a_id == hero_id else row.hero_a_id, "score": row.score, "confidence": row.confidence, "reason": row.reason, "patch_version": row.patch_version} for row in rows], "message": None if rows else "Chưa có quan hệ phối hợp đã đủ căn cứ."}


@router.get("/heroes/{hero_id}/counters-legacy", include_in_schema=False)
def hero_counters(hero_id: int, db: Session = Depends(get_db)):
    # Compatibility alias; it intentionally uses the same evidence checks as
    # the public endpoint and no longer filters the roster by legacy difficulty.
    return hero_counters_from_official_skills(hero_id, db)


@router.get("/heroes/{hero_id}/counters")
def hero_counters_from_official_skills(hero_id: int, db: Session = Depends(get_db)):
    heroes = list(db.scalars(select(Hero)).unique())
    by_id = {hero.id: hero for hero in heroes}
    target = by_id.get(hero_id)
    if not target:
        raise HTTPException(404, "Không tìm thấy tướng")
    analyses = prepare_heroes(db, heroes)
    target_profile = profile_for(target)
    rows = []
    for candidate in heroes:
        if candidate.id == hero_id:
            continue
        candidate_profile = profile_for(candidate)
        result = matchup_from_ratings(
            dict(candidate_profile.rating_scores), dict(target_profile.rating_scores)
        ) if candidate_profile.rating_scores and target_profile.rating_scores else {
            "advantage_score": None, "confidence": 0.0, "reasons": [], "conditions": []
        }
        if result["advantage_score"] is None:
            mapped = counter_fit_details(candidate, [target])
            if mapped["score"] is None:
                continue
            result = {
                "advantage_score": mapped["score"],
                "confidence": mapped["confidence"],
                "reasons": ["So sánh từ các thuộc tính chiến thuật có bằng chứng chung."],
                "conditions": ["Kết quả phụ thuộc vị trí, tài nguyên và thời điểm kỹ năng."],
            }
        rows.append((result, candidate))
    rows.sort(key=lambda row: row[0]["advantage_score"], reverse=True)
    return {
        "target": hero_payload(target, analyses.get(hero_id)),
        "counters": [{
            "hero": hero_payload(hero, analyses.get(hero.id)),
            "algorithmic_score": result["advantage_score"],
            "confidence": result["confidence"],
            "reasons": result["reasons"],
            "conditions": result["conditions"],
        } for result, hero in rows[:5]],
        "status": "ok" if rows else "insufficient",
        "message": None if rows else "Chưa có ít nhất ba cặp thuộc tính đối ứng có bằng chứng để xếp hạng khắc chế.",
        "notice": "Điểm đối kháng suy ra từ kỹ năng chính thức; không phải tỷ lệ thắng thực tế.",
    }


def draft_response(body: DraftRequest, db: Session) -> dict:
    allies = get_heroes(db, body.ally_ids, "tướng đồng minh")
    enemies = get_heroes(db, body.enemy_ids, "tướng đối phương")
    excluded = set(body.ally_ids + body.enemy_ids + body.banned_ids)
    candidates = [hero for hero in db.scalars(select(Hero)).unique() if hero.id not in excluded]
    analyses = prepare_heroes(db, [*allies, *enemies, *candidates])
    ranked = rank_candidates(
        candidates, allies, enemies, body.strategy, body.desired_position, body.mastered_hero_ids
    )[:5]
    recommendations = []
    for row in ranked:
        benefits = []
        if row.counter is not None and row.counter >= 60:
            benefits.append("có bộ chỉ số phù hợp để gây áp lực lên đội hình địch")
        if row.synergy is not None and row.synergy >= 60:
            benefits.append("bổ sung tốt các khoảng trống của đồng minh")
        if row.role >= 80:
            benefits.append("phù hợp vị trí đang cần")
        recommendations.append({
            "hero": hero_payload(row.hero, analyses.get(row.hero.id)),
            "fit_score": row.total,
            "counter_score": row.counter,
            "synergy_score": row.synergy,
            "strategy_score": row.strategy,
            "role_score": row.role,
            "confidence": row.confidence,
            "data_status": row.data_status,
            "evidence_sources": row.evidence_sources,
            "missing_components": row.missing_components,
            "advantages": benefits or ["phương án cân bằng theo trọng số hiện tại"],
            "risks": row.hero.weaknesses[:2],
            "explanation": "Điểm được chuẩn hóa trên các thành phần có bằng chứng; thành phần còn thiếu không bị quy thành 0.",
        })
    ally_analysis = composition_analysis(allies)
    enemy_analysis = composition_analysis(enemies)
    partial = any(row.data_status != "ok" for row in ranked) or any(
        result["data_status"] in {"partial", "insufficient"}
        for result in (ally_analysis, enemy_analysis)
    )
    return {
        "recommendations": recommendations,
        "ally_analysis": ally_analysis,
        "enemy_analysis": enemy_analysis,
        "status": "insufficient" if not recommendations else "partial" if partial else "ok",
        "message": (
            "Chưa có ứng viên đủ bằng chứng để xếp hạng."
            if not recommendations else
            "Một số thành phần chưa đủ bằng chứng và đã được loại khỏi phép tính."
            if partial else None
        ),
        "score_kind": "algorithmic",
        "notice": "Điểm phù hợp là kết quả thuật toán, không phải xác suất thắng.",
    }


@router.post("/draft/analyze")
@router.post("/draft/recommend")
def analyze_draft(body: DraftRequest, db: Session = Depends(get_db), user: User | None = Depends(get_optional_user)):
    response = draft_response(body, db)
    save_history(db, "draft", body.model_dump(), response, user)
    return response


@router.post("/team/generate")
def generate_team(body: TeamGenerateRequest, db: Session = Depends(get_db)):
    team = get_heroes(db, body.locked_hero_ids, "tướng đã khóa")
    enemies = get_heroes(db, body.enemy_ids, "tướng đối phương")
    all_heroes = list(db.scalars(select(Hero)).unique())
    analyses = prepare_heroes(db, all_heroes)
    # A banned hero must never re-enter the candidate pool. This guard lives
    # in the backend as well as the picker so crafted requests remain safe.
    used = {hero.id for hero in [*team, *enemies]} | set(body.banned_ids)
    positions = ["Caesar", "Rừng", "Giữa", "Rồng", "Trợ thủ"]
    occupied = {hero.positions[0] for hero in team if hero.positions}
    for position in positions:
        if len(team) >= 5:
            break
        if position in occupied:
            continue
        candidates = [hero for hero in all_heroes if hero.id not in used]
        ranked = rank_candidates(candidates, team, enemies, body.strategy, position)
        if ranked:
            chosen = ranked[0].hero
            team.append(chosen)
            used.add(chosen.id)
            occupied.add(position)
    analysis = composition_analysis(team)
    complete = len(team) == 5
    return {
        "team": [hero_payload(hero, analyses.get(hero.id)) for hero in team],
        "analysis": analysis,
        "strategy": body.strategy,
        "banned_ids": body.banned_ids,
        "complete": complete,
        "status": "insufficient" if not complete else "partial" if analysis["data_status"] != "ok" else "ok",
        "message": (
            "Không còn đủ ứng viên có bằng chứng chiến thuật cho các vị trí còn thiếu."
            if not complete else
            "Đội hình đã tạo; một số chỉ số còn thiếu bằng chứng và không được tính là 0."
            if analysis["data_status"] != "ok" else None
        ),
    }


@router.post("/team/compare")
def compare_teams(body: TeamCompareRequest, db: Session = Depends(get_db)):
    team_a = get_heroes(db, body.team_a_ids, "đội A")
    team_b = get_heroes(db, body.team_b_ids, "đội B")
    prepare_heroes(db, [*team_a, *team_b])
    a = composition_analysis(team_a)
    b = composition_analysis(team_b)
    a_engage, b_engage = a["scores"]["engage"], b["scores"]["engage"]
    if a_engage is None or b_engage is None:
        team_a_condition = team_b_condition = "Chưa đủ bằng chứng mở giao tranh để so sánh"
    else:
        team_a_condition = "Chủ động giao tranh" if a_engage > b_engage else "Kéo giãn và phản giao tranh"
        team_b_condition = "Chủ động giao tranh" if b_engage > a_engage else "Kéo giãn và phản giao tranh"
    partial = a["data_status"] != "ok" or b["data_status"] != "ok"
    return {
        "team_a": a,
        "team_b": b,
        "team_a_condition": team_a_condition,
        "team_b_condition": team_b_condition,
        "status": "partial" if partial else "ok",
        "message": "Một số chỉ số không được so sánh do thiếu bằng chứng." if partial else None,
        "notice": "So sánh thuộc tính chiến thuật, không dự đoán tỷ lệ thắng.",
    }


@router.post("/counter/analyze")
def analyze_counter(body: CounterRequest, db: Session = Depends(get_db)):
    hero = get_heroes(db, [body.hero_id])[0]
    lane_condition = f"Kèo {body.position}: ưu tiên trao đổi chiêu và kiểm soát tài nguyên đúng vị trí." if body.position else None
    if body.opponent_id:
        if body.opponent_id == body.hero_id:
            raise HTTPException(422, "Hai phía đối đầu phải là hai tướng khác nhau")
        opponent = get_heroes(db, [body.opponent_id])[0]
        analyses = prepare_heroes(db, [hero, opponent])
        hero_profile, opponent_profile = profile_for(hero), profile_for(opponent)
        hero_result = matchup_from_ratings(
            dict(hero_profile.rating_scores), dict(opponent_profile.rating_scores)
        )
        opponent_result = matchup_from_ratings(
            dict(opponent_profile.rating_scores), dict(hero_profile.rating_scores)
        )
        if hero_result["advantage_score"] is None or opponent_result["advantage_score"] is None:
            hero_mapped = counter_fit_details(hero, [opponent])
            opponent_mapped = counter_fit_details(opponent, [hero])
            if hero_mapped["score"] is None or opponent_mapped["score"] is None:
                return {
                    "hero": hero_payload(hero, analyses.get(hero.id)),
                    "opponent": hero_payload(opponent, analyses.get(opponent.id)),
                    "hero_advantage": None,
                    "opponent_advantage": None,
                    "conditions": ([lane_condition] if lane_condition else []) + hero_result["conditions"],
                    "position": body.position,
                    "confidence": 0.0,
                    "status": "insufficient",
                    "message": "Hai tướng chưa có ít nhất ba cặp thuộc tính đối ứng có bằng chứng.",
                    "score_kind": "algorithmic",
                }
            return {
                "hero": hero_payload(hero, analyses.get(hero.id)),
                "opponent": hero_payload(opponent, analyses.get(opponent.id)),
                "hero_advantage": hero_mapped["score"],
                "opponent_advantage": opponent_mapped["score"],
                "conditions": ([lane_condition] if lane_condition else []) + ["Dùng các thuộc tính chiến thuật có bằng chứng chung vì rating đối ứng chưa đủ ba cặp."],
                "position": body.position,
                "confidence": min(hero_mapped["confidence"], opponent_mapped["confidence"]),
                "status": "partial",
                "message": "Kết quả dùng adapter chiến thuật và không quy dữ liệu thiếu thành 0.",
                "score_kind": "algorithmic",
            }
        return {
            "hero": hero_payload(hero, analyses.get(hero.id)),
            "opponent": hero_payload(opponent, analyses.get(opponent.id)),
            "hero_advantage": hero_result["advantage_score"],
            "opponent_advantage": opponent_result["advantage_score"],
            "hero_reasons": hero_result["reasons"],
            "opponent_reasons": opponent_result["reasons"],
            "confidence": min(hero_result["confidence"], opponent_result["confidence"]),
            "conditions": ([lane_condition] if lane_condition else []) + hero_result["conditions"],
            "position": body.position,
            "status": "ok",
            "message": None,
            "score_kind": "algorithmic",
        }
    candidates = [item for item in db.scalars(select(Hero)).unique() if item.id != hero.id]
    analyses = prepare_heroes(db, [hero, *candidates])
    ranked = []
    for candidate in candidates:
        result = counter_fit_details(candidate, [hero])
        if result["score"] is not None:
            ranked.append((result, candidate))
    ranked.sort(key=lambda row: row[0]["score"], reverse=True)
    return {
        "target": hero_payload(hero, analyses.get(hero.id)),
        "counters": [{
            "hero": hero_payload(candidate, analyses.get(candidate.id)),
            "algorithmic_score": result["score"],
            "confidence": result["confidence"],
            "source": result["source"],
        } for result, candidate in ranked[:5]],
        "status": "ok" if ranked else "insufficient",
        "message": None if ranked else "Chưa đủ cặp thuộc tính có bằng chứng để xếp hạng tướng khắc chế.",
        "score_kind": "algorithmic",
    }


@router.post("/build/recommend")
def build_recommendation(body: BuildRequest, db: Session = Depends(get_db)):
    hero = get_heroes(db, [body.hero_id])[0]
    enemies = get_heroes(db, body.enemy_ids, "tướng đối phương")
    allies = get_heroes(db, body.ally_ids, "tướng đồng minh")
    prepare_heroes(db, [hero, *enemies, *allies])
    items = list(db.scalars(select(Item).where(Item.is_active.is_(True))))
    response = recommend_items(hero, enemies, items, body.phase, body.playstyle)
    response["position"] = body.position
    response["loadout"] = recommend_loadout(hero, body.position, body.phase, body.playstyle)
    response["ally_context"] = {
        "hero_ids": [ally.id for ally in allies],
        "note": "Đồng minh được xác nhận trong ngữ cảnh; engine hiện chỉ đổi trang bị theo mối đe dọa địch và vai trò tướng.",
    }
    return response


@router.post("/strategy/analyze")
def strategy_analysis(body: StrategyRequest, db: Session = Depends(get_db)):
    allies = get_heroes(db, body.ally_ids, "tướng đồng minh")
    enemies = get_heroes(db, body.enemy_ids, "tướng đối phương")
    prepare_heroes(db, [*allies, *enemies])
    return analyze_strategy(allies, enemies, body.phase)


@router.post("/strategy/macro-timeline")
def macro_timeline_analysis(body: MacroTimelineRequest, db: Session = Depends(get_db)):
    allies = get_heroes(db, body.ally_ids, "đội ta")
    enemies = get_heroes(db, body.enemy_ids, "đội địch")
    analyses = prepare_heroes(db, [*allies, *enemies])
    return analyze_macro_timeline(
        allies, enemies, body.timeline_phase,
        hero_payload=lambda hero: hero_payload(hero, analyses.get(hero.id)),
        ally_positions=body.ally_positions,
        enemy_positions=body.enemy_positions,
        enemy_start_buff=body.enemy_start_buff,
        ally_side=body.ally_side,
    )


@router.get("/meta/heroes")
def meta_heroes(db: Session = Depends(get_db)):
    rows = list(db.scalars(select(MetaStatistic).where(MetaStatistic.verified.is_(True))))
    if not rows:
        meta_file = _pathlib.Path(__file__).resolve().parents[3] / "data" / "imports" / "tournament_meta_2026.json"
        if not meta_file.exists():
            return {
                "status": "unavailable", "message": "Chưa có dữ liệu trận đấu có nguồn",
                "items": [], "policy": "Chỉ hiển thị tỷ lệ khi có nguồn, cỡ mẫu và thời điểm thu thập.",
            }
        snapshot = _json.loads(meta_file.read_text(encoding="utf-8"))
        heroes = list(db.scalars(select(Hero).order_by(Hero.name)).unique())

        def meta_key(value: str) -> str:
            value = re.sub(r"\s*\([^)]*\)\s*", "", normalize(value))
            compact = "".join(character for character in value if character.isalnum())
            return {"wirosableng": "wiro", "riktor": "richter", "jinnar": "jinna", "zanis": "trieuvan"}.get(compact, compact)

        aggregates: dict[str, dict] = {}
        for statistic in snapshot["heroes"]:
            key = meta_key(statistic["name"])
            row = aggregates.setdefault(key, {
                "source_rank": statistic["source_rank"], "picks": 0, "wins": 0, "losses": 0,
                "bans": 0, "source_names": [],
            })
            row["source_rank"] = min(row["source_rank"], statistic["source_rank"])
            for field in ("picks", "wins", "losses", "bans"):
                row[field] += statistic[field]
            row["source_names"].append(statistic["name"])

        items = []
        for hero in heroes:
            statistic = aggregates.get(meta_key(hero.name))
            if statistic:
                picks, bans = statistic["picks"], statistic["bans"]
                win_rate = round(statistic["wins"] / picks * 100, 2) if picks else None
                pick_rate = round(picks / snapshot["sample_games"] * 100, 2)
                ban_rate = round(bans / snapshot["sample_games"] * 100, 2)
                presence = round((picks + bans) / snapshot["sample_games"] * 100, 2)
                reliable_win_rate = 50 + ((win_rate or 50) - 50) * min(1, picks / 20)
                meta_score = round(presence * 0.7 + reliable_win_rate * 0.3, 1)
                values = {**statistic, "win_rate": win_rate, "pick_rate": pick_rate, "ban_rate": ban_rate, "presence": presence, "meta_score": meta_score, "played": True}
            else:
                values = {"source_rank": None, "picks": 0, "wins": 0, "losses": 0, "bans": 0, "source_names": [], "win_rate": None, "pick_rate": 0.0, "ban_rate": 0.0, "presence": 0.0, "meta_score": 0.0, "played": False}
            items.append({
                **values,
                "hero": {"id": hero.id, "name": hero.name, "slug": hero.slug, "image_url": hero.image_url, "roles": [role.role for role in hero.roles]},
                "sample_games": snapshot["sample_games"],
            })
        items.sort(key=lambda item: item["meta_score"], reverse=True)
        return {
            "status": "public_match_data",
            "message": "Thống kê giải đấu công khai được tìm thấy qua Google và đối chiếu với roster trong hệ thống.",
            "items": items,
            "tournament": snapshot["tournament"],
            "stage": snapshot["stage"],
            "sample_games": snapshot["sample_games"],
            "captured_at": snapshot["captured_at"],
            "source_status": snapshot["source_status"],
            "source": snapshot["source"],
            "method": snapshot["method"],
            "total_heroes": len(items),
            "heroes_with_matches": sum(item["played"] for item in items),
            "heroes_without_matches": sum(not item["played"] for item in items),
            "policy": "Số liệu trận đấu và điểm tổng hợp được hiển thị riêng; điểm meta không phải tỷ lệ thắng.",
        }
    return {"status": "verified", "items": [{
        "hero_id": row.hero_id,
        "patch_version": row.patch_version,
        "rank_tier": row.rank_tier,
        "sample_size": row.sample_size,
        "win_rate": row.win_rate,
        "pick_rate": row.pick_rate,
        "ban_rate": row.ban_rate,
        "source_id": row.source_id,
        "verified": row.verified,
    } for row in rows]}


@router.get("/patches")
def patches(db: Session = Depends(get_db)):
    return [{
        "id": patch.id,
        "version": patch.version,
        "title": patch.title,
        "released_at": patch.released_at,
        "is_current": patch.is_current,
        "source_url": patch.source_url,
    } for patch in db.scalars(select(GamePatch).order_by(GamePatch.created_at.desc()))]


_CATALOG_FILE = _pathlib.Path(__file__).resolve().parents[3] / "data" / "imports" / "official_gameplay_catalog.json"
_catalog_cache: dict | None = None


@router.get("/gameplay-catalog")
def gameplay_catalog(section: str | None = None):
    """Official Garena gameplay catalog: equipment, runes, talents, enchantments."""
    global _catalog_cache
    if _catalog_cache is None:
        if not _CATALOG_FILE.exists():
            return {"status": "unavailable", "message": "Chưa có catalog chính thức. Chạy scripts/sync_official_gameplay_catalog.py."}
        _catalog_cache = _json.loads(_CATALOG_FILE.read_text(encoding="utf-8"))
    payload = _catalog_cache
    valid_sections = ("equipment", "runes", "talents", "enchantment_families", "enchantments")
    if section and section in valid_sections:
        return {"section": section, "items": payload.get(section, []), "generated_at": payload.get("generated_at")}
    return {
        "generated_at": payload.get("generated_at"),
        "scope": payload.get("scope"),
        "sources": payload.get("sources"),
        "counts": {key: len(payload.get(key, [])) for key in valid_sections},
    }


@router.post("/vision/analyze")
async def vision_analyze(file: UploadFile = File(...)):
    if file.content_type not in {"image/png", "image/jpeg", "image/webp"}:
        raise HTTPException(415, "Chỉ hỗ trợ ảnh PNG, JPEG hoặc WebP")
    content = await file.read()
    if len(content) > 8 * 1024 * 1024:
        raise HTTPException(413, "Ảnh vượt quá giới hạn 8 MB")
    try:
        return analyze_match_image(content, file.filename)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@router.post("/auth/register", status_code=201)
def register(body: RegisterRequest, db: Session = Depends(get_db)):
    email = body.email.lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(409, "Email đã được sử dụng")
    user = User(email=email, display_name=body.display_name, password_hash=hash_password(body.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"access_token": create_access_token(user.id, user.role), "token_type": "bearer", "user": {"id": user.id, "display_name": user.display_name, "role": user.role}}


@router.post("/auth/login")
def login(body: LoginRequest, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == body.email.lower()))
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(401, "Email hoặc mật khẩu không đúng")
    return {"access_token": create_access_token(user.id, user.role), "token_type": "bearer", "user": {"id": user.id, "display_name": user.display_name, "role": user.role}}


@router.get("/history")
def history():
    return {
        "items": [],
        "storage": "browser_local",
        "message": "Hệ thống công khai không yêu cầu tài khoản; lịch sử cá nhân chỉ lưu trong trình duyệt.",
    }


@router.post("/admin/heroes/sync")
@router.post("/admin/heroes/analyze")
def admin_sync_hero_analysis(
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Import the audited local official snapshot and rerun deterministic analysis."""
    return {"status": "ok", "sync": sync_official_details(db, force=True), "report": analysis_report(db)}


@router.get("/admin/heroes/report")
def admin_hero_report(
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return analysis_report(db)

