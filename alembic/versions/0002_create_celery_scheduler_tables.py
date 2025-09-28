"""Create tables for SQLAlchemy-backed Celery beat scheduler."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy_celery_beat import models

revision = "0002_create_celery_scheduler_tables"
down_revision = "0001_create_core_tables"
branch_labels = None
depends_on = None

CELERY_SCHEMA = "celery_schema"


def upgrade() -> None:
    connection = op.get_bind()
    connection.execute(sa.text(f"CREATE SCHEMA IF NOT EXISTS {CELERY_SCHEMA}"))

    schema_connection = connection.execution_options(
        schema_translate_map={"celery_schema": CELERY_SCHEMA}
    )
    models.ModelBase.metadata.create_all(schema_connection, checkfirst=True)


def downgrade() -> None:
    connection = op.get_bind()
    schema_connection = connection.execution_options(
        schema_translate_map={"celery_schema": CELERY_SCHEMA}
    )
    models.ModelBase.metadata.drop_all(schema_connection, checkfirst=True)

    connection.execute(sa.text(f"DROP SCHEMA IF EXISTS {CELERY_SCHEMA} CASCADE"))
