"""Bổ sung cấu trúc phân tích tướng, không thay đổi bảng heroes.

Revision ID: 0002_hero_analysis
Revises: 0001_initial
"""
from alembic import op

from app.core.database import Base
from app.models import *  # noqa: F401,F403

revision = "0002_hero_analysis"
down_revision = "0001_initial"
branch_labels = None
depends_on = None

TABLES = [
    "hero_analysis", "hero_ratings", "hero_strengths", "hero_weaknesses",
    "hero_matchups", "hero_power_spikes", "hero_recommended_builds",
    "hero_data_sources", "hero_analysis_versions",
]


def upgrade():
    bind = op.get_bind()
    for name in TABLES:
        Base.metadata.tables[name].create(bind=bind, checkfirst=True)


def downgrade():
    bind = op.get_bind()
    for name in reversed(TABLES):
        Base.metadata.tables[name].drop(bind=bind, checkfirst=True)
