"""Celery tasks package."""

from __future__ import annotations

from warehouse_service.tasks.celery_app import celery

__all__ = ["celery"]
