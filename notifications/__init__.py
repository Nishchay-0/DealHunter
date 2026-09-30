"""
notifications package for DealHunter.
Exports models, dispatcher, renderer, and channel adapters.
"""

from notifications.base import Notifier
from notifications.dispatcher import NotificationDispatcher
from notifications.models import AlertPayload
from notifications.renderer import MessageRenderer
from notifications.telegram import TelegramNotifier
from notifications.whatsapp import WhatsAppNotifier

__all__ = [
    "AlertPayload",
    "Notifier",
    "MessageRenderer",
    "TelegramNotifier",
    "WhatsAppNotifier",
    "NotificationDispatcher",
]
