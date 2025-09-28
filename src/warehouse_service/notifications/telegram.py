"""Telegram notification helpers."""

from __future__ import annotations

import re
import httpx
from pydantic import ValidationError

from warehouse_service.config import get_settings
from warehouse_service.logging import logger


def escape_html(text: str) -> str:
    """Escape special characters for Telegram HTML."""
    # Characters that need to be escaped in HTML
    text = text.replace("&", "&amp;")
    text = text.replace("<", "&lt;")
    text = text.replace(">", "&gt;")
    return text


class TelegramNotifier:
    """Send operational notifications to Telegram chats."""

    def __init__(self, bot_token: str | None = None) -> None:
        try:
            settings = get_settings()
        except ValidationError:
            logger.info(
                "Telegram notifications disabled: configuration is incomplete"
            )
            self.bot_token = ""
            self.critical_chat_id = 0
            self.health_chat_id = 0
            self._client = None
            self._enabled = False
            return
        configured_token = bot_token or settings.telegram.bot_token
        self.bot_token = configured_token
        self.critical_chat_id = settings.telegram.critical_chat_id
        self.health_chat_id = settings.telegram.health_chat_id

        token_missing = not configured_token or configured_token == "replace-me"
        if token_missing:
            self._client: httpx.AsyncClient | None = None
            self._enabled = False
            logger.info("Telegram notifications disabled: bot token is not configured")
        else:
            base_url = f"https://api.telegram.org/bot{configured_token}"
            self._client = httpx.AsyncClient(base_url=base_url, timeout=10)
            self._enabled = True

    async def send_message(self, chat_id: int, text: str, *, parse_mode: str | None = "HTML") -> None:
        if not self._enabled:
            logger.debug("Skipping Telegram notification because notifier is disabled")
            return
        if not chat_id:
            logger.warning("Skipping Telegram notification because chat id is not configured")
            return
        if self._client is None:  # Safety net for type checkers
            logger.debug("Telegram HTTP client is not available, skipping notification")
            return

        payload = {"chat_id": chat_id, "text": text}
        if parse_mode:
            payload["parse_mode"] = parse_mode
            
        logger.info(f"Sending Telegram message to chat {chat_id}: {text[:100]}...")
        response = await self._client.post("/sendMessage", json=payload)
        if response.is_error:
            logger.error(
                "Failed to send Telegram message",
                status_code=response.status_code,
                body=response.text,
                payload=payload,
            )
            response.raise_for_status()

    async def notify_startup(self, ok: bool, details: str) -> None:
        chat_id = self.critical_chat_id
        status = "✅" if ok else "❌"
        escaped_details = escape_html(details)
        text = f"{status} <b>Warehouse service startup check</b>\n{escaped_details}"
        await self.send_message(chat_id, text)

    async def notify_health(self, ok: bool, details: str) -> None:
        chat_id = self.health_chat_id or self.critical_chat_id
        status = "✅" if ok else "❌"
        escaped_details = escape_html(details)
        text = f"{status} <b>Warehouse daily health report</b>\n{escaped_details}"
        await self.send_message(chat_id, text)

    async def aclose(self) -> None:
        if self._client is not None:
            await self._client.aclose()


__all__ = ["TelegramNotifier"]
