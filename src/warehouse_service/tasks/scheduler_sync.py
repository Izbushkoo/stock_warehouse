"""Helpers to bootstrap the SQLAlchemy-backed Celery beat schedule."""

from __future__ import annotations

import logging

from celery.app.base import Celery
from sqlalchemy_celery_beat.schedulers import DatabaseScheduler

from warehouse_service.tasks.celery_app import BEAT_SCHEMA, celery

logger = logging.getLogger(__name__)


def sync_schedule(app: Celery | None = None) -> None:
    """Ensure configured periodic tasks are persisted in the scheduler backend."""

    app = app or celery

    logger.info(
        "Syncing Celery beat schedule to SQLAlchemy backend",
        extra={"scheduler_schema": BEAT_SCHEMA},
    )

    scheduler = DatabaseScheduler(app=app, lazy=True)
    try:
        scheduler.setup_schedule()
        scheduler.sync()
    finally:
        scheduler.close()

    logger.info("Celery beat schedule successfully synchronised")


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint used by container helpers and operational scripts."""

    logging.basicConfig(level=logging.INFO)
    sync_schedule()
    return 0


if __name__ == "__main__":  # pragma: no cover - module CLI guard
    raise SystemExit(main())
