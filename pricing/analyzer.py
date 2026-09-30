"""
pricing/analyzer.py
Fake-discount detection and price manipulation analyzer per Section 4.5.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from pricing.models import HistoricalMetrics, PriceObservation


def detect_fake_discount(
    current_obs: PriceObservation,
    history_obs: list[PriceObservation],
    metrics: HistoricalMetrics,
    now: datetime | None = None,
) -> tuple[bool, str | None]:
    """
    Detect fake/artificial discounts per Section 4.5 rules:
    - MRP/list_price appears inflated (> 25% above 30d median)
    - Price was raised in the last 14 days and then dropped back to prior baseline
    """
    now = now or datetime.now(timezone.utc)
    curr_price = current_obs.price

    # 1. Check for inflated list price compared to 30d median
    if metrics.median_30d > Decimal("0.00"):
        ratio = (curr_price - metrics.median_30d) / metrics.median_30d
        if ratio > Decimal("0.25"):
            return True, f"Listed price is {float(ratio * 100):.0f}% above the 30-day median"

    # 2. Check for recent price spike in last 14 days followed by drop back to prior level
    cutoff_14d = now - timedelta(days=14)
    recent_obs = [o for o in history_obs if o.observed_at >= cutoff_14d]

    if len(recent_obs) >= 3:
        # Sort chronologically (oldest to newest)
        sorted_recent = sorted(recent_obs, key=lambda x: x.observed_at)
        p_initial = sorted_recent[0].price
        prices = [o.price for o in sorted_recent]
        max_price = max(prices)

        # If price spiked by >= 15% and then fell back to within 3% of initial
        if max_price > p_initial * Decimal("1.15"):
            if abs(curr_price - p_initial) / p_initial <= Decimal("0.03"):
                return (
                    True,
                    f"Price was artificially raised to ₹{max_price:,.2f} in the last 14 days and dropped back",
                )

    return False, None
