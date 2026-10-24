from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from statistics import mean
from typing import Iterable

from .analysis_adapter import profile_for
from .hero_rating import matchup_from_ratings


METRICS = (
    "physical_damage", "magic_damage", "durability", "crowd_control", "mobility",
    "engage", "protection", "split_push", "wave_clear", "objective_control",
)

STRATEGY_WEIGHTS = {
    "cân bằng": {metric: 1.0 for metric in METRICS},
    "giao tranh tổng": {"crowd_control": 1.6, "engage": 1.5, "durability": 1.25, "protection": 1.15},
    "bắt lẻ": {"mobility": 1.5, "crowd_control": 1.4, "physical_damage": 1.15, "magic_damage": 1.15},
    "cấu rỉa": {"magic_damage": 1.35, "physical_damage": 1.2, "wave_clear": 1.3, "protection": 1.1},
    "đẩy lẻ": {"split_push": 1.8, "mobility": 1.35, "wave_clear": 1.3},
    "kiểm soát mục tiêu": {"objective_control": 1.8, "durability": 1.25, "crowd_control": 1.2},
    "bảo vệ chủ lực": {"protection": 1.8, "crowd_control": 1.35, "durability": 1.25},
    "nhiều khống chế": {"crowd_control": 2.0, "engage": 1.25},
    "cơ động": {"mobility": 2.0, "split_push": 1.2},
    "chống chịu cao": {"durability": 2.0, "protection": 1.25},
    "mạnh đầu trận": {"objective_control": 1.35, "physical_damage": 1.2, "magic_damage": 1.2},
    "mạnh cuối trận": {"protection": 1.2, "physical_damage": 1.25, "magic_damage": 1.25},
}

POSITION_ROLE_HINTS = {
    "Caesar": {"Đấu sĩ", "Đỡ đòn"},
    "Rừng": {"Sát thủ", "Đấu sĩ"},
    "Giữa": {"Pháp sư"},
    "Rồng": {"Xạ thủ"},
    "Trợ thủ": {"Trợ thủ", "Đỡ đòn"},
}


def clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return round(max(low, min(high, value)), 1)


def attr_dict(hero) -> dict[str, float]:
    """Compatibility view for callers that require numeric values.

    New analysis code uses :func:`evidence_attr_dict`, which preserves unknowns.
    This helper deliberately remains zero-filled for older callers and fixtures.
    """
    return {
        metric: float(value) if value is not None else 0.0
        for metric, value in evidence_attr_dict(hero).items()
    }


def evidence_attr_dict(hero) -> dict[str, float | None]:
    profile = profile_for(hero)
    return {metric: profile.metrics.get(metric) for metric in METRICS}


def role_names(hero) -> set[str]:
    return {role.role for role in hero.roles}


def composition_vector(heroes: Iterable) -> dict[str, float | None]:
    heroes = list(heroes)
    if not heroes:
        return {metric: 0.0 for metric in METRICS}
    rows = [evidence_attr_dict(hero) for hero in heroes]
    vector: dict[str, float | None] = {}
    for metric in METRICS:
        known = [row[metric] for row in rows if row[metric] is not None]
        vector[metric] = round(mean(known), 1) if known else None
    return vector


