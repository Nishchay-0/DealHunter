"""
notifications/base.py
Abstract Base Class for notification delivery channels (Telegram, WhatsApp, etc.).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from database.models import User
    from notifications.models import AlertPayload


class Notifier(ABC):
    """Channel adapter interface for dispatching notifications."""

    channel_name: str  # "telegram", "whatsapp", etc.

    @abstractmethod
    async def send_alert(
        self,
        user: User,
        payload: AlertPayload,
        message_text: str,
    ) -> bool:
        """
        Deliver pre-rendered alert message to user on this channel.
        Returns True if delivered successfully, False otherwise.
        """
        raise NotImplementedError
