"""
pricing/models.py
Domain models and dataclasses for the Deal Analysis Engine.
Strictly channel-agnostic — no Telegram or FastAPI dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any


@dataclass(slots=True)
class PriceObservation:
    """Core price observation dataclass per Section 4.1 specification."""

    product_id: int | None
    price: Decimal
    currency: str
    source: str
    in_stock: bool = True
    seller: str | None = None
    seller_rating: float | None = None
    coupon: Decimal | None = None
    bank_offer: Decimal | None = None
    exchange_offer: Decimal | None = None
    cashback: Decimal | None = None
    raw_offer_text: str | None = None
    observed_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    @property
    def total_discounts(self) -> Decimal:
        """Total stackable discounts."""
        total = Decimal("0.00")
        if self.coupon:
            total += self.coupon
        if self.bank_offer:
            total += self.bank_offer
        if self.exchange_offer:
            total += self.exchange_offer
        if self.cashback:
            total += self.cashback
        return total

    @property
    def effective_price(self) -> Decimal:
        """Listed price minus valid identified stackable offers."""
        eff = self.price - self.total_discounts
        return max(Decimal("0.00"), eff)


@dataclass(slots=True)
class HistoricalMetrics:
    """Historical context metrics per Section 4.3 specification."""

    current_price: Decimal
    previous_price: Decimal | None
    lowest_30d: Decimal
    lowest_90d: Decimal
    lowest_all_time: Decimal
    median_30d: Decimal
    median_90d: Decimal
    mean_30d: Decimal
    price_volatility_30d: float  # std deviation of % changes
    observation_count: int
    days_since_lowest: int
    confidence: str = "high"  # "high" | "low"


@dataclass(slots=True)
class DropMetrics:
    """Drop magnitude and velocity metrics per Section 4.4 specification."""

    absolute_drop: Decimal
    absolute_drop_pct: float
    drop_vs_30d_low: Decimal
    drop_vs_alltime_low: Decimal
    drop_velocity: float  # % change per hour


@dataclass(slots=True)
class DealVerdict:
    """Transparent deal score, label, and breakdown per Section 4.6 & 4.7 specification."""

    product_name: str
    deal_score: float
    label: str
    factors: list[dict[str, Any]]
    penalties: list[dict[str, Any]]
    confidence: str
    suspicious_discount: bool = False
    suspicious_reason: str | None = None
    caveat: str = "Score is a heuristic based on the factors shown, not a guarantee."
