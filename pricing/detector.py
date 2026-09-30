"""
pricing/detector.py
Drop detection algorithms, deduplication checks, and cooldown evaluation per Section 4.8.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from pricing.models import PriceObservation


def is_duplicate_observation(
    obs1: PriceObservation,
    obs2: PriceObservation | None,
) -> bool:
    """Return True if obs1 is identical in price and offers to obs2."""
    if obs2 is None:
        return False
    return (
        obs1.price == obs2.price
        and obs1.effective_price == obs2.effective_price
        and obs1.in_stock == obs2.in_stock
        and obs1.coupon == obs2.coupon
        and obs1.bank_offer == obs2.bank_offer
    )


def is_in_cooldown(
    last_alert_at: datetime | None,
    cooldown_hours: int = 6,
    now: datetime | None = None,
) -> bool:
    """Return True if an alert was sent within the cooldown window."""
    if last_alert_at is None:
        return False
    now = now or datetime.now(timezone.utc)
    return (now - last_alert_at) < timedelta(hours=cooldown_hours)


def detect_price_drop(
    current_obs: PriceObservation,
    previous_obs: PriceObservation | None,
) -> tuple[bool, Decimal, float]:
    """
    Evaluate if price dropped compared to previous observation.
    Returns (has_dropped: bool, drop_amount: Decimal, drop_pct: float).
    """
    if previous_obs is None or previous_obs.price <= Decimal("0.00"):
        return False, Decimal("0.00"), 0.0

    if current_obs.price < previous_obs.price:
        drop_amount = previous_obs.price - current_obs.price
        drop_pct = float((drop_amount / previous_obs.price) * Decimal("100"))
        return True, drop_amount, round(drop_pct, 2)

    return False, Decimal("0.00"), 0.0
