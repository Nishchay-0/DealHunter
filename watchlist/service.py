"""
watchlist/service.py
Watchlist management service for querying, updating, and removing tracked products per user.
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database.models import Product, Watchlist
from watchlist.categories import infer_category

logger = logging.getLogger(__name__)


class WatchlistService:
    """Service managing user watchlists and target prices."""

    async def get_user_watchlist(
        self, session: AsyncSession, user_id: int
    ) -> list[dict[str, Any]]:
        """Return list of all products in user's watchlist with details."""
        stmt = (
            select(Watchlist, Product)
            .join(Product, Watchlist.product_id == Product.id)
            .where(Watchlist.user_id == user_id)
            .order_by(Watchlist.created_at.desc())
        )
        result = await session.execute(stmt)
        items: list[dict[str, Any]] = []

        for wl, prod in result.all():
            items.append({
                "watchlist_id": wl.id,
                "product_id": prod.id,
                "name": prod.name,
                "platform": prod.platform,
                "canonical_url": prod.canonical_url,
                "current_price": prod.list_price,
                "target_price": wl.target_price,
                "drop_threshold_pct": wl.drop_threshold_pct,
                "alert_mode": wl.alert_mode,
                "category": prod.category or infer_category(prod.name),
                "created_at": wl.created_at,
            })
        return items

    async def set_target_price(
        self,
        session: AsyncSession,
        user_id: int,
        product_id: int,
        target_price: Decimal,
    ) -> Watchlist | None:
        """Set or update target price for a watched product."""
        stmt = select(Watchlist).where(
            Watchlist.user_id == user_id,
            Watchlist.product_id == product_id,
        )
        res = await session.execute(stmt)
        item = res.scalars().first()
        if item:
            item.target_price = target_price
            await session.commit()
            logger.info("Updated target price to ₹%s for user %s, product %s", target_price, user_id, product_id)
            return item
        return None

    async def remove_from_watchlist(
        self, session: AsyncSession, user_id: int, product_id: int
    ) -> bool:
        """Remove a product from user's watchlist."""
        stmt = select(Watchlist).where(
            Watchlist.user_id == user_id,
            Watchlist.product_id == product_id,
        )
        res = await session.execute(stmt)
        item = res.scalars().first()
        if item:
            await session.delete(item)
            await session.commit()
            logger.info("Removed product %s from watchlist of user %s", product_id, user_id)
            return True
        return False
