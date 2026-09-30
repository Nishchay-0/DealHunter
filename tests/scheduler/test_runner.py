"""
tests/scheduler/test_runner.py
Unit and integration tests for PriceCheckScheduler.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import PriceHistory, Product, User, Watchlist
from notifications.base import Notifier
from notifications.dispatcher import NotificationDispatcher
from notifications.models import AlertPayload
from scheduler.runner import PriceCheckScheduler

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"


class RecordingNotifier(Notifier):
    channel_name = "telegram"

    def __init__(self):
        self.dispatched: list[AlertPayload] = []

    async def send_alert(self, user: User, payload: AlertPayload, message_text: str) -> bool:
        self.dispatched.append(payload)
        return True


def test_calculate_check_interval():
    """Verify dynamic intervals: 30m (recent drop), 1h (popular), 6h (default)."""
    now = datetime(2026, 9, 30, 12, 0, tzinfo=timezone.utc)
    dummy_prod = Product(canonical_url="https://amazon.in/dp/1", platform="amazon", external_id="1", name="Item")

    # 1. Recent drop (<24h ago) -> 30 min
    recent_drop = now - timedelta(hours=2)
    assert PriceCheckScheduler.calculate_check_interval(dummy_prod, watcher_count=1, last_drop_at=recent_drop, now=now) == timedelta(minutes=30)

    # 2. Popular (>2 watchers) -> 1 hour
    assert PriceCheckScheduler.calculate_check_interval(dummy_prod, watcher_count=5, last_drop_at=None, now=now) == timedelta(hours=1)

    # 3. Default -> 6 hours
    assert PriceCheckScheduler.calculate_check_interval(dummy_prod, watcher_count=1, last_drop_at=None, now=now) == timedelta(hours=6)


@pytest.mark.asyncio
async def test_scheduler_idempotency(test_session: AsyncSession):
    """If price and offers are unchanged, do not insert duplicate PriceHistory rows."""
    product = Product(
        canonical_url="https://www.amazon.in/dp/B0CHX1W1XY",
        platform="amazon",
        external_id="B0CHX1W1XY",
        name="Apple iPhone 15",
        currency="INR",
        list_price=Decimal("71499.00"),
    )
    test_session.add(product)
    await test_session.commit()

    amazon_fixture = (FIXTURES_DIR / "amazon_sample.html").read_text(encoding="utf-8")
    scheduler = PriceCheckScheduler(retry_base_delay=0.01)

    # 1st check -> records history
    obs1, is_dup1 = await scheduler.check_product(product, test_session, html_fixture=amazon_fixture)
    assert is_dup1 is False

    # 2nd check with exact same fixture -> flagged as duplicate, history row count remains 1
    obs2, is_dup2 = await scheduler.check_product(product, test_session, html_fixture=amazon_fixture)
    assert is_dup2 is True

    hist_res = await test_session.execute(select(PriceHistory).where(PriceHistory.product_id == product.id))
    assert len(hist_res.scalars().all()) == 1


@pytest.mark.asyncio
async def test_scheduler_triggers_target_hit_alert(test_session: AsyncSession):
    """When current price drops to/below target price, dispatch TARGET_HIT alert."""
    # 1. Setup User and Product with higher initial price
    user = User(telegram_id=777, username="deal_watcher")
    product = Product(
        canonical_url="https://www.amazon.in/dp/B0CHX1W1XY",
        platform="amazon",
        external_id="B0CHX1W1XY",
        name="Apple iPhone 15",
        currency="INR",
        list_price=Decimal("79999.00"),  # old price
    )
    test_session.add_all([user, product])
    await test_session.commit()

    # Initial history at old price
    old_hist = PriceHistory(
        product_id=product.id,
        listed_price=Decimal("79999.00"),
        effective_price=Decimal("79999.00"),
        source="amazon",
    )
    # User watchlist with target 75,000
    watchlist = Watchlist(
        user_id=user.id,
        product_id=product.id,
        target_price=Decimal("75000.00"),
        drop_threshold_pct=5.0,
    )
    test_session.add_all([old_hist, watchlist])
    await test_session.commit()

    # 2. Run scheduler with sample fixture where price is 71,499 (< 75,000 target)
    recording_notifier = RecordingNotifier()
    dispatcher = NotificationDispatcher(notifiers=[recording_notifier])
    scheduler = PriceCheckScheduler(dispatcher=dispatcher, retry_base_delay=0.01)

    amazon_fixture = (FIXTURES_DIR / "amazon_sample.html").read_text(encoding="utf-8")
    await scheduler.check_product(product, test_session, html_fixture=amazon_fixture)

    # 3. Verify alert dispatched
    assert len(recording_notifier.dispatched) == 1
    alert = recording_notifier.dispatched[0]
    assert alert.rule == "TARGET_HIT"
    assert alert.current_price == Decimal("71499.00")
    assert alert.previous_price == Decimal("79999.00")
