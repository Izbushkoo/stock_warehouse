from __future__ import annotations

from warehouse_service.config import Settings


def test_settings_load_from_env(monkeypatch):
    monkeypatch.setenv("APP_NAME", "Test App")
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://user:pass@localhost:5432/db")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("CELERY_BROKER_URL", "redis://localhost:6379/1")
    monkeypatch.setenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/2")
    monkeypatch.setenv("CELERY_DB_SCHEDULER_URL", "postgresql+psycopg://user:pass@localhost:5432/db")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "token")
    monkeypatch.setenv("TELEGRAM_CRITICAL_CHAT_ID", "123")
    monkeypatch.setenv("TELEGRAM_HEALTH_CHAT_ID", "456")
    monkeypatch.setenv("SUPERADMIN_EMAIL", "admin@example.com")
    monkeypatch.setenv("SUPERADMIN_PASSWORD", "secret")

    settings = Settings()
    assert settings.app_name == "Test App"
    assert settings.database.url.startswith("postgresql+")
    assert settings.redis.url.startswith("redis://")
    assert settings.telegram.critical_chat_id == 123
    assert settings.security.superadmin_email == "admin@example.com"
