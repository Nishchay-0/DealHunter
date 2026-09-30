"""
tests/notifications/test_renderer.py
Tests for message formatting, discount breakdowns, and disclaimer caveats.
"""

from decimal import Decimal

from notifications.models import AlertPayload
from notifications.renderer import MessageRenderer


def test_render_basic_price_drop():
    """Verify standard price drop message format."""
    payload = AlertPayload(
        product_id=1,
        product_name="Apple iPhone 15 (128 GB)",
        platform="amazon",
        canonical_url="https://www.amazon.in/dp/B0CHX1W1XY",
        rule="PRICE_DROP",
        previous_price=Decimal("79900.00"),
        current_price=Decimal("71499.00"),
        effective_price=Decimal("69499.00"),
        coupon=Decimal("2000.00"),
    )

    rendered = MessageRenderer.render(payload)

    assert "PRICE DROP DETECTED" in rendered
    assert "Apple iPhone 15" in rendered
    assert "₹79,900.00" in rendered
    assert "₹71,499.00" in rendered
    assert "₹69,499.00" in rendered
    assert "Coupon Discount: -₹2,000.00" in rendered
    assert "Disclaimer:" in rendered
    assert "not a purchase guarantee" in rendered


def test_render_target_hit_with_deal_factors():
    """Verify target hit message with deal factors and conditions."""
    payload = AlertPayload(
        product_id=2,
        product_name="Sony WH-1000XM5",
        platform="flipkart",
        canonical_url="https://www.flipkart.com/p/item?pid=MOB123",
        rule="TARGET_HIT",
        previous_price=Decimal("29990.00"),
        current_price=Decimal("24990.00"),
        effective_price=Decimal("23490.00"),
        bank_offer=Decimal("1500.00"),
        deal_score=85.0,
        factors=[
            {"name": "historical_position", "note": "Near 90-day low"},
            {"name": "drop_magnitude", "note": "16.7% drop"},
        ],
        condition_notes=["HDFC Bank Credit Cards only"],
    )

    rendered = MessageRenderer.render(payload)

    assert "TARGET PRICE HIT" in rendered
    assert "*Deal Score:* 85/100" in rendered
    assert "Near 90-day low" in rendered
    assert "HDFC Bank Credit Cards only" in rendered
