"""Celery application configuration."""

from __future__ import annotations

import os

from celery import Celery
from celery.schedules import crontab

from warehouse_service.config import get_settings

settings = get_settings()

celery = Celery(
    "warehouse_service",
    broker=settings.redis.broker_url,
    backend=settings.redis.result_backend,
)

celery.conf.update(
    timezone=settings.timezone,
    enable_utc=False,
    beat_scheduler="celery_sqlalchemy_scheduler.schedulers:DatabaseScheduler",
    beat_dburi=settings.redis.scheduler_url,
    beat_schedule={
        "daily-health-check": {
            "task": "warehouse_service.tasks.health.daily_health_check",
            "schedule": crontab(hour=9, minute=0),
            "options": {"queue": "monitoring"},
        }
    },
    worker_hijack_root_logger=False,
)

celery.conf.beat_schedule_filename = os.getenv("CELERY_BEAT_SCHEDULE", "celerybeat-schedule")
celery.conf.result_expires = 3600
celery.autodiscover_tasks(["warehouse_service.tasks"])
