"""
tests/products/test_service.py
End-to-end tests for ProductTrackingService against test database.
"""

from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import PriceHistory, Product, User, Watchlist
from products.service import ProductTrackingService

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"


@pytest.mark.asyncio
async def test_track_new_product_and_watchlist(test_session: AsyncSession):
    """Test tracking a new product URL creates Product, PriceHistory, and Watchlist."""
    # 1. Create a user
    user = User(telegram_id=999888777, username="shopper")
    test_session.add(user)
    await test_session.commit()

    amazon_fixture = (FIXTURES_DIR / "amazon_sample.html").read_text(encoding="utf-8")
    service = ProductTrackingService()

    # 2. Track product
    url = "https://www.amazon.in/dp/B0CHX1W1XY?ref=deal"
    product, obs, is_new = await service.track_product(
        url=url,
        session=test_session,
        user_id=user.id,
        target_price=Decimal("70000.00"),
        drop_threshold_pct=4.0,
        html_fixture=amazon_fixture,
    )

    assert is_new is True
    assert product.id is not None
    assert product.platform == "amazon"
    assert product.external_id == "B0CHX1W1XY"
    assert product.list_price == Decimal("71499.00")
    assert product.observation_count == 1

    # 3. Verify PriceHistory
    ph_result = await test_session.execute(
        select(PriceHistory).where(PriceHistory.product_id == product.id)
    )
    histories = ph_result.scalars().all()
    assert len(histories) == 1
    assert histories[0].listed_price == Decimal("71499.00")
    assert histories[0].effective_price == Decimal("69499.00")
    assert histories[0].coupon == Decimal("2000.00")

    # 4. Verify Watchlist
    wl_result = await test_session.execute(
        select(Watchlist).where(Watchlist.user_id == user.id)
    )
    watchlist_items = wl_result.scalars().all()
    assert len(watchlist_items) == 1
    assert watchlist_items[0].product_id == product.id
    assert watchlist_items[0].target_price == Decimal("70000.00")
    assert watchlist_items[0].drop_threshold_pct == 4.0


@pytest.mark.asyncio
async def test_track_existing_product_increments_count(test_session: AsyncSession):
    """Tracking an already cataloged product updates observation count and adds history."""
    amazon_fixture = (FIXTURES_DIR / "amazon_sample.html").read_text(encoding="utf-8")
    service = ProductTrackingService()

    url = "https://www.amazon.in/dp/B0CHX1W1XY"

    # First check
    p1, obs1, is_new1 = await service.track_product(
        url=url,
        session=test_session,
        html_fixture=amazon_fixture,
    )
    assert is_new1 is True
    assert p1.observation_count == 1

    # Second check
    p2, obs2, is_new2 = await service.track_product(
        url=url,
        session=test_session,
        html_fixture=amazon_fixture,
    )
    assert is_new2 is False
    assert p2.id == p1.id
    assert p2.observation_count == 2

    # Check history rows
    ph_result = await test_session.execute(
        select(PriceHistory).where(PriceHistory.product_id == p1.id)
    )
    assert len(ph_result.scalars().all()) == 2
