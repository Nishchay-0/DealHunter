"""
tests/database/test_models.py
Unit tests verifying SQLAlchemy models, schema constraints, and CRUD operations.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import (
    AlertSent,
    AuditLog,
    Offer,
    PriceHistory,
    Product,
    Source,
    User,
    Watchlist,
)


@pytest.mark.asyncio
async def test_create_source(test_session: AsyncSession):
    """Test creating and retrieving a price source."""
    source = Source(name="amazon_in", enabled=True, rate_limit_per_min=15)
    test_session.add(source)
    await test_session.commit()

    result = await test_session.execute(
        select(Source).where(Source.name == "amazon_in")
    )
    saved = result.scalar_one()
    assert saved.id is not None
    assert saved.name == "amazon_in"
    assert saved.enabled is True
    assert saved.rate_limit_per_min == 15
    assert "amazon_in" in repr(saved)


@pytest.mark.asyncio
async def test_create_user_and_product(test_session: AsyncSession):
    """Test creating users, products, and price history."""
    user = User(
        telegram_id=123456789,
        username="dealfinder",
        timezone="Asia/Kolkata",
    )
    product = Product(
        canonical_url="https://amazon.in/dp/B09G9FPHY6",
        platform="amazon",
        external_id="B09G9FPHY6",
        name="Apple iPhone 13 (128GB) - Midnight",
        currency="INR",
        list_price=Decimal("49999.00"),
    )
    test_session.add_all([user, product])
    await test_session.commit()

    assert user.id is not None
    assert product.id is not None
    assert user.username == "dealfinder"
    assert str(user.telegram_id) in repr(user)
    assert "Apple iPhone" in repr(product)


@pytest.mark.asyncio
async def test_price_history_and_watchlist(test_session: AsyncSession):
    """Test price history tracking and watchlist associations."""
    user = User(telegram_id=987654321, username="test_shopper")
    product = Product(
        canonical_url="https://flipkart.com/p/item123",
        platform="flipkart",
        external_id="item123",
        name="Sony WH-1000XM5 Headphones",
        currency="INR",
        list_price=Decimal("29990.00"),
    )
    test_session.add_all([user, product])
    await test_session.commit()

    # Price observation
    history = PriceHistory(
        product_id=product.id,
        listed_price=Decimal("26990.00"),
        effective_price=Decimal("24990.00"),
        coupon=Decimal("1000.00"),
        bank_offer=Decimal("1000.00"),
        in_stock=True,
        seller="Appario Retail",
        seller_rating=4.6,
        source="flipkart",
    )
    # Watchlist entry
    watchlist = Watchlist(
        user_id=user.id,
        product_id=product.id,
        target_price=Decimal("25000.00"),
        drop_threshold_pct=5.0,
    )
    test_session.add_all([history, watchlist])
    await test_session.commit()

    assert history.id is not None
    assert watchlist.id is not None
    assert f"user_id={user.id}" in repr(watchlist)
    assert f"product_id={product.id}" in repr(watchlist)


@pytest.mark.asyncio
async def test_watchlist_unique_constraint(test_session: AsyncSession):
    """A user cannot add the same product twice to their watchlist."""
    user = User(telegram_id=111222333)
    product = Product(
        canonical_url="https://amazon.in/dp/B08N5WRWNW",
        platform="amazon",
        external_id="B08N5WRWNW",
        name="MacBook Air M1",
        currency="INR",
    )
    test_session.add_all([user, product])
    await test_session.commit()

    entry1 = Watchlist(user_id=user.id, product_id=product.id)
    test_session.add(entry1)
    await test_session.commit()

    entry2 = Watchlist(user_id=user.id, product_id=product.id)
    test_session.add(entry2)
    with pytest.raises(IntegrityError):
        await test_session.commit()
    await test_session.rollback()


@pytest.mark.asyncio
async def test_alerts_offers_and_audit(test_session: AsyncSession):
    """Test AlertSent, Offer, and AuditLog records."""
    user = User(telegram_id=444555666)
    product = Product(
        canonical_url="https://croma.com/p/123",
        platform="croma",
        external_id="123",
        name="LG OLED C3 55-inch TV",
        currency="INR",
    )
    test_session.add_all([user, product])
    await test_session.commit()

    alert = AlertSent(
        user_id=user.id,
        product_id=product.id,
        rule="TARGET_HIT",
        deal_score=88.5,
        channel="telegram",
        payload_json={"message": "Price hit your target ₹1,00,000!"},
    )
    offer = Offer(
        product_id=product.id,
        type="bank",
        value=Decimal("5000.00"),
        condition_text="HDFC Credit Card Instant Discount",
        source="croma",
    )
    log = AuditLog(
        actor="system",
        action="PRICE_SCRAPED",
        entity="product",
        entity_id=product.id,
        meta_json={"price": 99990.0},
    )
    test_session.add_all([alert, offer, log])
    await test_session.commit()

    assert alert.id is not None
    assert offer.id is not None
    assert log.id is not None
    assert "TARGET_HIT" in repr(alert)
    assert "bank" in repr(offer)
    assert "PRICE_SCRAPED" in repr(log)
