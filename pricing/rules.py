"""
pricing/rules.py
Alert rule evaluation engine per Section 4.8 specification.
"""

from __future__ import annotations

from decimal import Decimal

from pricing.models import DealVerdict, DropMetrics, HistoricalMetrics, PriceObservation


def evaluate_alert_rules(
    current_obs: PriceObservation,
    previous_obs: PriceObservation | None,
    history: HistoricalMetrics,
    drop_metrics: DropMetrics,
    verdict: DealVerdict,
    target_price: Decimal | None = None,
    user_drop_threshold_pct: float = 5.0,
) -> list[str]:
    """
    Evaluate which alert rules fire for the given observation.
    Low-confidence observations suppress aggressive alerts (STRONG_DEAL).
    """
    fired_rules: list[str] = []

    # 1. Target Price Hit
    if target_price is not None and current_obs.price <= target_price:
        fired_rules.append("TARGET_HIT")

    # 2. All-Time Low Price
    if (
        history.lowest_all_time > Decimal("0.00")
        and current_obs.price <= history.lowest_all_time
        and history.observation_count >= 2
    ):
        fired_rules.append("ALL_TIME_LOW")

    # 3. Big Deal Drop (15%+ off)
    if drop_metrics.absolute_drop_pct >= 15.0:
        fired_rules.append("BIG_DEAL")
    # 4. Standard Price Drop (User Threshold)
    elif drop_metrics.absolute_drop_pct >= user_drop_threshold_pct:
        fired_rules.append("PRICE_DROP")

    # 5. Strong Deal (High confidence required)
    if verdict.deal_score >= 80.0 and history.confidence == "high":
        if "STRONG_DEAL" not in fired_rules:
            fired_rules.append("STRONG_DEAL")

    # 6. Coupon newly available
    prev_coupon = previous_obs.coupon if previous_obs else None
    if current_obs.coupon and current_obs.coupon > Decimal("0.00"):
        if prev_coupon is None or current_obs.coupon > prev_coupon:
            fired_rules.append("COUPON_ALERT")

    return fired_rules
