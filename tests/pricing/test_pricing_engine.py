"""
tests/pricing/test_pricing_engine.py
Comprehensive unit tests for the Deal Analysis Engine (pricing/ module).
Verifies effective price, historical metrics, fake-discount detection, deal scoring, rules, and cooldowns.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from pricing.analyzer import detect_fake_discount
from pricing.config import get_deal_label
from pricing.detector import detect_price_drop, is_duplicate_observation, is_in_cooldown
from pricing.effective_price import calculate_effective_price
from pricing.history import compute_drop_metrics, compute_historical_metrics
from pricing.models import PriceObservation
from pricing.rules import evaluate_alert_rules
from pricing.scorer import DealScorer


def test_effective_price_calculation():
    """Test offer stacking (coupon + bank offer + cashback)."""
    obs = PriceObservation(
        product_id=101,
        price=Decimal("50000.00"),
        currency="INR",
        source="amazon",
        in_stock=True,
        coupon=Decimal("2000.00"),
        bank_offer=Decimal("3000.00"),
        cashback=Decimal("1000.00"),
    )

    listed, effective, notes = calculate_effective_price(obs)

    assert listed == Decimal("50000.00")
    assert effective == Decimal("44000.00")
    assert len(notes) == 3
    assert "Coupon applied" in notes[0]


def test_historical_metrics_computation():
    """Test computation of lows, medians, volatility, and confidence."""
    now = datetime(2026, 9, 30, 12, 0, tzinfo=timezone.utc)
    obs_list = [
        PriceObservation(1, Decimal("10000.00"), "INR", "amazon", observed_at=now - timedelta(days=1)),
        PriceObservation(1, Decimal("12000.00"), "INR", "amazon", observed_at=now - timedelta(days=5)),
        PriceObservation(1, Decimal("15000.00"), "INR", "amazon", observed_at=now - timedelta(days=10)),
        PriceObservation(1, Decimal("9000.00"), "INR", "amazon", observed_at=now - timedelta(days=20)),
    ]

    metrics = compute_historical_metrics(obs_list, now=now)

    assert metrics.current_price == Decimal("10000.00")
    assert metrics.previous_price == Decimal("12000.00")
    assert metrics.lowest_all_time == Decimal("9000.00")
    assert metrics.lowest_30d == Decimal("9000.00")
    assert metrics.observation_count == 4
    assert metrics.confidence == "low"  # < 20 observations


def test_drop_metrics_and_velocity():
    """Test drop magnitude and velocity (% per hour)."""
    t1 = datetime(2026, 9, 30, 10, 0, tzinfo=timezone.utc)
    t2 = datetime(2026, 9, 30, 14, 0, tzinfo=timezone.utc)  # 4 hours later

    prev_obs = PriceObservation(1, Decimal("10000.00"), "INR", "amazon", observed_at=t1)
    curr_obs = PriceObservation(1, Decimal("8000.00"), "INR", "amazon", observed_at=t2)  # 20% drop in 4h

    hist = compute_historical_metrics([curr_obs, prev_obs], now=t2)
    drop_m = compute_drop_metrics(curr_obs, prev_obs, hist)

    assert drop_m.absolute_drop == Decimal("2000.00")
    assert drop_m.absolute_drop_pct == 20.0
    assert drop_m.drop_velocity == 5.0  # 20% / 4 hours = 5%/hr


def test_fake_discount_detection_inflated_mrp():
    """Detect artificially inflated list price compared to 30d median."""
    now = datetime(2026, 9, 30, 12, 0, tzinfo=timezone.utc)
    # Median is around 10,000
    obs_list = [PriceObservation(1, Decimal("10000.00"), "INR", "amazon", observed_at=now - timedelta(days=i)) for i in range(5)]

    metrics = compute_historical_metrics(obs_list, now=now)
    # Current list price is 15,000 (50% above 10,000 median)
    inflated_obs = PriceObservation(1, Decimal("15000.00"), "INR", "amazon", observed_at=now)

    is_fake, reason = detect_fake_discount(inflated_obs, obs_list, metrics, now=now)
    assert is_fake is True
    assert "30-day median" in (reason or "")


def test_deal_scorer_and_verdict():
    """Verify weighted score calculation and factor breakdown."""
    now = datetime(2026, 9, 30, 12, 0, tzinfo=timezone.utc)
    prev_obs = PriceObservation(1, Decimal("30000.00"), "INR", "amazon", seller_rating=4.8, observed_at=now - timedelta(hours=2))
    curr_obs = PriceObservation(
        1,
        Decimal("24000.00"),
        "INR",
        "amazon",
        seller_rating=4.8,
        coupon=Decimal("1000.00"),
        observed_at=now,
    )

    history_list = [curr_obs, prev_obs] + [PriceObservation(1, Decimal("30000.00"), "INR", "amazon", observed_at=now - timedelta(days=i)) for i in range(25)]
    metrics = compute_historical_metrics(history_list, now=now)
    drop_m = compute_drop_metrics(curr_obs, prev_obs, metrics)

    scorer = DealScorer()
    verdict = scorer.compute_score(
        product_name="Sony Headphones",
        current_obs=curr_obs,
        history=metrics,
        drop_metrics=drop_m,
        suspicious_discount=False,
    )

    assert verdict.deal_score >= 70.0
    assert "deal" in verdict.label.lower()
    assert len(verdict.factors) == 5
    assert verdict.confidence == "high"


def test_deal_labels_mapping():
    """Verify score to deal label thresholds."""
    assert "Excellent" in get_deal_label(90.0)
    assert "Strong" in get_deal_label(75.0)
    assert "Fair" in get_deal_label(60.0)
    assert "Average" in get_deal_label(45.0)
    assert "Skip" in get_deal_label(30.0)


def test_detector_and_rules():
    """Verify price drop detector, duplicate check, cooldown, and alert rule evaluation."""
    t1 = datetime(2026, 9, 30, 10, 0, tzinfo=timezone.utc)
    t2 = datetime(2026, 9, 30, 12, 0, tzinfo=timezone.utc)

    obs1 = PriceObservation(1, Decimal("1000.00"), "INR", "amazon", observed_at=t1)
    obs2 = PriceObservation(1, Decimal("1000.00"), "INR", "amazon", observed_at=t2)
    obs3 = PriceObservation(1, Decimal("800.00"), "INR", "amazon", observed_at=t2)

    assert is_duplicate_observation(obs1, obs2) is True
    assert is_duplicate_observation(obs1, obs3) is False

    assert is_in_cooldown(last_alert_at=t2 - timedelta(hours=2), cooldown_hours=6, now=t2) is True
    assert is_in_cooldown(last_alert_at=t2 - timedelta(hours=8), cooldown_hours=6, now=t2) is False

    has_dropped, drop_amt, drop_pct = detect_price_drop(obs3, obs1)
    assert has_dropped is True
    assert drop_amt == Decimal("200.00")
    assert drop_pct == 20.0
