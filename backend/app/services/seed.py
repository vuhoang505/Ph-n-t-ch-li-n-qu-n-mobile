import json
from pathlib import Path

from datetime import datetime

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models import DataSource, GamePatch, Hero, HeroAttribute, HeroRole, Item


DATA_FILE = Path(__file__).resolve().parents[3] / "data" / "imports" / "starter_data.json"
ROSTER_FILE = Path(__file__).resolve().parents[3] / "data" / "imports" / "official_roster.json"


ZERO_ATTRIBUTES = {
    "physical_damage": 0, "magic_damage": 0, "durability": 0, "crowd_control": 0,
    "mobility": 0, "engage": 0, "protection": 0, "split_push": 0,
    "wave_clear": 0, "objective_control": 0,
}


def seed_database(db: Session) -> None:
    payload = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    source = db.scalar(select(DataSource).where(DataSource.name == payload["source"]["name"]))
    if not source:
        source = DataSource(**payload["source"])
        db.add(source)
        db.flush()
    patch = db.scalar(select(GamePatch).where(GamePatch.version == payload["patch"]["version"]))
    if not patch:
        db.add(GamePatch(**payload["patch"]))
    for source_row in payload["heroes"]:
        row = dict(source_row)
        attrs = row.pop("attributes")
        roles = row.pop("roles")
        hero = db.scalar(select(Hero).where(Hero.slug == row["slug"]))
        if not hero:
            hero = Hero(**row, source_id=source.id)
            hero.roles = [HeroRole(role=role) for role in roles]
            hero.attributes = HeroAttribute(**attrs)
            db.add(hero)
    for row in payload["items"]:
        # Official catalog updates can rename a slug while preserving the item
        # name. Seed data is only a fallback, so either identity means the row
        # already exists and must not be duplicated.
        if not db.scalar(select(Item).where(or_(Item.slug == row["slug"], Item.name == row["name"]))):
            db.add(Item(**row))
    db.flush()

    if ROSTER_FILE.exists():
        roster_payload = json.loads(ROSTER_FILE.read_text(encoding="utf-8"))
        source_data = dict(roster_payload["source"])
        retrieved = source_data.pop("retrieved_at", None)
        official_source = db.scalar(select(DataSource).where(DataSource.name == source_data["name"]))
        if not official_source:
            official_source = DataSource(
                **source_data,
                retrieved_at=datetime.fromisoformat(retrieved) if retrieved else None,
            )
            db.add(official_source)
            db.flush()
        for row in roster_payload["heroes"]:
            hero = db.scalar(select(Hero).where(Hero.slug == row["slug"]))
            if hero:
                hero.image_url = row["image_url"]
                continue
            hero = Hero(
                slug=row["slug"], name=row["name"], image_url=row["image_url"],
                damage_type="unknown", positions=row["positions_inferred_from_roles"],
                power_phase="unknown", difficulty=0, strengths=[], weaknesses=[],
                patch_version="official-roster-2026.10", source_id=official_source.id,
            )
            hero.roles = [HeroRole(role=role) for role in row["roles"]]
            hero.attributes = HeroAttribute(**ZERO_ATTRIBUTES)
            db.add(hero)
    db.commit()

