"""
products/sources/croma.py
Croma Electronics price source adapter.

Access method: public_page_read (HTML Open Graph and JSON-LD).
Why permitted: Public catalog pages parsed at low frequency with polite headers and rate limits.
"""

from __future__ import annotations

import html
import json
import logging
import re
from decimal import Decimal

from products.models import PriceObservation, ProductData
from products.sources.base import PriceSource

logger = logging.getLogger(__name__)

CROMA_PID_PATTERN = re.compile(r"/p/([0-9]{5,10})", re.IGNORECASE)


class CromaSource(PriceSource):
    """Croma (croma.com) product source adapter."""

    name: str = "croma"
    access_method: str = "public_page_read"
    access_permission_rationale: str = (
        "Publicly readable Open Graph and JSON-LD tags, throttled and rate-limited."
    )
    rate_limit_per_min: int = 10

    def matches(self, url: str) -> bool:
        """Check if URL belongs to Croma."""
        return "croma.com" in url.lower()

    def extract_external_id(self, url: str) -> str | None:
        """Extract Croma numeric product code from URL."""
        match = CROMA_PID_PATTERN.search(url)
        return match.group(1) if match else None

    def canonicalize_url(self, url: str) -> str:
        """Return standardized Croma canonical product URL."""
        pid = self.extract_external_id(url)
        if pid:
            return f"https://www.croma.com/p/{pid}"
        return url.split("?")[0].rstrip("/")

    def parse_html(self, html_content: str, url: str) -> tuple[ProductData, PriceObservation]:
        """Parse Croma product page HTML."""
        pid = self.extract_external_id(url) or "UNKNOWN"

        # 1. Title
        title = "Croma Product"
        title_match = re.search(r'<meta\s+property=["\']og:title["\']\s+content=["\']([^"\']+)["\']', html_content, re.IGNORECASE)
        if not title_match:
            title_match = re.search(r'<title>(.*?)</title>', html_content, re.IGNORECASE | re.DOTALL)
        if title_match:
            cleaned = html.unescape(title_match.group(1)).strip()
            cleaned = re.sub(r"\s*\|\s*Croma.*$", "", cleaned, flags=re.IGNORECASE)
            title = cleaned[:255] if cleaned else title

        # 2. Image
        image_url = None
        img_match = re.search(r'<meta\s+property=["\']og:image["\']\s+content=["\']([^"\']+)["\']', html_content, re.IGNORECASE)
        if img_match:
            image_url = html.unescape(img_match.group(1)).strip()

        # 3. Price
        price = Decimal("0.00")
        price_found = False

        json_ld_matches = re.findall(r'<script\s+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', html_content, re.IGNORECASE | re.DOTALL)
        for block in json_ld_matches:
            try:
                data = json.loads(block)
                if isinstance(data, dict):
                    offers = data.get("offers")
                    if isinstance(offers, dict) and "price" in offers:
                        price = Decimal(str(offers["price"]))
                        price_found = True
                        break
            except Exception:
                continue

        if not price_found:
            price_match = re.search(r'class=["\']amount["\'][^>]*>₹?\s*([0-9,]+)', html_content)
            if price_match:
                price = Decimal(price_match.group(1).replace(",", "").strip())
                price_found = True

        in_stock = "out of stock" not in html_content.lower()

        product_data = ProductData(
            canonical_url=self.canonicalize_url(url),
            platform=self.name,
            external_id=pid,
            name=title,
            image_url=image_url,
            currency="INR",
            list_price=price,
        )

        observation = PriceObservation(
            price=price,
            currency="INR",
            source=self.name,
            in_stock=in_stock,
        )

        return product_data, observation
