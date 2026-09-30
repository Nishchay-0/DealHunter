"""
notifications/models.py
Data structures for deal and price-drop notifications.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any


@dataclass(slots=True)
class AlertPayload:
    """Contains all details required to format and dispatch a price alert."""

    product_id: int
    product_name: str
    platform: str
    canonical_url: str
    rule: str  # TARGET_HIT | PRICE_DROP | BIG_DEAL | ALL_TIME_LOW | COUPON_ALERT
    previous_price: Decimal
    current_price: Decimal
    effective_price: Decimal
    currency: str = "INR"
    coupon: Decimal | None = None
    bank_offer: Decimal | None = None
    deal_score: float | None = None
    factors: list[dict[str, Any]] = field(default_factory=list)
    condition_notes: list[str] = field(default_factory=list)

    @property
    def drop_amount(self) -> Decimal:
        """Absolute price reduction."""
        return max(Decimal("0.00"), self.previous_price - self.current_price)

    @property
    def drop_pct(self) -> float:
        """Percentage price drop compared to previous price."""
        if self.previous_price <= Decimal("0.00"):
            return 0.0
        return float((self.drop_amount / self.previous_price) * Decimal("100"))
