"""
products/sources/amazon.py
Amazon India price source adapter.

Access method: public_page_read (HTML Open Graph, JSON-LD, and microdata).
Why permitted: Publicly accessible catalog pages parsed at low frequency with polite headers and rate limits.
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

ASIN_PATTERN = re.compile(r"(?:/dp/|/gp/product/|/gp/aw/d/|/d/)([A-Z0-9]{10})", re.IGNORECASE)


class AmazonSource(PriceSource):
    """Amazon India (amazon.in) product source adapter."""

    name: str = "amazon"
    access_method: str = "public_page_read"
    access_permission_rationale: str = (
        "Publicly readable metadata and Open Graph tags, rate-limited and throttled."
    )
    rate_limit_per_min: int = 12

    def matches(self, url: str) -> bool:
        """Check if URL belongs to Amazon India."""
        return "amazon.in" in url.lower() or "amzn.to" in url.lower() or "amzn.in" in url.lower()

    def extract_external_id(self, url: str) -> str | None:
        """Extract 10-character Amazon ASIN from URL."""
        match = ASIN_PATTERN.search(url)
        return match.group(1).upper() if match else None

    def canonicalize_url(self, url: str) -> str:
        """Return standardized Amazon India URL using the ASIN."""
        asin = self.extract_external_id(url)
        if asin:
            return f"https://www.amazon.in/dp/{asin}"
        return url.split("?")[0].rstrip("/")

    def parse_html(self, html_content: str, url: str) -> tuple[ProductData, PriceObservation]:
        """Parse Amazon product page HTML for title, price, and offers."""
        asin = self.extract_external_id(url) or "UNKNOWN"

        # 1. Title Extraction
        title = "Amazon Product"
        title_match = re.search(r'<meta\s+property=["\']og:title["\']\s+content=["\']([^"\']+)["\']', html_content, re.IGNORECASE)
        if not title_match:
            title_match = re.search(r'<title>(.*?)</title>', html_content, re.IGNORECASE | re.DOTALL)
        if not title_match:
            title_match = re.search(r'id=["\']productTitle["\'][^>]*>(.*?)</span>', html_content, re.IGNORECASE | re.DOTALL)
        if title_match:
            cleaned = html.unescape(title_match.group(1)).strip()
            # Clean common Amazon suffixes
            cleaned = re.sub(r"\s*:\s*Amazon\.in.*$", "", cleaned, flags=re.IGNORECASE)
            title = cleaned[:255] if cleaned else title

        # 2. Image Extraction
        image_url = None
        img_match = re.search(r'<meta\s+property=["\']og:image["\']\s+content=["\']([^"\']+)["\']', html_content, re.IGNORECASE)
        if img_match:
            image_url = html.unescape(img_match.group(1)).strip()

        # 3. Price Extraction
        price = Decimal("0.00")
        price_found = False

        # Try JSON-LD first
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
                    elif isinstance(offers, list) and offers and "price" in offers[0]:
                        price = Decimal(str(offers[0]["price"]))
                        price_found = True
                        break
            except Exception:
                continue

        # Fallback to microdata / CSS classes
        if not price_found:
            price_match = re.search(r'class=["\']a-price-whole["\'][^>]*>([0-9,]+)', html_content)
            if price_match:
                clean_num = price_match.group(1).replace(",", "").strip()
                price = Decimal(clean_num)
                price_found = True

        if not price_found:
            og_price = re.search(r'<meta\s+property=["\']og:price:amount["\']\s+content=["\']([0-9.,]+)["\']', html_content)
            if og_price:
                price = Decimal(og_price.group(1).replace(",", "").strip())
                price_found = True

        # 4. Stock & Seller
        in_stock = "currently unavailable" not in html_content.lower() and "out of stock" not in html_content.lower()
        seller = None
        seller_match = re.search(r'id=["\']merchant-info["\'][^>]*>(.*?)</div>', html_content, re.IGNORECASE | re.DOTALL)
        if seller_match:
            seller_text = re.sub(r"<[^>]+>", " ", seller_match.group(1))
            seller = html.unescape(seller_text).strip()[:100]

        # 5. Coupon / Offers
        coupon: Decimal | None = None
        coupon_match = re.search(r'Apply\s*₹?\s*([0-9,]+)\s*coupon', html_content, re.IGNORECASE)
        if coupon_match:
            coupon = Decimal(coupon_match.group(1).replace(",", "").strip())

        product_data = ProductData(
            canonical_url=self.canonicalize_url(url),
            platform=self.name,
            external_id=asin,
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
            seller=seller,
            coupon=coupon,
            raw_offer_text=f"Coupon: ₹{coupon}" if coupon else None,
        )

        return product_data, observation
