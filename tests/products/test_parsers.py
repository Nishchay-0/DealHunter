"""
tests/products/test_parsers.py
Offline parser tests using HTML fixtures (never hits live websites).
"""

from decimal import Decimal
from pathlib import Path

from products.sources.amazon import AmazonSource
from products.sources.croma import CromaSource
from products.sources.flipkart import FlipkartSource
from products.sources.myntra import MyntraSource

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"


def test_parse_amazon_fixture():
    """Verify parsing Amazon offline HTML fixture."""
    fixture_path = FIXTURES_DIR / "amazon_sample.html"
    html_content = fixture_path.read_text(encoding="utf-8")

    source = AmazonSource()
    url = "https://www.amazon.in/dp/B0CHX1W1XY"
    product, obs = source.parse_html(html_content, url)

    assert "iPhone 15" in product.name
    assert product.external_id == "B0CHX1W1XY"
    assert obs.price == Decimal("71499.00")
    assert obs.currency == "INR"
    assert obs.in_stock is True
    assert obs.coupon == Decimal("2000.00")
    assert obs.effective_price == Decimal("69499.00")
    assert "Appario Retail" in (obs.seller or "")


def test_parse_flipkart_fixture():
    """Verify parsing Flipkart offline HTML fixture."""
    fixture_path = FIXTURES_DIR / "flipkart_sample.html"
    html_content = fixture_path.read_text(encoding="utf-8")

    source = FlipkartSource()
    url = "https://www.flipkart.com/sony/p/itm123?pid=MOBGGW7QZ7GHZNYW"
    product, obs = source.parse_html(html_content, url)

    assert "Sony WH-1000XM5" in product.name
    assert product.external_id == "MOBGGW7QZ7GHZNYW"
    assert obs.price == Decimal("26990.00")
    assert obs.bank_offer == Decimal("1500.00")
    assert obs.effective_price == Decimal("25490.00")
    assert obs.in_stock is True


def test_parse_croma_fixture():
    """Verify parsing Croma offline HTML fixture."""
    fixture_path = FIXTURES_DIR / "croma_sample.html"
    html_content = fixture_path.read_text(encoding="utf-8")

    source = CromaSource()
    url = "https://www.croma.com/p/265748"
    product, obs = source.parse_html(html_content, url)

    assert "LG OLED" in product.name
    assert product.external_id == "265748"
    assert obs.price == Decimal("99990.00")
    assert obs.in_stock is True


def test_parse_myntra_fixture():
    """Verify parsing Myntra offline HTML fixture."""
    fixture_path = FIXTURES_DIR / "myntra_sample.html"
    html_content = fixture_path.read_text(encoding="utf-8")

    source = MyntraSource()
    url = "https://www.myntra.com/24189340"
    product, obs = source.parse_html(html_content, url)

    assert "Nike Air Pegasus" in product.name
    assert product.external_id == "24189340"
    assert obs.price == Decimal("8995.00")
    assert obs.in_stock is True
