"""
pricing/history.py
Historical context and drop metrics computation algorithms per Sections 4.3 & 4.4.
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from statistics import mean, median, stdev

from pricing.config import MIN_CONFIDENCE_OBSERVATIONS
from pricing.models import DropMetrics, HistoricalMetrics, PriceObservation


def compute_historical_metrics(
    observations: list[PriceObservation],
    now: datetime | None = None,
) -> HistoricalMetrics:
    """
    Compute historical statistics (lows, medians, mean, volatility, confidence)
    from a list of PriceObservation records sorted by observed_at descending.
    """
    now = now or datetime.now(timezone.utc)
    if not observations:
        return HistoricalMetrics(
            current_price=Decimal("0.00"),
            previous_price=None,
            lowest_30d=Decimal("0.00"),
            lowest_90d=Decimal("0.00"),
            lowest_all_time=Decimal("0.00"),
            median_30d=Decimal("0.00"),
            median_90d=Decimal("0.00"),
            mean_30d=Decimal("0.00"),
            price_volatility_30d=0.0,
            observation_count=0,
            days_since_lowest=0,
            confidence="low",
        )

    # Ensure sorted by observed_at DESC (most recent first)
    sorted_obs = sorted(observations, key=lambda x: x.observed_at, reverse=True)
    current_obs = sorted_obs[0]
    current_price = current_obs.price
    previous_price = sorted_obs[1].price if len(sorted_obs) > 1 else None

    cutoff_30d = now - timedelta(days=30)
    cutoff_90d = now - timedelta(days=90)

    prices_all = [float(o.price) for o in sorted_obs]
    prices_30d = [float(o.price) for o in sorted_obs if o.observed_at >= cutoff_30d] or prices_all
    prices_90d = [float(o.price) for o in sorted_obs if o.observed_at >= cutoff_90d] or prices_all

    lowest_all_time = Decimal(str(min(prices_all)))
    lowest_30d = Decimal(str(min(prices_30d)))
    lowest_90d = Decimal(str(min(prices_90d)))

    median_30d = Decimal(str(round(median(prices_30d), 2)))
    median_90d = Decimal(str(round(median(prices_90d), 2)))
    mean_30d = Decimal(str(round(mean(prices_30d), 2)))

    # Calculate price volatility (std deviation of % changes)
    pct_changes: list[float] = []
    for i in range(len(prices_30d) - 1):
        p_curr = prices_30d[i]
        p_prev = prices_30d[i + 1]
        if p_prev > 0:
            pct_changes.append(((p_curr - p_prev) / p_prev) * 100.0)

    volatility = stdev(pct_changes) if len(pct_changes) >= 2 else 0.0

    # Days since all-time lowest observation
    lowest_obs = min(sorted_obs, key=lambda x: x.price)
    days_since_lowest = max(0, (now - lowest_obs.observed_at).days)

    obs_count = len(sorted_obs)
    confidence = "high" if obs_count >= MIN_CONFIDENCE_OBSERVATIONS else "low"

    return HistoricalMetrics(
        current_price=current_price,
        previous_price=previous_price,
        lowest_30d=lowest_30d,
        lowest_90d=lowest_90d,
        lowest_all_time=lowest_all_time,
        median_30d=median_30d,
        median_90d=median_90d,
        mean_30d=mean_30d,
        price_volatility_30d=round(volatility, 2),
        observation_count=obs_count,
        days_since_lowest=days_since_lowest,
        confidence=confidence,
    )


def compute_drop_metrics(
    current_obs: PriceObservation,
    previous_obs: PriceObservation | None,
    history: HistoricalMetrics,
) -> DropMetrics:
    """Compute drop magnitude and velocity metrics (Section 4.4)."""
    prev_price = previous_obs.price if previous_obs else history.previous_price or current_obs.price
    curr_price = current_obs.price

    absolute_drop = max(Decimal("0.00"), prev_price - curr_price)
    if prev_price > Decimal("0.00"):
        drop_pct = float((absolute_drop / prev_price) * Decimal("100"))
    else:
        drop_pct = 0.0

    drop_vs_30d = curr_price - history.lowest_30d
    drop_vs_alltime = curr_price - history.lowest_all_time

    # Velocity: % drop per hour since previous observation
    velocity = 0.0
    if previous_obs and drop_pct > 0:
        hours_diff = (current_obs.observed_at - previous_obs.observed_at).total_seconds() / 3600.0
        if hours_diff > 0:
            velocity = drop_pct / hours_diff

    return DropMetrics(
        absolute_drop=absolute_drop,
        absolute_drop_pct=round(drop_pct, 2),
        drop_vs_30d_low=drop_vs_30d,
        drop_vs_alltime_low=drop_vs_alltime,
        drop_velocity=round(velocity, 2),
    )
