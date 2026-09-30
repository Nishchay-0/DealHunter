"""
notifications/whatsapp.py
Official WhatsApp Business Cloud API notification adapter.

Compliance: Uses the Meta WhatsApp Business Cloud API.
Never automates personal accounts.
"""

from __future__ import annotations

import logging
import os
import httpx

from database.models import User
from notifications.base import Notifier
from notifications.models import AlertPayload

logger = logging.getLogger(__name__)


class WhatsAppNotifier(Notifier):
    """Delivers alerts via official Meta WhatsApp Business Cloud API."""

    channel_name: str = "whatsapp"

    def __init__(
        self,
        token: str | None = None,
        phone_number_id: str | None = None,
    ) -> None:
        self.token = token or os.getenv("WHATSAPP_API_TOKEN")
        self.phone_number_id = phone_number_id or os.getenv("WHATSAPP_PHONE_NUMBER_ID")

    async def send_alert(
        self,
        user: User,
        payload: AlertPayload,
        message_text: str,
    ) -> bool:
        """Send message via official WhatsApp Cloud API."""
        if not user.whatsapp_id:
            logger.debug("User %s has no whatsapp_id; skipping whatsapp channel", user.id)
            return False

        if not self.token or not self.phone_number_id:
            logger.info("WhatsApp Cloud API credentials not configured; alert skipped for user %s", user.id)
            return False

        url = f"https://graph.facebook.com/v19.0/{self.phone_number_id}/messages"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }
        body = {
            "messaging_product": "whatsapp",
            "to": user.whatsapp_id,
            "type": "text",
            "text": {"preview_url": True, "body": message_text},
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(url, headers=headers, json=body)
                if resp.status_code in (200, 201):
                    logger.info("Delivered WhatsApp alert to user %s (%s)", user.id, user.whatsapp_id)
                    return True
                logger.error("WhatsApp Cloud API error (%s): %s", resp.status_code, resp.text)
                return False
        except Exception as exc:
            logger.error("WhatsApp delivery failed for user %s: %s", user.id, exc)
            return False
