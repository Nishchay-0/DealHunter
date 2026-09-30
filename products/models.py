"""
products/models.py
Domain dataclasses for products and price observations.
Channel-agnostic and decoupled from transport/database layers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal


@dataclass(slots=True)
class PriceObservation:
    """
    Standard price and offer observation returned by any retailer source.
    Conforms to the DealHunter core engine specification (Section 4.1).
    """

    price: Decimal
    currency: str
    source: str
    in_stock: bool = True
    product_id: int | None = None
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
        """Total stackable discounts identified in this observation."""
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
class ProductData:
    """Standardized metadata for a tracked product across all platforms."""

    canonical_url: str
    platform: str
    external_id: str
    name: str
    currency: str = "INR"
    brand: str | None = None
    category: str | None = None
    image_url: str | None = None
    list_price: Decimal | None = None
