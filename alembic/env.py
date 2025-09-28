from __future__ import annotations

import os
from logging.config import fileConfig

from alembic import context
from sqlmodel import SQLModel

from warehouse_service.db.engine import get_engine
from warehouse_service.models import metadata  # noqa: F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

section = config.config_ini_section
if section is not None:
    url = os.getenv("DATABASE_URL")
    if url:
        config.set_section_option(section, "sqlalchemy.url", url)

def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=SQLModel.metadata, literal_binds=True, dialect_opts={"paramstyle": "named"})

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = get_engine()

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=SQLModel.metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
