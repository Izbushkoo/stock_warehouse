"""Application configuration loading helpers."""

from __future__ import annotations

from functools import lru_cache
from typing import Any, Literal

from pydantic import BaseModel, Field, PrivateAttr
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseModel):
    url: str
    async_url: str | None = None
    pool_size: int = 10
    echo: bool = False


class RedisSettings(BaseModel):
    url: str
    broker_url: str
    result_backend: str
    scheduler_url: str


class TelegramSettings(BaseModel):
    bot_token: str
    critical_chat_id: int
    health_chat_id: int


class SecuritySettings(BaseModel):
    superadmin_email: str
    superadmin_password: str
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    jwt_expire_hours: int = 24


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", ".env.local"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = Field(default="Unified Warehouse", alias="APP_NAME")
    environment: Literal["development", "staging", "production"] = Field(
        default="development", alias="ENVIRONMENT"
    )
    api_host: str = Field(default="0.0.0.0", alias="API_HOST")
    api_port: int = Field(default=8000, alias="API_PORT")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    timezone: str = Field(default="Europe/Minsk", alias="TZ")
    sentry_dsn: str | None = Field(default=None, alias="SENTRY_DSN")

    database_url: str = Field(alias="DATABASE_URL")
    async_database_url: str | None = Field(default=None, alias="ASYNC_DATABASE_URL")
    database_pool_size: int = Field(default=10, alias="DATABASE_POOL_SIZE")
    database_echo: bool = Field(default=False, alias="DATABASE_ECHO")

    redis_url: str = Field(alias="REDIS_URL")
    celery_broker_url: str = Field(alias="CELERY_BROKER_URL")
    celery_result_backend: str = Field(alias="CELERY_RESULT_BACKEND")
    celery_db_scheduler_url: str = Field(alias="CELERY_DB_SCHEDULER_URL")

    telegram_bot_token: str = Field(alias="TELEGRAM_BOT_TOKEN")
    telegram_critical_chat_id: int = Field(alias="TELEGRAM_CRITICAL_CHAT_ID")
    telegram_health_chat_id: int = Field(alias="TELEGRAM_HEALTH_CHAT_ID")

    superadmin_email: str = Field(alias="SUPERADMIN_EMAIL")
    superadmin_password: str = Field(alias="SUPERADMIN_PASSWORD")
    jwt_secret: str = Field(default="dev-secret", alias="JWT_SECRET")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    jwt_expire_hours: int = Field(default=24, alias="JWT_EXPIRE_HOURS")

    _database: DatabaseSettings = PrivateAttr()
    _redis: RedisSettings = PrivateAttr()
    _telegram: TelegramSettings = PrivateAttr()
    _security: SecuritySettings = PrivateAttr()

    def model_post_init(self, __context: Any) -> None:  # pragma: no cover - simple data wiring
        object.__setattr__(
            self,
            "_database",
            DatabaseSettings(
                url=self.database_url,
                async_url=self.async_database_url,
                pool_size=self.database_pool_size,
                echo=self.database_echo,
            ),
        )
        object.__setattr__(
            self,
            "_redis",
            RedisSettings(
                url=self.redis_url,
                broker_url=self.celery_broker_url,
                result_backend=self.celery_result_backend,
                scheduler_url=self.celery_db_scheduler_url,
            ),
        )
        object.__setattr__(
            self,
            "_telegram",
            TelegramSettings(
                bot_token=self.telegram_bot_token,
                critical_chat_id=self.telegram_critical_chat_id,
                health_chat_id=self.telegram_health_chat_id,
            ),
        )
        object.__setattr__(
            self,
            "_security",
            SecuritySettings(
                superadmin_email=self.superadmin_email,
                superadmin_password=self.superadmin_password,
                jwt_secret=self.jwt_secret,
                jwt_algorithm=self.jwt_algorithm,
                jwt_expire_hours=self.jwt_expire_hours,
            ),
        )

    @property
    def database(self) -> DatabaseSettings:
        return self._database

    @property
    def redis(self) -> RedisSettings:
        return self._redis

    @property
    def telegram(self) -> TelegramSettings:
        return self._telegram

    @property
    def security(self) -> SecuritySettings:
        return self._security


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]


__all__ = ["Settings", "get_settings", "DatabaseSettings", "RedisSettings", "TelegramSettings", "SecuritySettings"]