def composition_analysis(heroes: Iterable) -> dict:
    heroes = list(heroes)
    vector = composition_vector(heroes)
    missing = []
    if vector["durability"] is not None and vector["durability"] < 48:
        missing.append("chống chịu")
    if vector["crowd_control"] is not None and vector["crowd_control"] < 45:
        missing.append("khống chế")
    if vector["engage"] is not None and vector["engage"] < 42:
        missing.append("khả năng mở giao tranh")
    if vector["protection"] is not None and vector["protection"] < 40:
        missing.append("bảo vệ chủ lực")
    physical = vector["physical_damage"]
    magic = vector["magic_damage"]
    damage_balance = "chưa đủ dữ liệu"
    if physical is not None and magic is not None and physical >= magic + 22:
        damage_balance = "thiên sát thương vật lý"
    elif physical is not None and magic is not None and magic >= physical + 22:
        damage_balance = "thiên sát thương phép"
    elif physical is not None and magic is not None:
        damage_balance = "cân bằng"
    elif physical is not None:
        damage_balance = "có bằng chứng sát thương vật lý; thiếu dữ liệu sát thương phép"
    elif magic is not None:
        damage_balance = "có bằng chứng sát thương phép; thiếu dữ liệu sát thương vật lý"

    phases = []
    for hero in heroes:
        profile = profile_for(hero)
        phase_scores = {
            "early": profile.rating_scores.get("early_game"),
            "mid": profile.rating_scores.get("mid_game"),
            "late": profile.rating_scores.get("late_game"),
        }
        known_phases = {key: value for key, value in phase_scores.items() if value is not None}
        if known_phases:
            phases.append(max(known_phases, key=known_phases.get))
        elif profile.source == "legacy_tactical_profile":
            phases.append(getattr(hero, "power_phase", "mid"))
    phase = max(set(phases), key=phases.count) if phases else "chưa xác định"
    missing_evidence = [metric for metric, value in vector.items() if value is None]
    coverage = (len(METRICS) - len(missing_evidence)) / len(METRICS) if heroes else 0.0
    profile_confidence = mean(profile_for(hero).confidence for hero in heroes) if heroes else 0.0
    confidence = min(0.95, profile_confidence * (0.55 + coverage * 0.45))
    if not heroes:
        data_status = "empty"
    elif coverage < 0.35:
        data_status = "insufficient"
    elif missing_evidence:
        data_status = "partial"
    else:
        data_status = "ok"
    return {
        "size": len(heroes),
        "scores": vector,
        "missing": missing,
        "missing_evidence": missing_evidence,
        "damage_balance": damage_balance,
        "dominant_phase": phase,
        "confidence": round(confidence, 2),
        "coverage": round(coverage, 2),
        "data_status": data_status,
        "score_kind": "algorithmic",
    }


def counter_fit_details(candidate, enemies: Iterable) -> dict:
    enemies = list(enemies)
    if not enemies:
        return {"score": None, "confidence": 0.0, "coverage": 0.0, "source": "not_applicable"}
    candidate_profile = profile_for(candidate)
    c = evidence_attr_dict(candidate)
    scores = []
    confidences = []
    sources = []
    for enemy in enemies:
        enemy_profile = profile_for(enemy)
        if candidate_profile.rating_scores and enemy_profile.rating_scores:
            official = matchup_from_ratings(
                dict(candidate_profile.rating_scores), dict(enemy_profile.rating_scores)
            )
            if official["advantage_score"] is not None:
                scores.append(float(official["advantage_score"]))
                confidences.append(float(official["confidence"]))
                sources.append("official_skill_rating")
                continue

        e = evidence_attr_dict(enemy)
        damage_values = [e[key] for key in ("physical_damage", "magic_damage") if e[key] is not None]
        enemy_damage = mean(damage_values) if damage_values else None
        weighted: list[tuple[float, float]] = []
        if c["crowd_control"] is not None and e["mobility"] is not None:
            weighted.append((c["crowd_control"] * e["mobility"] / 100, 0.34))
        if c["durability"] is not None and enemy_damage is not None:
            weighted.append((c["durability"] * enemy_damage / 100, 0.25))
        if c["mobility"] is not None and e["crowd_control"] is not None:
            weighted.append((c["mobility"] * e["crowd_control"] / 100, 0.16))
        if c["protection"] is not None and enemy_damage is not None:
            weighted.append((c["protection"] * enemy_damage / 100, 0.15))
        if len(weighted) < 2:
            continue
        used_weight = sum(weight for _, weight in weighted)
        scores.append(sum(value * weight for value, weight in weighted) / used_weight)
        coverage = used_weight / 0.90
        confidences.append(min(candidate_profile.confidence, enemy_profile.confidence) * coverage)
        sources.append("mapped_tactical_metrics")
    if not scores:
        return {"score": None, "confidence": 0.0, "coverage": 0.0, "source": "insufficient"}
    return {
        "score": clamp(mean(scores)),
        "confidence": round(mean(confidences), 2),
        "coverage": round(len(scores) / len(enemies), 2),
        "source": "official_skill_rating" if all(source == "official_skill_rating" for source in sources) else "mixed_evidence",
    }


