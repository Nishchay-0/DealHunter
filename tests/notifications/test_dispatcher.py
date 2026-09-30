"""
tests/notifications/test_dispatcher.py
Unit tests for notification guardrails (dedup, cooldown, quiet hours, rate cap).
"""

from datetime import datetime, time, timezone
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import AlertSent, User
from notifications.base import Notifier
from notifications.dispatcher import NotificationDispatcher
from notifications.models import AlertPayload


class DummyNotifier(Notifier):
    channel_name = "telegram"

    def __init__(self, should_succeed: bool = True):
        self.should_succeed = should_succeed
        self.sent_messages: list[str] = []

    async def send_alert(self, user: User, payload: AlertPayload, message_text: str) -> bool:
        if self.should_succeed:
            self.sent_messages.append(message_text)
            return True
        return False


@pytest.mark.asyncio
async def test_deduplication_guardrail(test_session: AsyncSession):
    """Never send an alert if price is unchanged from previous."""
    dispatcher = NotificationDispatcher(notifiers=[DummyNotifier()])
    user = User(telegram_id=123)

    payload = AlertPayload(
        product_id=1,
        product_name="Product",
        platform="amazon",
        canonical_url="https://amazon.in/dp/B001",
        rule="PRICE_DROP",
        previous_price=Decimal("1000.00"),
        current_price=Decimal("1000.00"),  # Unchanged
        effective_price=Decimal("1000.00"),
    )

    can_send, reason = await dispatcher.can_send_alert(user, payload, test_session)
    assert can_send is False
    assert "deduplicated" in reason.lower()


@pytest.mark.asyncio
async def test_quiet_hours_guardrail(test_session: AsyncSession):
    """Suppress alerts during user-configured quiet hours."""
    dispatcher = NotificationDispatcher(notifiers=[DummyNotifier()])
    user = User(
        telegram_id=123,
        timezone="UTC",
        quiet_hours_start=time(22, 0),
        quiet_hours_end=time(7, 0),
    )

    payload = AlertPayload(
        product_id=1,
        product_name="Product",
        platform="amazon",
        canonical_url="https://amazon.in/dp/B001",
        rule="PRICE_DROP",
        previous_price=Decimal("1000.00"),
        current_price=Decimal("900.00"),
        effective_price=Decimal("900.00"),
    )

    # 23:30 UTC is inside 22:00 - 07:00 quiet hours
    inside_quiet = datetime(2026, 9, 30, 23, 30, tzinfo=timezone.utc)
    can_send, reason = await dispatcher.can_send_alert(user, payload, test_session, now_utc=inside_quiet)
    assert can_send is False
    assert "quiet hours" in reason.lower()

    # 14:00 UTC is outside quiet hours
    outside_quiet = datetime(2026, 9, 30, 14, 0, tzinfo=timezone.utc)
    can_send_day, _ = await dispatcher.can_send_alert(user, payload, test_session, now_utc=outside_quiet)
    assert can_send_day is True


@pytest.mark.asyncio
async def test_cooldown_and_recording(test_session: AsyncSession):
    """Verify cooldown stops rapid-fire alerts and successful alert records in DB."""
    notifier = DummyNotifier()
    dispatcher = NotificationDispatcher(notifiers=[notifier], default_cooldown_hours=6)

    user = User(telegram_id=456)
    test_session.add(user)
    await test_session.commit()

    payload = AlertPayload(
        product_id=99,
        product_name="Gadget",
        platform="flipkart",
        canonical_url="https://flipkart.com/p/item",
        rule="PRICE_DROP",
        previous_price=Decimal("2000.00"),
        current_price=Decimal("1800.00"),
        effective_price=Decimal("1800.00"),
    )

    # 1. First dispatch succeeds and records in DB
    sent = await dispatcher.dispatch_alert(user, payload, test_session)
    assert sent is True
    assert len(notifier.sent_messages) == 1

    # Verify AlertSent record created
    res = await test_session.execute(select(AlertSent).where(AlertSent.user_id == user.id))
    alerts = res.scalars().all()
    assert len(alerts) == 1
    assert alerts[0].product_id == 99

    # 2. Immediate second dispatch is blocked by cooldown
    can_send, reason = await dispatcher.can_send_alert(user, payload, test_session)
    assert can_send is False
    assert "cooldown" in reason.lower()
