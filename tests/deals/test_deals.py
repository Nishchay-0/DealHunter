"""
tests/deals/test_deals.py
Unit tests for DealsService price-drop discovery.
"""

from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import PriceHistory, Product
from deals.service import DealsService


@pytest.mark.asyncio
async def test_deals_service_discovery(test_session: AsyncSession):
    """Test DealsService queries active price drops sorted by drop percentage."""
    svc = DealsService()

    # Product 1: 20% drop (iPhone)
    p1 = Product(
        canonical_url="https://amazon.in/dp/B001",
        platform="amazon",
        external_id="B001",
        name="Apple iPhone 15 (128GB)",
        list_price=Decimal("64000.00"),
        observation_count=2,
    )
    # Product 2: 10% drop (MacBook)
    p2 = Product(
        canonical_url="https://amazon.in/dp/B002",
        platform="amazon",
        external_id="B002",
        name="Apple MacBook Air M2",
        list_price=Decimal("90000.00"),
        observation_count=2,
    )
    test_session.add_all([p1, p2])
    await test_session.commit()

    # Product 1 history (80k -> 64k = 20% drop)
    h1_old = PriceHistory(product_id=p1.id, listed_price=Decimal("80000.00"), effective_price=Decimal("80000.00"), source="amazon")
    h1_new = PriceHistory(product_id=p1.id, listed_price=Decimal("64000.00"), effective_price=Decimal("64000.00"), source="amazon")

    # Product 2 history (100k -> 90k = 10% drop)
    h2_old = PriceHistory(product_id=p2.id, listed_price=Decimal("100000.00"), effective_price=Decimal("100000.00"), source="amazon")
    h2_new = PriceHistory(product_id=p2.id, listed_price=Decimal("90000.00"), effective_price=Decimal("90000.00"), source="amazon")

    test_session.add_all([h1_old, h1_new, h2_old, h2_new])
    await test_session.commit()

    # Query all top deals
    top_deals = await svc.get_top_deals(test_session, min_drop_pct=5.0)
    assert len(top_deals) == 2
    assert top_deals[0]["product_id"] == p1.id  # Highest drop % first (20%)
    assert top_deals[0]["drop_pct"] == 20.0
    assert top_deals[1]["product_id"] == p2.id  # 10% drop second

    # Query category filtered deals
    mobile_deals = await svc.get_top_deals(test_session, category="Mobiles")
    assert len(mobile_deals) == 1
    assert mobile_deals[0]["name"] == "Apple iPhone 15 (128GB)"
