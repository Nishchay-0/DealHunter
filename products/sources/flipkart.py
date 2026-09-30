"""
products/sources/flipkart.py
Flipkart India price source adapter.

Access method: public_page_read (HTML Open Graph, JSON-LD, and structured product attributes).
Why permitted: Reads public schema markup for product identity and price; throttled and rate-limited.
"""

from __future__ import annotations

import html
import json
import logging
import re
from decimal import Decimal
from urllib.parse import parse_qs, urlparse

from products.models import PriceObservation, ProductData
from products.sources.base import PriceSource

logger = logging.getLogger(__name__)

PID_PARAM_PATTERN = re.compile(r"pid=([A-Z0-9]+)", re.IGNORECASE)
ITM_PATTERN = re.compile(r"/p/(itm[a-zA-Z0-9]+)", re.IGNORECASE)


class FlipkartSource(PriceSource):
    """Flipkart (flipkart.com) product source adapter."""

    name: str = "flipkart"
    access_method: str = "public_page_read"
    access_permission_rationale: str = (
        "Publicly readable Open Graph and JSON-LD schema tags, throttled and rate-limited."
    )
    rate_limit_per_min: int = 10

    def matches(self, url: str) -> bool:
        """Check if URL belongs to Flipkart."""
        return "flipkart.com" in url.lower() or "fkrt.it" in url.lower()

    def extract_external_id(self, url: str) -> str | None:
        """Extract Flipkart PID or Item ID from URL."""
        parsed = urlparse(url)
        query = parse_qs(parsed.query)
        if "pid" in query and query["pid"]:
            return query["pid"][0].strip()

        pid_match = PID_PARAM_PATTERN.search(url)
        if pid_match:
            return pid_match.group(1).strip()

        itm_match = ITM_PATTERN.search(url)
        if itm_match:
            return itm_match.group(1).strip()

        return None

    def canonicalize_url(self, url: str) -> str:
        """Return standardized Flipkart canonical product URL."""
        pid = self.extract_external_id(url)
        if pid:
            return f"https://www.flipkart.com/p/item?pid={pid}"
        return url.split("?")[0].rstrip("/")

    def parse_html(self, html_content: str, url: str) -> tuple[ProductData, PriceObservation]:
        """Parse Flipkart product page HTML."""
        pid = self.extract_external_id(url) or "UNKNOWN"

        # 1. Title Extraction
        title = "Flipkart Product"
        title_match = re.search(r'<meta\s+property=["\']og:title["\']\s+content=["\']([^"\']+)["\']', html_content, re.IGNORECASE)
        if not title_match:
            title_match = re.search(r'<title>(.*?)</title>', html_content, re.IGNORECASE | re.DOTALL)
        if title_match:
            cleaned = html.unescape(title_match.group(1)).strip()
            # Clean common Flipkart suffixes
            cleaned = re.sub(r"\s*\|\s*Flipkart\.com.*$", "", cleaned, flags=re.IGNORECASE)
            title = cleaned[:255] if cleaned else title

        # 2. Image Extraction
        image_url = None
        img_match = re.search(r'<meta\s+property=["\']og:image["\']\s+content=["\']([^"\']+)["\']', html_content, re.IGNORECASE)
        if img_match:
            image_url = html.unescape(img_match.group(1)).strip()

        # 3. Price Extraction
        price = Decimal("0.00")
        price_found = False

        # Try JSON-LD
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

        # Fallback to currency pattern (e.g. ₹24,999)
        if not price_found:
            price_match = re.search(r'₹\s*([0-9,]+)', html_content)
            if price_match:
                clean_num = price_match.group(1).replace(",", "").strip()
                price = Decimal(clean_num)
                price_found = True

        # 4. Bank / Special Offers
        bank_offer: Decimal | None = None
        raw_offers: list[str] = []
        bank_match = re.search(r'Bank Offer.*?(?:₹|Rs\.?)\s*([0-9,]+)', html_content, re.IGNORECASE)
        if bank_match:
            val = Decimal(bank_match.group(1).replace(",", "").strip())
            bank_offer = val
            raw_offers.append(f"Bank Offer: ₹{val}")

        in_stock = "out of stock" not in html_content.lower() and "sold out" not in html_content.lower()

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
            bank_offer=bank_offer,
            raw_offer_text=" | ".join(raw_offers) if raw_offers else None,
        )

        return product_data, observation
