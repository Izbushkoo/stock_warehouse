"""Health check runner."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Iterable, Protocol

from redis import Redis
from sqlalchemy import create_engine, text

from warehouse_service.config import get_settings
from warehouse_service.logging import logger


class Check(Protocol):
    name: str

    async def run(self) -> "CheckResult":
        ...


@dataclass(slots=True)
class CheckResult:
    name: str
    ok: bool
    details: str


class DatabaseCheck:
    name = "database"

    async def run(self) -> CheckResult:
        settings = get_settings()
        try:
            engine = create_engine(settings.database.url)
            with engine.connect() as connection:
                result = connection.execute(text("SELECT 1"))
                result.fetchone()
        except Exception as exc:  # pragma: no cover - real connection required
            return CheckResult(name=self.name, ok=False, details=str(exc))
        return CheckResult(name=self.name, ok=True, details="PostgreSQL reachable")


class RedisCheck:
    name = "redis"

    async def run(self) -> CheckResult:
        settings = get_settings()
        try:
            client = Redis.from_url(settings.redis.url)
            pong = client.ping()
            ok = bool(pong)
        except Exception as exc:  # pragma: no cover - requires redis
            return CheckResult(name=self.name, ok=False, details=str(exc))
        return CheckResult(name=self.name, ok=True, details="Redis reachable" if ok else "Unexpected response")


async def run_checks(checks: Iterable[Check] | None = None) -> list[CheckResult]:
    checks = list(checks or [DatabaseCheck(), RedisCheck()])
    results = await asyncio.gather(*(check.run() for check in checks))
    status = all(result.ok for result in results)
    for result in results:
        if result.ok:
            logger.info("Health check passed", check=result.name, details=result.details)
        else:
            logger.error("Health check failed", check=result.name, details=result.details)
    logger.info("Overall health", ok=status)
    return results
