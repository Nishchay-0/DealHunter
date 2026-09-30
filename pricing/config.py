"""
pricing/config.py
Configurable weights, penalties, thresholds, and labels for the Deal Analysis Engine.
"""

from __future__ import annotations

# Factor Weights (Max points out of 100)
WEIGHT_HISTORICAL_POSITION: float = 40.0
WEIGHT_DROP_MAGNITUDE: float = 25.0
WEIGHT_DROP_VELOCITY: float = 10.0
WEIGHT_EFFECTIVE_PRICE: float = 15.0
WEIGHT_SELLER_TRUST: float = 10.0

# Penalties
PENALTY_SUSPICIOUS_DISCOUNT: float = 25.0
PENALTY_LOW_CONFIDENCE: float = 15.0

# Confidence Threshold
MIN_CONFIDENCE_OBSERVATIONS: int = 20


def get_deal_label(score: float) -> str:
    """Map numeric deal score (0-100) to human-readable deal label."""
    if score >= 85.0:
        return "🔥 Excellent deal"
    if score >= 70.0:
        return "🟢 Strong deal"
    if score >= 55.0:
        return "🟡 Fair deal"
    if score >= 40.0:
        return "⚪ Average — not urgent"
    return "🔴 Skip"
