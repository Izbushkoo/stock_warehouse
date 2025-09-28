"""Celery tasks related to health monitoring."""

from __future__ import annotations

import asyncio

from warehouse_service.notifications import TelegramNotifier
from warehouse_service.system_checks import run_checks
from warehouse_service.tasks.celery_app import celery


@celery.task(name="warehouse_service.tasks.health.daily_health_check", bind=True)
def daily_health_check(self):
    """Run daily health check and notify the monitoring channel."""

    async def _run() -> None:
        results = await run_checks()
        ok = all(result.ok for result in results)
        details = "\n".join(
            f"{result.name}: {'OK' if result.ok else 'FAILED'} — {result.details}" for result in results
        )
        notifier = TelegramNotifier()
        try:
            await notifier.notify_health(ok, details)
        finally:
            await notifier.aclose()

    return asyncio.run(_run())
