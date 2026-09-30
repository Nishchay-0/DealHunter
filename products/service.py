"""
products/service.py
ProductTrackingService orchestrating URL resolution, cataloging,
price observation recording, and user watchlisting.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import AuditLog, PriceHistory, Product, Watchlist
from products.models import PriceObservation, ProductData
from products.sources.base import PriceSource
from products.sources.registry import SourceRegistry, default_registry

logger = logging.getLogger(__name__)


class ProductTrackingService:
    """Service to track products and record historical price observations."""

    def __init__(self, registry: SourceRegistry | None = None) -> None:
        self.registry = registry or default_registry

    async def get_or_fetch_observation(
        self,
        source: PriceSource,
        url: str,
        html_content: str | None = None,
    ) -> tuple[ProductData, PriceObservation]:
        """Fetch page (or use provided HTML fixture) and parse product + price."""
        if html_content is None:
            html_content = await source.fetch_page(url)
        return source.parse_html(html_content, url)

    async def track_product(
        self,
        url: str,
        session: AsyncSession,
        user_id: int | None = None,
        target_price: Decimal | None = None,
        drop_threshold_pct: float = 5.0,
        html_fixture: str | None = None,
    ) -> tuple[Product, PriceObservation, bool]:
        """
        Track a product given its URL.
        - Resolves platform source
        - Extracts metadata and current price observation
        - Creates or updates Product record
        - Records a new PriceHistory entry
        - Optionally links to user's Watchlist
        """
        source, canonical_url, ext_id = self.registry.resolve(url)

        product_data, observation = await self.get_or_fetch_observation(
            source=source,
            url=url,
            html_content=html_fixture,
        )

        now = datetime.now(timezone.utc)

        # 1. Check if product already exists
        query = select(Product).where(
            (Product.canonical_url == canonical_url)
            | ((Product.platform == source.name) & (Product.external_id == ext_id))
        )
        result = await session.execute(query)
        product = result.scalars().first()

        is_new = product is None
        if is_new:
            product = Product(
                canonical_url=canonical_url,
                platform=source.name,
                external_id=ext_id or product_data.external_id,
                name=product_data.name,
                brand=product_data.brand,
                category=product_data.category,
                image_url=product_data.image_url,
                list_price=observation.price,
                currency=observation.currency,
                last_checked_at=now,
                observation_count=1,
            )
            session.add(product)
            await session.flush()  # Flush to generate product.id
        else:
            # Update existing product
            if product_data.name and product_data.name != "Amazon Product":
                product.name = product_data.name
            if product_data.image_url:
                product.image_url = product_data.image_url
            product.list_price = observation.price
            product.last_checked_at = now
            product.observation_count += 1

        # 2. Record PriceHistory
        history = PriceHistory(
            product_id=product.id,
            listed_price=observation.price,
            effective_price=observation.effective_price,
            coupon=observation.coupon,
            bank_offer=observation.bank_offer,
            exchange_offer=observation.exchange_offer,
            cashback=observation.cashback,
            in_stock=observation.in_stock,
            seller=observation.seller,
            seller_rating=observation.seller_rating,
            source=source.name,
            observed_at=observation.observed_at,
        )
        session.add(history)

        # 3. Add to Watchlist if user_id is provided
        if user_id is not None:
            wl_query = select(Watchlist).where(
                Watchlist.user_id == user_id,
                Watchlist.product_id == product.id,
            )
            wl_result = await session.execute(wl_query)
            watchlist_item = wl_result.scalars().first()

            if watchlist_item is None:
                watchlist_item = Watchlist(
                    user_id=user_id,
                    product_id=product.id,
                    target_price=target_price,
                    drop_threshold_pct=drop_threshold_pct,
                )
                session.add(watchlist_item)
            else:
                if target_price is not None:
                    watchlist_item.target_price = target_price
                if drop_threshold_pct is not None:
                    watchlist_item.drop_threshold_pct = drop_threshold_pct

        # 4. Record Audit Log
        audit = AuditLog(
            actor=f"user:{user_id}" if user_id else "system",
            action="TRACK_PRODUCT",
            entity="product",
            entity_id=product.id,
            meta_json={
                "canonical_url": canonical_url,
                "price": float(observation.price),
                "is_new": is_new,
            },
        )
        session.add(audit)
        await session.commit()

        return product, observation, is_new
