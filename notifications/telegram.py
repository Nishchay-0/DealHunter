"""
notifications/telegram.py
Telegram notification adapter for delivering deal alerts to users.
"""

from __future__ import annotations

import logging
import os
import httpx

from database.models import User
from notifications.base import Notifier
from notifications.models import AlertPayload

logger = logging.getLogger(__name__)


class TelegramNotifier(Notifier):
    """Delivers deal alerts via the Telegram Bot API."""

    channel_name: str = "telegram"

    def __init__(self, token: str | None = None) -> None:
        self.token = token or os.getenv("TELEGRAM_BOT_TOKEN")

    async def send_alert(
        self,
        user: User,
        payload: AlertPayload,
        message_text: str,
    ) -> bool:
        """Send pre-rendered alert to user's Telegram chat."""
        if not user.telegram_id:
            logger.debug("User %s has no telegram_id; skipping telegram notification", user.id)
            return False

        if not self.token:
            logger.warning("TELEGRAM_BOT_TOKEN not configured; cannot deliver alert")
            return False

        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        post_data = {
            "chat_id": user.telegram_id,
            "text": message_text,
            "parse_mode": "Markdown",
            "disable_web_page_preview": False,
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(url, json=post_data)
                data = resp.json()
                if resp.status_code == 200 and data.get("ok"):
                    logger.info("Delivered Telegram alert to user %s (chat %s)", user.id, user.telegram_id)
                    return True
                logger.error("Telegram API failed for user %s: %s", user.id, data.get("description"))
                return False
        except Exception as exc:
            logger.error("Telegram delivery exception for user %s: %s", user.id, exc)
            return False