def counter_fit(candidate, enemies: Iterable) -> float | None:
    return counter_fit_details(candidate, enemies)["score"]


def synergy_fit(candidate, allies: Iterable) -> float | None:
    allies = list(allies)
    if not allies:
        return None
    before = composition_analysis(allies)
    after = composition_analysis([*allies, candidate])
    filled = len(before["missing"]) - len(after["missing"])
    c = evidence_attr_dict(candidate)
    usable = [
        min(100.0, c[metric] + before["scores"][metric])
        for metric in ("engage", "protection", "crowd_control", "durability")
        if c[metric] is not None and before["scores"][metric] is not None
    ]
    if len(usable) < 2:
        return None
    complement = mean(usable)
    return clamp(complement * 0.7 + 15 + filled * 8)


def strategy_fit(hero, strategy: str) -> float | None:
    attrs = evidence_attr_dict(hero)
    overrides = STRATEGY_WEIGHTS.get(strategy.lower(), STRATEGY_WEIGHTS["cân bằng"])
    weights = {metric: overrides.get(metric, 0.65) for metric in METRICS}
    usable = [(attrs[metric], weights[metric]) for metric in METRICS if attrs[metric] is not None]
    if len(usable) < 3:
        return None
    total = sum(value * weight for value, weight in usable)
    return clamp(total / sum(weight for _, weight in usable))


def role_fit(hero, desired_position: str | None, occupied_positions: set[str] | None = None) -> float:
    if desired_position:
        return 100.0 if desired_position in hero.positions else 12.0
    occupied_positions = occupied_positions or set()
    available = set(hero.positions) - occupied_positions
    return 85.0 if available else 38.0


@dataclass(frozen=True)
class CandidateScore:
    hero: object
    total: float
    counter: float | None
    synergy: float | None
    strategy: float | None
    role: float
    confidence: float
    data_status: str
    evidence_sources: tuple[str, ...]
    missing_components: tuple[str, ...]


def rank_candidates(candidates, allies, enemies, strategy="cân bằng", desired_position=None, mastered_ids=None):
    mastered_ids = set(mastered_ids or [])
    occupied = {position for hero in allies for position in hero.positions[:1]}
    ranked = []
    for hero in candidates:
        counter_result = counter_fit_details(hero, enemies)
        counter = counter_result["score"]
        synergy = synergy_fit(hero, allies)
        tactical = strategy_fit(hero, strategy)
        role = role_fit(hero, desired_position, occupied)
        mastery_bonus = 4.0 if hero.id in mastered_ids else 0.0
        components = {
            "counter": (counter, 0.30),
            "synergy": (synergy, 0.27),
            "strategy": (tactical, 0.25),
            "role": (role, 0.18),
        }
        usable = [(name, value, weight) for name, (value, weight) in components.items() if value is not None]
        # Role alone is not enough to present a tactical recommendation.
        if tactical is None and counter is None and synergy is None:
            continue
        used_weight = sum(weight for _, _, weight in usable)
        total = clamp(sum(value * weight for _, value, weight in usable) / used_weight + mastery_bonus)
        coverage = used_weight / sum(weight for _, weight in components.values())
        profile = profile_for(hero)
        confidence = round(min(0.92, profile.confidence * coverage), 2)
        missing_components = tuple(name for name, (value, _) in components.items() if value is None)
        sources = {profile.source}
        if counter is not None:
            sources.add(counter_result["source"])
        ranked.append(CandidateScore(
            hero, total, counter, synergy, tactical, role, confidence,
            "ok" if not missing_components else "partial",
            tuple(sorted(sources)), missing_components,
        ))
    return sorted(ranked, key=lambda row: row.total, reverse=True)


def synergy_pairs(heroes: Iterable) -> float | None:
    pairs = list(combinations(list(heroes), 2))
    scores = [score for a, b in pairs if (score := synergy_fit(a, [b])) is not None]
    return round(mean(scores), 1) if scores else None

