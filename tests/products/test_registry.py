"""
tests/products/test_registry.py
Tests for URL to PriceSource resolution and canonicalization.
"""

import pytest

from products.sources.registry import (
    SourceRegistry,
    UnsupportedPlatformError,
    default_registry,
)


def test_registry_has_four_retailers():
    """Verify default registry provides Amazon, Flipkart, Croma, Myntra."""
    sources = default_registry.list_sources()
    names = {s.name for s in sources}
    assert {"amazon", "flipkart", "croma", "myntra"}.issubset(names)


@pytest.mark.parametrize(
    "url,expected_source,expected_canonical,expected_id",
    [
        (
            "https://www.amazon.in/Apple-iPhone-15-128-GB/dp/B0CHX1W1XY?th=1&psc=1",
            "amazon",
            "https://www.amazon.in/dp/B0CHX1W1XY",
            "B0CHX1W1XY",
        ),
        (
            "https://amzn.in/d/9XYZ1234AB",
            "amazon",
            "https://www.amazon.in/dp/9XYZ1234AB",
            "9XYZ1234AB",
        ),
        (
            "https://www.flipkart.com/sony-wh-1000xm5/p/itm123456789?pid=MOBGGW7QZ7GHZNYW&lid=LST123",
            "flipkart",
            "https://www.flipkart.com/p/item?pid=MOBGGW7QZ7GHZNYW",
            "MOBGGW7QZ7GHZNYW",
        ),
        (
            "https://www.croma.com/lg-oled-55-inch/p/265748?utm_source=google",
            "croma",
            "https://www.croma.com/p/265748",
            "265748",
        ),
        (
            "https://www.myntra.com/shoes/nike/nike-air-pegasus/24189340/buy",
            "myntra",
            "https://www.myntra.com/24189340",
            "24189340",
        ),
    ],
)
def test_source_resolution(url, expected_source, expected_canonical, expected_id):
    """Test URL resolves to correct source, canonical URL, and external ID."""
    source, canonical, ext_id = default_registry.resolve(url)
    assert source.name == expected_source
    assert canonical == expected_canonical
    assert ext_id == expected_id


def test_unsupported_url_raises_error():
    """An unrecognised retailer domain must raise UnsupportedPlatformError."""
    with pytest.raises(UnsupportedPlatformError):
        default_registry.get_source("https://www.ebay.com/itm/123456789")
