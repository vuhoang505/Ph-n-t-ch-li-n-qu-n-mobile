from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def utcnow_naive() -> datetime:
    """UTC timestamp compatible with MySQL/SQLite naive DATETIME columns."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow_naive)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow_naive, onupdate=utcnow_naive)


class GamePatch(Base, TimestampMixin):
    __tablename__ = "game_patches"
    id: Mapped[int] = mapped_column(primary_key=True)
    version: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(160))
    released_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    is_current: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    source_url: Mapped[str | None] = mapped_column(String(500), nullable=True)


class DataSource(Base, TimestampMixin):
    __tablename__ = "data_sources"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    source_type: Mapped[str] = mapped_column(String(40), default="manual_verified")
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    retrieved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class Hero(Base, TimestampMixin):
    __tablename__ = "heroes"
    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    damage_type: Mapped[str] = mapped_column(String(24), default="mixed")
    positions: Mapped[list] = mapped_column(JSON, default=list)
    power_phase: Mapped[str] = mapped_column(String(24), default="mid")
    difficulty: Mapped[int] = mapped_column(Integer, default=5)
    strengths: Mapped[list] = mapped_column(JSON, default=list)
    weaknesses: Mapped[list] = mapped_column(JSON, default=list)
    patch_version: Mapped[str] = mapped_column(String(40), index=True)
    source_id: Mapped[int | None] = mapped_column(ForeignKey("data_sources.id"), nullable=True)
    roles: Mapped[list["HeroRole"]] = relationship(cascade="all, delete-orphan", lazy="selectin")
    attributes: Mapped["HeroAttribute"] = relationship(cascade="all, delete-orphan", uselist=False, lazy="selectin")
    skills: Mapped[list["HeroSkill"]] = relationship(cascade="all, delete-orphan", lazy="selectin")


class HeroRole(Base):
    __tablename__ = "hero_roles"
    id: Mapped[int] = mapped_column(primary_key=True)
    hero_id: Mapped[int] = mapped_column(ForeignKey("heroes.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(40), index=True)
    __table_args__ = (UniqueConstraint("hero_id", "role"),)


class HeroAttribute(Base):
    __tablename__ = "hero_attributes"
    hero_id: Mapped[int] = mapped_column(ForeignKey("heroes.id", ondelete="CASCADE"), primary_key=True)
    physical_damage: Mapped[float] = mapped_column(Float, default=0)
    magic_damage: Mapped[float] = mapped_column(Float, default=0)
    durability: Mapped[float] = mapped_column(Float, default=0)
    crowd_control: Mapped[float] = mapped_column(Float, default=0)
    mobility: Mapped[float] = mapped_column(Float, default=0)
    engage: Mapped[float] = mapped_column(Float, default=0)
    protection: Mapped[float] = mapped_column(Float, default=0)
    split_push: Mapped[float] = mapped_column(Float, default=0)
    wave_clear: Mapped[float] = mapped_column(Float, default=0)
    objective_control: Mapped[float] = mapped_column(Float, default=0)


class HeroSkill(Base):
    __tablename__ = "hero_skills"
    id: Mapped[int] = mapped_column(primary_key=True)
    hero_id: Mapped[int] = mapped_column(ForeignKey("heroes.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    skill_type: Mapped[str] = mapped_column(String(20))
    description: Mapped[str] = mapped_column(Text)
    order_index: Mapped[int] = mapped_column(Integer, default=0)


class HeroAnalysis(Base, TimestampMixin):
    __tablename__ = "hero_analysis"
    id: Mapped[int] = mapped_column(primary_key=True)
    hero_id: Mapped[int] = mapped_column(ForeignKey("heroes.id", ondelete="CASCADE"), unique=True, index=True)
    aliases: Mapped[list] = mapped_column(JSON, default=list)
    primary_role: Mapped[str | None] = mapped_column(String(40), nullable=True)
    secondary_role: Mapped[str | None] = mapped_column(String(40), nullable=True)
    damage_type: Mapped[str | None] = mapped_column(String(24), nullable=True)
    range_type: Mapped[str | None] = mapped_column(String(24), nullable=True)
    special_mechanics: Mapped[list] = mapped_column(JSON, default=list)
    data_status: Mapped[str] = mapped_column(String(40), default="insufficient", index=True)
    confidence: Mapped[float] = mapped_column(Float, default=0)
    method_version: Mapped[str] = mapped_column(String(40), default="hero-rating-v1")
    patch_version: Mapped[str] = mapped_column(String(40), index=True)


class HeroRating(Base, TimestampMixin):
    __tablename__ = "hero_ratings"
    id: Mapped[int] = mapped_column(primary_key=True)
    hero_id: Mapped[int] = mapped_column(ForeignKey("heroes.id", ondelete="CASCADE"), index=True)
    damage: Mapped[float | None] = mapped_column(Float, nullable=True)
    durability: Mapped[float | None] = mapped_column(Float, nullable=True)
    mobility: Mapped[float | None] = mapped_column(Float, nullable=True)
    crowd_control: Mapped[float | None] = mapped_column(Float, nullable=True)
    sustain: Mapped[float | None] = mapped_column(Float, nullable=True)
    burst: Mapped[float | None] = mapped_column(Float, nullable=True)
    teamfight: Mapped[float | None] = mapped_column(Float, nullable=True)
    split_push: Mapped[float | None] = mapped_column(Float, nullable=True)
    pickoff: Mapped[float | None] = mapped_column(Float, nullable=True)
    protection: Mapped[float | None] = mapped_column(Float, nullable=True)
    objective_control: Mapped[float | None] = mapped_column(Float, nullable=True)
    early_game: Mapped[float | None] = mapped_column(Float, nullable=True)
    mid_game: Mapped[float | None] = mapped_column(Float, nullable=True)
    late_game: Mapped[float | None] = mapped_column(Float, nullable=True)
    difficulty: Mapped[float | None] = mapped_column(Float, nullable=True)
    explanations: Mapped[dict] = mapped_column(JSON, default=dict)
    evidence: Mapped[dict] = mapped_column(JSON, default=dict)
    confidence: Mapped[float] = mapped_column(Float, default=0)
    provenance: Mapped[str] = mapped_column(String(40), default="derived")
    method_version: Mapped[str] = mapped_column(String(40), default="hero-rating-v1")
    patch_version: Mapped[str] = mapped_column(String(40), index=True)
    __table_args__ = (UniqueConstraint("hero_id", "method_version", "patch_version"),)


class HeroStrength(Base, TimestampMixin):
    __tablename__ = "hero_strengths"
    id: Mapped[int] = mapped_column(primary_key=True)
    hero_id: Mapped[int] = mapped_column(ForeignKey("heroes.id", ondelete="CASCADE"), index=True)
    attribute_key: Mapped[str] = mapped_column(String(50))
    title: Mapped[str] = mapped_column(String(160))
    explanation: Mapped[str] = mapped_column(Text)
    evidence: Mapped[list] = mapped_column(JSON, default=list)
    confidence: Mapped[float] = mapped_column(Float, default=0)
    provenance: Mapped[str] = mapped_column(String(40), default="derived")
    patch_version: Mapped[str] = mapped_column(String(40), index=True)
    __table_args__ = (UniqueConstraint("hero_id", "attribute_key", "patch_version"),)


class HeroWeakness(Base, TimestampMixin):
    __tablename__ = "hero_weaknesses"
    id: Mapped[int] = mapped_column(primary_key=True)
    hero_id: Mapped[int] = mapped_column(ForeignKey("heroes.id", ondelete="CASCADE"), index=True)
    weakness_key: Mapped[str] = mapped_column(String(50))
    title: Mapped[str] = mapped_column(String(160))
    explanation: Mapped[str] = mapped_column(Text)
    evidence: Mapped[list] = mapped_column(JSON, default=list)
    confidence: Mapped[float] = mapped_column(Float, default=0)
    provenance: Mapped[str] = mapped_column(String(40), default="expert")
    patch_version: Mapped[str] = mapped_column(String(40), index=True)
    __table_args__ = (UniqueConstraint("hero_id", "weakness_key", "patch_version"),)


class HeroMatchup(Base, TimestampMixin):
    __tablename__ = "hero_matchups"
    id: Mapped[int] = mapped_column(primary_key=True)
    hero_id: Mapped[int] = mapped_column(ForeignKey("heroes.id", ondelete="CASCADE"), index=True)
    opponent_id: Mapped[int] = mapped_column(ForeignKey("heroes.id", ondelete="CASCADE"), index=True)
    advantage_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    reasons: Mapped[list] = mapped_column(JSON, default=list)
    conditions: Mapped[list] = mapped_column(JSON, default=list)
    data_status: Mapped[str] = mapped_column(String(40), default="insufficient")
    confidence: Mapped[float] = mapped_column(Float, default=0)
    method_version: Mapped[str] = mapped_column(String(40), default="matchup-v1")
    patch_version: Mapped[str] = mapped_column(String(40), index=True)
    __table_args__ = (UniqueConstraint("hero_id", "opponent_id", "method_version", "patch_version"),)


class HeroPowerSpike(Base, TimestampMixin):
    __tablename__ = "hero_power_spikes"
    id: Mapped[int] = mapped_column(primary_key=True)
    hero_id: Mapped[int] = mapped_column(ForeignKey("heroes.id", ondelete="CASCADE"), index=True)
    phase: Mapped[str] = mapped_column(String(20))
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    analysis: Mapped[dict] = mapped_column(JSON, default=dict)
    confidence: Mapped[float] = mapped_column(Float, default=0)
    provenance: Mapped[str] = mapped_column(String(40), default="derived")
    patch_version: Mapped[str] = mapped_column(String(40), index=True)
    __table_args__ = (UniqueConstraint("hero_id", "phase", "patch_version"),)


class HeroRecommendedBuild(Base, TimestampMixin):
    __tablename__ = "hero_recommended_builds"
    id: Mapped[int] = mapped_column(primary_key=True)
    hero_id: Mapped[int] = mapped_column(ForeignKey("heroes.id", ondelete="CASCADE"), index=True)
    position: Mapped[str] = mapped_column(String(40))
    situation: Mapped[str] = mapped_column(String(60), default="default")
    item_ids: Mapped[list] = mapped_column(JSON, default=list)
    arcana: Mapped[dict] = mapped_column(JSON, default=dict)
    enchantments: Mapped[dict] = mapped_column(JSON, default=dict)
    talent: Mapped[str | None] = mapped_column(String(80), nullable=True)
    explanation: Mapped[str] = mapped_column(Text)
    data_status: Mapped[str] = mapped_column(String(40), default="pending_review")
    evidence: Mapped[list] = mapped_column(JSON, default=list)
    confidence: Mapped[float] = mapped_column(Float, default=0)
    provenance: Mapped[str] = mapped_column(String(60), default="derived")
    method_version: Mapped[str] = mapped_column(String(40), default="hero-build-v1")
    source_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    patch_version: Mapped[str] = mapped_column(String(40), index=True)


class HeroDataSource(Base, TimestampMixin):
    __tablename__ = "hero_data_sources"
    id: Mapped[int] = mapped_column(primary_key=True)
    hero_id: Mapped[int] = mapped_column(ForeignKey("heroes.id", ondelete="CASCADE"), index=True)
    source_url: Mapped[str] = mapped_column(String(500))
    source_kind: Mapped[str] = mapped_column(String(40))
    fetched_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    fields: Mapped[list] = mapped_column(JSON, default=list)
    __table_args__ = (UniqueConstraint("hero_id", "source_url", "content_hash"),)


class HeroAnalysisVersion(Base, TimestampMixin):
    __tablename__ = "hero_analysis_versions"
    id: Mapped[int] = mapped_column(primary_key=True)
    hero_id: Mapped[int] = mapped_column(ForeignKey("heroes.id", ondelete="CASCADE"), index=True)
    version: Mapped[str] = mapped_column(String(60))
    status: Mapped[str] = mapped_column(String(40), index=True)
    summary: Mapped[dict] = mapped_column(JSON, default=dict)
    reviewed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    __table_args__ = (UniqueConstraint("hero_id", "version"),)


class HeroCounter(Base, TimestampMixin):
    __tablename__ = "hero_counters"
    id: Mapped[int] = mapped_column(primary_key=True)
    hero_id: Mapped[int] = mapped_column(ForeignKey("heroes.id", ondelete="CASCADE"), index=True)
    target_hero_id: Mapped[int] = mapped_column(ForeignKey("heroes.id", ondelete="CASCADE"), index=True)
    advantage_score: Mapped[float] = mapped_column(Float)
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    reason: Mapped[str] = mapped_column(Text)
    conditions: Mapped[dict] = mapped_column(JSON, default=dict)
    patch_version: Mapped[str] = mapped_column(String(40), index=True)
    __table_args__ = (UniqueConstraint("hero_id", "target_hero_id", "patch_version"),)


class HeroSynergy(Base, TimestampMixin):
    __tablename__ = "hero_synergies"
    id: Mapped[int] = mapped_column(primary_key=True)
    hero_a_id: Mapped[int] = mapped_column(ForeignKey("heroes.id", ondelete="CASCADE"), index=True)
    hero_b_id: Mapped[int] = mapped_column(ForeignKey("heroes.id", ondelete="CASCADE"), index=True)
    score: Mapped[float] = mapped_column(Float)
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    reason: Mapped[str] = mapped_column(Text)
    evidence: Mapped[list] = mapped_column(JSON, default=list)
    conditions: Mapped[list] = mapped_column(JSON, default=list)
    data_status: Mapped[str] = mapped_column(String(40), default="derived_partial")
    provenance: Mapped[str] = mapped_column(String(60), default="derived")
    method_version: Mapped[str] = mapped_column(String(40), default="hero-synergy-v1")
    patch_version: Mapped[str] = mapped_column(String(40), index=True)
    __table_args__ = (UniqueConstraint("hero_a_id", "hero_b_id", "patch_version"),)


class GameplayCatalogEntry(Base, TimestampMixin):
    """Verified public entries from Garena's gameplay catalog pages.

    Hero loadouts reference these records by ``external_key`` inside their JSON
    fields.  Keeping the source text intact makes derived recommendations
    auditable without claiming that Garena recommends a particular loadout.
    """

    __tablename__ = "gameplay_catalog_entries"
    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String(32), index=True)
    external_key: Mapped[str] = mapped_column(String(140))
    slug: Mapped[str] = mapped_column(String(140), index=True)
    name: Mapped[str] = mapped_column(String(160), index=True)
    category: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    level: Mapped[str | None] = mapped_column(String(40), nullable=True)
    image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    description: Mapped[str] = mapped_column(Text)
    attributes: Mapped[dict] = mapped_column(JSON, default=dict)
    source_url: Mapped[str] = mapped_column(String(500))
    content_hash: Mapped[str] = mapped_column(String(64))
    fetched_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    verified: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    __table_args__ = (UniqueConstraint("kind", "external_key"),)


class Item(Base, TimestampMixin):
    __tablename__ = "items"
    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(100), unique=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    category: Mapped[str] = mapped_column(String(40), index=True)
    cost: Mapped[int] = mapped_column(Integer)
    attributes: Mapped[dict] = mapped_column(JSON, default=dict)
    passive: Mapped[str | None] = mapped_column(Text, nullable=True)
    roles: Mapped[list] = mapped_column(JSON, default=list)
    counters: Mapped[list] = mapped_column(JSON, default=list)
    patch_version: Mapped[str] = mapped_column(String(40), index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class MetaStatistic(Base, TimestampMixin):
    __tablename__ = "meta_statistics"
    id: Mapped[int] = mapped_column(primary_key=True)
    hero_id: Mapped[int] = mapped_column(ForeignKey("heroes.id"), index=True)
    patch_version: Mapped[str] = mapped_column(String(40), index=True)
    rank_tier: Mapped[str | None] = mapped_column(String(40), nullable=True)
    sample_size: Mapped[int] = mapped_column(Integer)
    win_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    pick_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    ban_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("data_sources.id"))
    verified: Mapped[bool] = mapped_column(Boolean, default=False, index=True)


class User(Base, TimestampMixin):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(80))
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), default="user", index=True)
    favorite_hero_ids: Mapped[list] = mapped_column(JSON, default=list)
    mastered_hero_ids: Mapped[list] = mapped_column(JSON, default=list)


class AnalysisHistory(Base, TimestampMixin):
    __tablename__ = "analysis_history"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    session_key: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    analysis_type: Mapped[str] = mapped_column(String(40), index=True)
    input_payload: Mapped[dict] = mapped_column(JSON)
    output_payload: Mapped[dict] = mapped_column(JSON)
    patch_version: Mapped[str] = mapped_column(String(40), index=True)


Index("ix_hero_role_lookup", HeroRole.role, HeroRole.hero_id)

