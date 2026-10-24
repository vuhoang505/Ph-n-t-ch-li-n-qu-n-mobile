"""Audit hero-data coverage without mutating the database.

Run from the repository root. The command exits non-zero only for integrity
failures (missing/duplicate heroes, IDs, official profiles or skills). Analysis
coverage is reported separately because nullable, evidence-based fields are
valid and must not be silently filled.
"""
from __future__ import annotations

import json
import os
import sys
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
os.chdir(ROOT / "backend")

from sqlalchemy import func, select  # noqa: E402

from app.core.database import SessionLocal  # noqa: E402
from app.models import (  # noqa: E402
    Hero,
    HeroAnalysis,
    HeroDataSource,
    HeroMatchup,
    HeroPowerSpike,
    HeroRating,
    HeroRecommendedBuild,
    HeroSkill,
    HeroStrength,
    HeroSynergy,
    HeroWeakness,
    Item,
)
from app.engines.hero_rating import METHOD_VERSION  # noqa: E402
from app.services.hero_analysis import PATCH_VERSION  # noqa: E402


RATING_FIELDS = (
    "damage", "durability", "mobility", "crowd_control", "sustain", "burst",
    "teamfight", "split_push", "pickoff", "protection", "objective_control",
    "early_game", "mid_game", "late_game", "difficulty",
)


def audit() -> tuple[dict, list[str]]:
    with SessionLocal() as db:
        heroes = list(db.scalars(select(Hero).order_by(Hero.id)))
        analyses = list(db.scalars(select(HeroAnalysis)))
        ratings = list(db.scalars(select(HeroRating).where(
            HeroRating.method_version == METHOD_VERSION,
            HeroRating.patch_version == PATCH_VERSION,
        )))
        skill_counts = Counter(db.scalars(select(HeroSkill.hero_id)))
        source_hero_ids = set(db.scalars(select(HeroDataSource.hero_id).where(HeroDataSource.verified.is_(True))))
        weakness_hero_ids = set(db.scalars(select(HeroWeakness.hero_id)))
        build_hero_ids = set(db.scalars(select(HeroRecommendedBuild.hero_id)))
        spike_counts = Counter(db.scalars(select(HeroPowerSpike.hero_id)))
        synergy_hero_ids = set(db.scalars(select(HeroSynergy.hero_a_id))) | set(db.scalars(select(HeroSynergy.hero_b_id)))
        matchup_hero_ids = set(db.scalars(select(HeroMatchup.hero_id)))

        report = {
            "integrity": {
                "heroes": len(heroes),
                "unique_ids": len({hero.id for hero in heroes}),
                "unique_names": len({hero.name.casefold() for hero in heroes}),
                "unique_slugs": len({hero.slug for hero in heroes}),
                "id_range": [min((hero.id for hero in heroes), default=None), max((hero.id for hero in heroes), default=None)],
            },
            "official_data": {
                "verified_source_heroes": len(source_hero_ids),
                "heroes_with_four_or_more_skills": sum(skill_counts[hero.id] >= 4 for hero in heroes),
                "skills": sum(skill_counts.values()),
                "items": db.scalar(select(func.count()).select_from(Item)) or 0,
            },
            "analysis": {
                "analysis_rows": len(analyses),
                "rating_rows": len(ratings),
                "strength_rows": db.scalar(select(func.count()).select_from(HeroStrength)) or 0,
                "heroes_with_weaknesses": len(weakness_hero_ids),
                "heroes_with_three_phase_rows": sum(spike_counts[hero.id] >= 3 for hero in heroes),
                "heroes_with_builds": len(build_hero_ids),
                "heroes_with_synergies": len(synergy_hero_ids),
                "heroes_with_persisted_matchups": len(matchup_hero_ids),
                "known_ratings": {field: sum(getattr(row, field) is not None for row in ratings) for field in RATING_FIELDS},
                "statuses": dict(Counter(row.data_status for row in analyses)),
                "heroes_with_core_profile": sum(
                    bool(hero.positions and hero.roles and hero.damage_type and hero.power_phase != "unknown" and hero.difficulty > 0 and hero.strengths and hero.weaknesses)
                    for hero in heroes
                ),
            },
        }

    failures = []
    if report["integrity"]["heroes"] != 129:
        failures.append("database must contain exactly 129 heroes")
    for field in ("unique_ids", "unique_names", "unique_slugs"):
        if report["integrity"][field] != 129:
            failures.append(f"{field} must equal 129")
    if report["official_data"]["verified_source_heroes"] != 129:
        failures.append("every hero must have a verified official profile source")
    if report["official_data"]["heroes_with_four_or_more_skills"] != 129:
        failures.append("every hero must have at least four parsed official skills")
    if report["analysis"]["rating_rows"] != 129:
        failures.append("current rating version must contain exactly one row for every hero")
    if report["analysis"]["heroes_with_core_profile"] != 129:
        failures.append("every hero must have a complete core profile")
    if any(count != 129 for count in report["analysis"]["known_ratings"].values()):
        failures.append("every current tactical rating dimension must cover all 129 heroes")
    if report["analysis"]["statuses"] != {"complete": 129}:
        failures.append("all 129 hero analyses must have complete status")
    return report, failures


def main() -> None:
    report, failures = audit()
    print(json.dumps({"report": report, "integrity_failures": failures}, ensure_ascii=False, indent=2))
    raise SystemExit(1 if failures else 0)


if __name__ == "__main__":
    main()
