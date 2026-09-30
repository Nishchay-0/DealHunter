"""
tests/watchlist/test_watchlist.py
Unit tests for WatchlistService and category inferencing.
"""

from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Product, User, Watchlist
from watchlist.categories import infer_category
from watchlist.service import WatchlistService


def test_category_inference():
    """Verify automated category classification by keywords."""
    assert infer_category("Apple iPhone 15 Pro Max 256GB") == "Mobiles & Tablets"
    assert infer_category("Apple MacBook Air M2 16GB RAM") == "Electronics & Laptops"
    assert infer_category("Sony WH-1000XM5 Wireless Headphones") == "Audio & Wearables"
    assert infer_category("LG 55 Inch 4K Smart OLED TV") == "TV & Appliances"
    assert infer_category("Nike Air Pegasus 40 Sneakers") == "Fashion & Apparel"
    assert infer_category("Generic Coffee Mug") == "General"


@pytest.mark.asyncio
async def test_watchlist_service_operations(test_session: AsyncSession):
    """Test WatchlistService query, target price update, and removal."""
    svc = WatchlistService()

    # 1. Setup User and Product
    user = User(telegram_id=888111, username="wl_user")
    prod = Product(
        canonical_url="https://amazon.in/dp/B0001",
        platform="amazon",
        external_id="B0001",
        name="Samsung Galaxy S24 Ultra",
        list_price=Decimal("129999.00"),
    )
    test_session.add_all([user, prod])
    await test_session.commit()

    # 2. Add to Watchlist
    wl_entry = Watchlist(user_id=user.id, product_id=prod.id, target_price=Decimal("120000.00"))
    test_session.add(wl_entry)
    await test_session.commit()

    # 3. Query watchlist
    items = await svc.get_user_watchlist(test_session, user.id)
    assert len(items) == 1
    assert items[0]["name"] == "Samsung Galaxy S24 Ultra"
    assert items[0]["category"] == "Mobiles & Tablets"
    assert items[0]["target_price"] == Decimal("120000.00")

    # 4. Update target price
    updated = await svc.set_target_price(test_session, user.id, prod.id, Decimal("115000.00"))
    assert updated is not None
    assert updated.target_price == Decimal("115000.00")

    # 5. Remove item
    removed = await svc.remove_from_watchlist(test_session, user.id, prod.id)
    assert removed is True

    items_after = await svc.get_user_watchlist(test_session, user.id)
    assert len(items_after) == 0
