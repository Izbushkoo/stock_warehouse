"""Telegram notification helpers."""

from __future__ import annotations

import httpx

from warehouse_service.config import get_settings
from warehouse_service.logging import logger


class TelegramNotifier:
    """Send operational notifications to Telegram chats."""

    def __init__(self, bot_token: str | None = None) -> None:
        settings = get_settings()
        self.bot_token = bot_token or settings.telegram.bot_token
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"
        self._client = httpx.AsyncClient(base_url=self.base_url, timeout=10)
        self.critical_chat_id = settings.telegram.critical_chat_id
        self.health_chat_id = settings.telegram.health_chat_id

    async def send_message(self, chat_id: int, text: str, *, parse_mode: str | None = "MarkdownV2") -> None:
        payload = {"chat_id": chat_id, "text": text, "parse_mode": parse_mode}
        response = await self._client.post("/sendMessage", json=payload)
        if response.is_error:
            logger.error("Failed to send Telegram message", status_code=response.status_code, body=response.text)
            response.raise_for_status()

    async def notify_startup(self, ok: bool, details: str) -> None:
        chat_id = self.critical_chat_id
        status = "✅" if ok else "❌"
        await self.send_message(chat_id, f"{status} *Warehouse service startup check*\n{details}")

    async def notify_health(self, ok: bool, details: str) -> None:
        chat_id = self.health_chat_id or self.critical_chat_id
        status = "✅" if ok else "❌"
        await self.send_message(chat_id, f"{status} *Warehouse daily health report*\n{details}")

    async def aclose(self) -> None:
        await self._client.aclose()


__all__ = ["TelegramNotifier"]
