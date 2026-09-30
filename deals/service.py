"""
deals/service.py
Deal discovery service identifying top price drops across all catalog products.
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import PriceHistory, Product
from watchlist.categories import infer_category

logger = logging.getLogger(__name__)


class DealsService:
    """Service to discover and filter active price drops and deals."""

    async def get_top_deals(
        self,
        session: AsyncSession,
        category: str | None = None,
        min_drop_pct: float = 5.0,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """
        Query catalog products that experienced recent price reductions.
        Returns sorted list of deals with drop metrics.
        """
        stmt = select(Product).where(Product.observation_count > 1).order_by(Product.last_checked_at.desc())
        res = await session.execute(stmt)
        products = res.scalars().all()

        deals: list[dict[str, Any]] = []

        for prod in products:
            prod_cat = prod.category or infer_category(prod.name)
            if category and category.lower() not in prod_cat.lower():
                continue

            # Fetch last 2 price observations
            hist_stmt = (
                select(PriceHistory)
                .where(PriceHistory.product_id == prod.id)
                .order_by(desc(PriceHistory.observed_at))
                .limit(2)
            )
            hist_res = await session.execute(hist_stmt)
            history = hist_res.scalars().all()

            if len(history) < 2:
                continue

            latest = history[0]
            previous = history[1]

            if previous.listed_price <= Decimal("0.00"):
                continue

            if latest.listed_price < previous.listed_price:
                drop_amount = previous.listed_price - latest.listed_price
                drop_pct = float((drop_amount / previous.listed_price) * Decimal("100"))

                if drop_pct >= min_drop_pct:
                    deals.append({
                        "product_id": prod.id,
                        "name": prod.name,
                        "platform": prod.platform,
                        "canonical_url": prod.canonical_url,
                        "current_price": latest.listed_price,
                        "previous_price": previous.listed_price,
                        "effective_price": latest.effective_price,
                        "drop_amount": drop_amount,
                        "drop_pct": drop_pct,
                        "coupon": latest.coupon,
                        "bank_offer": latest.bank_offer,
                        "category": prod_cat,
                    })

        # Sort by highest drop percentage
        deals.sort(key=lambda x: x["drop_pct"], reverse=True)
        return deals[:limit]
