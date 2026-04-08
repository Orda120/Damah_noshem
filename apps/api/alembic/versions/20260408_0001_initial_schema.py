"""Initial schema for Damah_noshem MVP."""

from __future__ import annotations

from alembic import op
from sqlalchemy import text

from app.db.base import Base
from app.db import models  # noqa: F401

# revision identifiers, used by Alembic.
revision = "20260408_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    archive_schema = bind.engine.url.query.get("archive_schema") or "archive_catalog"
    if bind.dialect.name == "postgresql" and archive_schema:
        bind.execute(text(f"CREATE SCHEMA IF NOT EXISTS {archive_schema}"))
    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)
    archive_schema = bind.engine.url.query.get("archive_schema") or "archive_catalog"
    if bind.dialect.name == "postgresql" and archive_schema:
        bind.execute(text(f"DROP SCHEMA IF EXISTS {archive_schema} CASCADE"))
