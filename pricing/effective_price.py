"""
pricing/effective_price.py
Effective price calculation and offer condition parsing per Section 4.2.
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pricing.models import PriceObservation


def calculate_effective_price(
    obs: PriceObservation,
) -> tuple[Decimal, Decimal, list[str]]:
    """
    Calculate (listed_price, effective_price, condition_notes).
    Guarantees both listed_price and effective_price are tracked.
    """
    listed_price = obs.price
    total_discounts = Decimal("0.00")
    notes: list[str] = []

    if obs.coupon and obs.coupon > Decimal("0.00"):
        total_discounts += obs.coupon
        notes.append(f"Coupon applied: -₹{obs.coupon:,.2f}")

    if obs.bank_offer and obs.bank_offer > Decimal("0.00"):
        total_discounts += obs.bank_offer
        notes.append(f"Bank offer applied: -₹{obs.bank_offer:,.2f} (Requires qualifying bank card)")

    if obs.exchange_offer and obs.exchange_offer > Decimal("0.00"):
        total_discounts += obs.exchange_offer
        notes.append(f"Exchange offer applied: -₹{obs.exchange_offer:,.2f} (Requires eligible trade-in device)")

    if obs.cashback and obs.cashback > Decimal("0.00"):
        total_discounts += obs.cashback
        notes.append(f"Cashback: -₹{obs.cashback:,.2f}")

    effective_price = max(Decimal("0.00"), listed_price - total_discounts)
    return listed_price, effective_price, notes
