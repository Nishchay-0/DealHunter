"""
scheduler/runner.py
Core price monitoring scheduler coordinating:
- Dynamic check frequency (6h default, 1h popular, 30m post-drop)
- Exponential backoff retries (3 attempts)
- Circuit breaker protection per source
- Observation idempotency
- Rule-based price drop detection and notification triggering
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import PriceHistory, Product, User, Watchlist
from notifications.dispatcher import NotificationDispatcher
from notifications.models import AlertPayload
from products.models import PriceObservation
from products.sources.registry import SourceRegistry, default_registry
from scheduler.circuit_breaker import CircuitBreaker

logger = logging.getLogger(__name__)


class PriceCheckScheduler:
    """Orchestrates periodic price verification and alert triggering."""

    def __init__(
        self,
        registry: SourceRegistry | None = None,
        dispatcher: NotificationDispatcher | None = None,
        circuit_breaker: CircuitBreaker | None = None,
        max_retries: int = 3,
        retry_base_delay: float = 1.0,
    ) -> None:
        self.registry = registry or default_registry
        self.dispatcher = dispatcher or NotificationDispatcher()
        self.circuit_breaker = circuit_breaker or CircuitBreaker()
        self.max_retries = max_retries
        self.retry_base_delay = retry_base_delay

    @staticmethod
    def calculate_check_interval(
        product: Product,
        watcher_count: int,
        last_drop_at: datetime | None,
        now: datetime | None = None,
    ) -> timedelta:
        """
        Dynamic check frequency per Section 7:
        - Recently dropped (<24h): every 30-60 min
        - Popular (>2 watchers): every 1-2h
        - Default: every 6h
        """
        now = now or datetime.now(timezone.utc)
        if last_drop_at and (now - last_drop_at) <= timedelta(hours=24):
            return timedelta(minutes=30)
        if watcher_count > 2:
            return timedelta(hours=1)
        return timedelta(hours=6)

    async def fetch_with_retry(
        self,
        source_name: str,
        url: str,
        html_fixture: str | None = None,
    ) -> PriceObservation:
        """Fetch price observation with exponential backoff and circuit breaker check."""
        if not self.circuit_breaker.is_available(source_name):
            raise RuntimeError(f"Circuit breaker is OPEN for source '{source_name}'; check suspended")

        source = self.registry.get_source(url)

        last_exc: Exception | None = None
        for attempt in range(self.max_retries):
            try:
                if html_fixture is not None:
                    html_content = html_fixture
                else:
                    html_content = await source.fetch_page(url)

                _, observation = source.parse_html(html_content, url)
                self.circuit_breaker.record_success(source_name)
                return observation
            except Exception as exc:
                last_exc = exc
                logger.warning(
                    "[%s] Attempt %d/%d failed for %s: %s",
                    source_name,
                    attempt + 1,
                    self.max_retries,
                    url,
                    exc,
                )
                if attempt < self.max_retries - 1:
                    delay = self.retry_base_delay * (2 ** attempt)
                    await asyncio.sleep(delay)

        # Record failure with circuit breaker
        self.circuit_breaker.record_failure(source_name, str(last_exc))
        raise last_exc or RuntimeError(f"Failed to fetch price from {source_name}")

    async def check_product(
        self,
        product: Product,
        session: AsyncSession,
        html_fixture: str | None = None,
    ) -> tuple[PriceObservation | None, bool]:
        """
        Check a single product's price, record history (if changed),
        and trigger alerts for watching users.
        Returns (observation, is_duplicate).
        """
        source = self.registry.get_source(product.canonical_url)

        try:
            observation = await self.fetch_with_retry(
                source_name=source.name,
                url=product.canonical_url,
                html_fixture=html_fixture,
            )
        except Exception as exc:
            logger.error("Failed checking product %s (%s): %s", product.id, product.name, exc)
            return None, False

        now = datetime.now(timezone.utc)

        # 1. Fetch latest recorded price history
        latest_hist_stmt = (
            select(PriceHistory)
            .where(PriceHistory.product_id == product.id)
            .order_by(desc(PriceHistory.observed_at))
            .limit(1)
        )
        hist_res = await session.execute(latest_hist_stmt)
        latest_hist = hist_res.scalars().first()

        previous_price = latest_hist.listed_price if latest_hist else product.list_price or observation.price

        # 2. Idempotency Check: Don't store duplicate observations
        is_duplicate = False
        if latest_hist is not None:
            if (
                latest_hist.listed_price == observation.price
                and latest_hist.effective_price == observation.effective_price
                and latest_hist.in_stock == observation.in_stock
                and latest_hist.coupon == observation.coupon
                and latest_hist.bank_offer == observation.bank_offer
            ):
                is_duplicate = True

        if not is_duplicate:
            new_history = PriceHistory(
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
            session.add(new_history)

        # Update product metadata
        product.list_price = observation.price
        product.last_checked_at = now
        product.observation_count += 1
        await session.commit()

        # 3. Detect price drops and alert watching users
        if observation.price < previous_price:
            drop_amount = previous_price - observation.price
            drop_pct = float((drop_amount / previous_price) * Decimal("100"))

            # Query all users watching this product
            wl_stmt = (
                select(Watchlist, User)
                .join(User, Watchlist.user_id == User.id)
                .where(Watchlist.product_id == product.id)
            )
            wl_res = await session.execute(wl_stmt)

            for watchlist_item, user in wl_res.all():
                rule: str | None = None

                # Rule 1: Target hit
                if watchlist_item.target_price and observation.price <= watchlist_item.target_price:
                    rule = "TARGET_HIT"
                # Rule 2: Big deal (>= 15% drop)
                elif drop_pct >= 15.0:
                    rule = "BIG_DEAL"
                # Rule 3: User drop threshold hit (default 5%)
                elif drop_pct >= (watchlist_item.drop_threshold_pct or 5.0):
                    rule = "PRICE_DROP"

                if rule:
                    payload = AlertPayload(
                        product_id=product.id,
                        product_name=product.name,
                        platform=product.platform,
                        canonical_url=product.canonical_url,
                        rule=rule,
                        previous_price=previous_price,
                        current_price=observation.price,
                        effective_price=observation.effective_price,
                        currency=product.currency or "INR",
                        coupon=observation.coupon,
                        bank_offer=observation.bank_offer,
                    )
                    await self.dispatcher.dispatch_alert(user, payload, session)

        return observation, is_duplicate
