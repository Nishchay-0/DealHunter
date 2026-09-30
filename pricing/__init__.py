"""
pricing package for DealHunter.
Isolated, testable Deal Analysis Engine.
"""

from pricing.analyzer import detect_fake_discount
from pricing.config import (
    MIN_CONFIDENCE_OBSERVATIONS,
    WEIGHT_DROP_MAGNITUDE,
    WEIGHT_DROP_VELOCITY,
    WEIGHT_EFFECTIVE_PRICE,
    WEIGHT_HISTORICAL_POSITION,
    WEIGHT_SELLER_TRUST,
    get_deal_label,
)
from pricing.detector import (
    detect_price_drop,
    is_duplicate_observation,
    is_in_cooldown,
)
from pricing.effective_price import calculate_effective_price
from pricing.history import compute_drop_metrics, compute_historical_metrics
from pricing.models import DealVerdict, DropMetrics, HistoricalMetrics, PriceObservation
from pricing.rules import evaluate_alert_rules
from pricing.scorer import DealScorer

__all__ = [
    "PriceObservation",
    "HistoricalMetrics",
    "DropMetrics",
    "DealVerdict",
    "calculate_effective_price",
    "compute_historical_metrics",
    "compute_drop_metrics",
    "detect_fake_discount",
    "DealScorer",
    "detect_price_drop",
    "is_duplicate_observation",
    "is_in_cooldown",
    "evaluate_alert_rules",
    "get_deal_label",
    "MIN_CONFIDENCE_OBSERVATIONS",
    "WEIGHT_HISTORICAL_POSITION",
    "WEIGHT_DROP_MAGNITUDE",
    "WEIGHT_DROP_VELOCITY",
    "WEIGHT_EFFECTIVE_PRICE",
    "WEIGHT_SELLER_TRUST",
]
