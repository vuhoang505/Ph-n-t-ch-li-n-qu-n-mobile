"""Add auditable gameplay catalog and derived-build metadata.

Revision ID: 0003_gameplay_catalog
Revises: 0002_hero_analysis
"""
from alembic import op
import sqlalchemy as sa

from app.core.database import Base
from app.models import *  # noqa: F401,F403


revision = "0003_gameplay_catalog"
down_revision = "0002_hero_analysis"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    Base.metadata.tables["gameplay_catalog_entries"].create(bind=bind, checkfirst=True)
    inspector = sa.inspect(bind)
    build_columns = {column["name"] for column in inspector.get_columns("hero_recommended_builds")}
    synergy_columns = {column["name"] for column in inspector.get_columns("hero_synergies")}
    additions = {
        "hero_recommended_builds": [
            sa.Column("evidence", sa.JSON(), nullable=False, server_default="[]"),
            sa.Column("confidence", sa.Float(), nullable=False, server_default="0"),
            sa.Column("provenance", sa.String(60), nullable=False, server_default="derived"),
            sa.Column("method_version", sa.String(40), nullable=False, server_default="hero-build-v1"),
        ],
        "hero_synergies": [
            sa.Column("evidence", sa.JSON(), nullable=False, server_default="[]"),
            sa.Column("conditions", sa.JSON(), nullable=False, server_default="[]"),
            sa.Column("data_status", sa.String(40), nullable=False, server_default="derived_partial"),
            sa.Column("provenance", sa.String(60), nullable=False, server_default="derived"),
            sa.Column("method_version", sa.String(40), nullable=False, server_default="hero-synergy-v1"),
        ],
    }
    known = {"hero_recommended_builds": build_columns, "hero_synergies": synergy_columns}
    for table, columns in additions.items():
        for column in columns:
            if column.name not in known[table]:
                op.add_column(table, column)


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    for table, names in {
        "hero_synergies": ["method_version", "provenance", "data_status", "conditions", "evidence"],
        "hero_recommended_builds": ["method_version", "provenance", "confidence", "evidence"],
    }.items():
        existing = {column["name"] for column in inspector.get_columns(table)}
        for name in names:
            if name in existing:
                op.drop_column(table, name)
    Base.metadata.tables["gameplay_catalog_entries"].drop(bind=bind, checkfirst=True)
