"""
notifications/dispatcher.py
NotificationDispatcher coordinates deal alert delivery while strictly enforcing:
1. Deduplication (current_price == previous_price)
2. Per-product cooldowns (default 6h)
3. Quiet hours by user timezone
4. Digest mode filtering
5. Daily message rate caps per user
6. Recording into alerts_sent table
"""

from __future__ import annotations

import logging
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import AlertSent, User
from notifications.base import Notifier
from notifications.models import AlertPayload
from notifications.renderer import MessageRenderer
from notifications.telegram import TelegramNotifier
from notifications.whatsapp import WhatsAppNotifier

logger = logging.getLogger(__name__)


class NotificationDispatcher:
    """Manages guardrails, message rendering, and delivery across channels."""

    def __init__(
        self,
        notifiers: list[Notifier] | None = None,
        default_cooldown_hours: int = 6,
    ) -> None:
        self.notifiers: list[Notifier] = notifiers or [
            TelegramNotifier(),
            WhatsAppNotifier(),
        ]
        self.cooldown_hours = default_cooldown_hours

    def is_in_quiet_hours(self, user: User, now_utc: datetime | None = None) -> bool:
        """Check if current time in user's timezone falls within quiet hours."""
        if not user.quiet_hours_start or not user.quiet_hours_end:
            return False

        now_utc = now_utc or datetime.now(timezone.utc)
        try:
            user_tz = ZoneInfo(user.timezone or "Asia/Kolkata")
            local_time = now_utc.astimezone(user_tz).time()
        except Exception:
            local_time = now_utc.time()

        start = user.quiet_hours_start
        end = user.quiet_hours_end

        if start <= end:
            return start <= local_time <= end
        # Overnight quiet hours (e.g. 23:00 to 07:00)
        return local_time >= start or local_time <= end

    async def can_send_alert(
        self,
        user: User,
        payload: AlertPayload,
        session: AsyncSession,
        now_utc: datetime | None = None,
    ) -> tuple[bool, str]:
        """
        Evaluate mandatory guardrails before sending an alert.
        Returns (can_send: bool, reason: str).
        """
        now = now_utc or datetime.now(timezone.utc)

        # 1. Deduplication guardrail
        if payload.current_price == payload.previous_price:
            return False, "Price unchanged from previous observation (deduplicated)"

        # 2. Digest mode guardrail
        if user.digest_mode:
            return False, "User has enabled digest mode; skipping instant alert"

        # 3. Quiet hours guardrail
        if self.is_in_quiet_hours(user, now):
            return False, "Currently within user's quiet hours"

        # 4. Daily alert cap guardrail
        day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        count_stmt = select(func.count(AlertSent.id)).where(
            AlertSent.user_id == user.id,
            AlertSent.sent_at >= day_start,
        )
        count_res = await session.execute(count_stmt)
        alerts_today = count_res.scalar() or 0
        if alerts_today >= (user.daily_alert_cap or 20):
            return False, f"User exceeded daily alert cap ({alerts_today}/{user.daily_alert_cap})"

        # 5. Cooldown guardrail (per product, per user)
        cooldown_cutoff = now - timedelta(hours=self.cooldown_hours)
        cooldown_stmt = select(AlertSent).where(
            AlertSent.user_id == user.id,
            AlertSent.product_id == payload.product_id,
            AlertSent.sent_at >= cooldown_cutoff,
        )
        cooldown_res = await session.execute(cooldown_stmt)
        recent_alert = cooldown_res.scalars().first()
        if recent_alert:
            return False, f"Product alert in cooldown period (last sent at {recent_alert.sent_at})"

        return True, "All guardrails passed"

    async def dispatch_alert(
        self,
        user: User,
        payload: AlertPayload,
        session: AsyncSession,
    ) -> bool:
        """
        Check guardrails, render message once, deliver via active adapters,
        and record to alerts_sent.
        """
        can_send, reason = await self.can_send_alert(user, payload, session)
        if not can_send:
            logger.info("Alert suppressed for user %s on product %s: %s", user.id, payload.product_id, reason)
            return False

        message_text = MessageRenderer.render(payload)
        any_success = False

        for notifier in self.notifiers:
            # Only attempt if user has the relevant channel ID
            if notifier.channel_name == "telegram" and not user.telegram_id:
                continue
            if notifier.channel_name == "whatsapp" and not user.whatsapp_id:
                continue

            delivered = await notifier.send_alert(user, payload, message_text)
            if delivered:
                any_success = True
                # Record to alerts_sent
                record = AlertSent(
                    user_id=user.id,
                    product_id=payload.product_id,
                    rule=payload.rule,
                    deal_score=payload.deal_score,
                    channel=notifier.channel_name,
                    payload_json={
                        "rule": payload.rule,
                        "current_price": float(payload.current_price),
                        "previous_price": float(payload.previous_price),
                        "effective_price": float(payload.effective_price),
                    },
                )
                session.add(record)

        if any_success:
            await session.commit()

        return any_success
