"""Bridge evidence-backed ``HeroRating`` rows to the legacy tactical engines.

The original scoring modules consume ten tactical metrics from ``HeroAttribute``.
Official hero profiles provide a smaller, nullable set of dimensions instead.
This adapter keeps unknown values as ``None`` and only derives a legacy metric
when there is a direct, explainable mapping.  It never persists inferred values
and therefore cannot overwrite the stable hero records or their IDs.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import HeroAnalysis, HeroRating


TACTICAL_METRICS = (
    "physical_damage", "magic_damage", "durability", "crowd_control", "mobility",
    "engage", "protection", "split_push", "wave_clear", "objective_control",
)
RATING_METRICS = (
    "damage", "durability", "mobility", "crowd_control", "sustain", "burst",
    "teamfight", "split_push", "pickoff", "protection", "objective_control",
    "early_game", "mid_game", "late_game", "difficulty",
)
COUNTER_DIMENSIONS = (
    "mobility", "crowd_control", "durability", "burst", "sustain", "pickoff",
)


@dataclass(frozen=True)
class EngineProfile:
    """Transient data supplied to scoring engines for one hero."""

    metrics: Mapping[str, float | None]
    rating_scores: Mapping[str, float | None]
    confidence: float
    source: str
    damage_type: str | None
    method_version: str
    known_metrics: tuple[str, ...]
    evidence: Mapping[str, object]

    def readiness(self, has_roles: bool = True, has_positions: bool = True) -> dict[str, bool]:
        known = set(self.known_metrics)
        composition = (
            len(known) >= 4
            and bool(known & {"physical_damage", "magic_damage"})
            and bool(known & {"durability", "crowd_control", "mobility", "protection"})
        )
        counter_known = sum(
            self.rating_scores.get(key) is not None for key in COUNTER_DIMENSIONS
        )
        # Counter readiness is only a per-hero hint. A concrete matchup still
        # checks that the two heroes have at least three usable cross-pairs.
        counter = counter_known >= 3 or self.source == "legacy_tactical_profile"
        return {
            "composition": composition,
            "draft": composition and has_positions,
            "team": composition and has_positions,
            "counter": counter,
            "build": has_roles,
            "strategy": composition,
            "coach": composition,
        }


def _number(value) -> float | None:
    return float(value) if value is not None else None


def _legacy_profile(hero) -> EngineProfile:
    attrs = getattr(hero, "attributes", None)
    metrics = {
        key: _number(getattr(attrs, key, None)) if attrs is not None else None
        for key in TACTICAL_METRICS
    }
    # Roster-only placeholders are stored as zeroes. They are not evidence.
    # Plain objects used by engine consumers/tests may not expose difficulty;
    # the presence of a populated attributes object is then the legacy signal.
    if hasattr(hero, "difficulty") and getattr(hero, "difficulty", 0) <= 0:
        metrics = {key: None for key in TACTICAL_METRICS}
    known = tuple(key for key, value in metrics.items() if value is not None)
    return EngineProfile(
        metrics=metrics,
        rating_scores={},
        confidence=0.72 if known else 0.0,
        source="legacy_tactical_profile" if known else "insufficient",
        damage_type=getattr(hero, "damage_type", None),
        method_version="legacy-tactical-v1" if known else "none",
        known_metrics=known,
        evidence={},
    )


def _rating_profile(hero, rating: HeroRating, analysis: HeroAnalysis | None) -> EngineProfile:
    scores = {key: _number(getattr(rating, key, None)) for key in RATING_METRICS}
    damage_type = (
        getattr(analysis, "damage_type", None)
        or getattr(hero, "damage_type", None)
        or None
    )
    damage = scores["damage"]
    physical_damage: float | None = None
    magic_damage: float | None = None
    if damage_type == "physical":
        physical_damage = damage
    elif damage_type == "magic":
        magic_damage = damage
    elif damage_type == "mixed":
        # The official descriptions explicitly contain both damage types. The
        # aggregate damage rating is consequently exposed to both channels.
        physical_damage = damage
        magic_damage = damage

    crowd_control = scores["crowd_control"]
    teamfight = scores["teamfight"]
    engage = (
        round((crowd_control + teamfight) / 2, 1)
        if crowd_control is not None and teamfight is not None
        else None
    )
    metrics = {
        "physical_damage": physical_damage,
        "magic_damage": magic_damage,
        "durability": scores["durability"],
        "crowd_control": crowd_control,
        "mobility": scores["mobility"],
        "engage": engage,
        "protection": scores["protection"],
        "split_push": scores["split_push"],
        # There is no direct wave-clear rating in the official-text engine.
        "wave_clear": None,
        "objective_control": scores["objective_control"],
    }
    known = tuple(key for key, value in metrics.items() if value is not None)
    return EngineProfile(
        metrics=metrics,
        rating_scores=scores,
        confidence=float(rating.confidence or 0),
        source="official_skill_rating",
        damage_type=damage_type,
        method_version=rating.method_version,
        known_metrics=known,
        evidence=rating.evidence or {},
    )


def profile_for(hero) -> EngineProfile:
    """Return an attached official profile or a safe legacy fallback."""
    attached = getattr(hero, "_engine_profile", None)
    return attached if isinstance(attached, EngineProfile) else _legacy_profile(hero)


def load_engine_profiles(
    db: Session,
    heroes: Iterable,
    analyses_by_hero: Mapping[int, HeroAnalysis] | None = None,
) -> dict[int, EngineProfile]:
    """Load and attach ratings/analysis in two bounded queries.

    ``HeroRating`` is versioned. Rows are ordered newest first and only the
    newest row for each hero is used. The method avoids per-hero queries in list,
    draft and team endpoints.
    """
    unique = {hero.id: hero for hero in heroes}
    if not unique:
        return {}
    hero_ids = tuple(unique)
    analyses = dict(analyses_by_hero or {})
    if analyses_by_hero is None:
        analyses = {
            row.hero_id: row
            for row in db.scalars(
                select(HeroAnalysis).where(HeroAnalysis.hero_id.in_(hero_ids))
            )
        }
    ratings: dict[int, HeroRating] = {}
    for row in db.scalars(
        select(HeroRating)
        .where(HeroRating.hero_id.in_(hero_ids))
        .order_by(HeroRating.created_at.desc(), HeroRating.id.desc())
    ):
        ratings.setdefault(row.hero_id, row)

    profiles: dict[int, EngineProfile] = {}
    for hero_id, hero in unique.items():
        legacy = _legacy_profile(hero)
        rating = ratings.get(hero_id)
        if rating is None:
            profile = legacy
        else:
            official = _rating_profile(hero, rating, analyses.get(hero_id))
            # Official values are preferred once they meet the minimum needed
            # by composition engines. The 15 curated records remain a complete
            # fallback when keyword-derived evidence is sparse.
            official_ready = official.readiness(
                bool(getattr(hero, "roles", [])), bool(getattr(hero, "positions", []))
            )["composition"]
            profile = official if official_ready or legacy.source == "insufficient" else legacy
            if profile is legacy and rating is not None:
                # Preserve the official counter evidence even when composition
                # needs the richer curated fallback.
                profile = EngineProfile(
                    metrics=legacy.metrics,
                    rating_scores=official.rating_scores,
                    confidence=max(legacy.confidence, official.confidence),
                    source=legacy.source,
                    damage_type=legacy.damage_type,
                    method_version=f"{legacy.method_version}+{official.method_version}",
                    known_metrics=legacy.known_metrics,
                    evidence=official.evidence,
                )
        setattr(hero, "_engine_profile", profile)
        profiles[hero_id] = profile
    return profiles


def readiness_payload(hero, profile: EngineProfile | None = None) -> dict:
    profile = profile or profile_for(hero)
    modules = profile.readiness(
        bool(getattr(hero, "roles", [])), bool(getattr(hero, "positions", []))
    )
    return {
        "engine_ready": any(modules.values()),
        "modules": modules,
        "source": profile.source,
        "confidence": round(profile.confidence, 2),
        "known_metrics": list(profile.known_metrics),
        "missing_metrics": [key for key in TACTICAL_METRICS if key not in profile.known_metrics],
        "method_version": profile.method_version,
    }
