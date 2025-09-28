from __future__ import annotations

import pytest

from warehouse_service.config import get_settings
from warehouse_service.notifications.telegram import TelegramNotifier


@pytest.fixture(autouse=True)
def clear_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def anyio_backend():
    return "asyncio"


def configure_base_env(monkeypatch, *, token: str, critical_id: str, health_id: str) -> None:
    monkeypatch.setenv("APP_NAME", "Test App")
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://user:pass@localhost:5432/db")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("CELERY_BROKER_URL", "redis://localhost:6379/1")
    monkeypatch.setenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/2")
    monkeypatch.setenv("CELERY_DB_SCHEDULER_URL", "postgresql+psycopg://user:pass@localhost:5432/db")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", token)
    monkeypatch.setenv("TELEGRAM_CRITICAL_CHAT_ID", critical_id)
    monkeypatch.setenv("TELEGRAM_HEALTH_CHAT_ID", health_id)
    monkeypatch.setenv("SUPERADMIN_EMAIL", "admin@example.com")
    monkeypatch.setenv("SUPERADMIN_PASSWORD", "secret")


@pytest.mark.anyio(backend="asyncio")
async def test_notifier_disabled_when_token_missing(monkeypatch):
    configure_base_env(monkeypatch, token="replace-me", critical_id="0", health_id="0")

    notifier = TelegramNotifier()

    assert notifier._enabled is False  # type: ignore[attr-defined]

    await notifier.notify_startup(ok=True, details="All good")
    await notifier.aclose()


@pytest.mark.anyio(backend="asyncio")
async def test_notifier_skips_when_chat_not_configured(monkeypatch):
    configure_base_env(monkeypatch, token="valid-token", critical_id="0", health_id="0")

    notifier = TelegramNotifier()

    calls: list[None] = []

    async def fail_post(*args, **kwargs):  # pragma: no cover - guarded by chat id check
        calls.append(None)
        raise AssertionError("HTTP client should not be called when chat id is missing")

    if notifier._client is not None:
        notifier._client.post = fail_post  # type: ignore[assignment]

    await notifier.notify_startup(ok=False, details="Failed checks")
    await notifier.aclose()

    assert not calls
