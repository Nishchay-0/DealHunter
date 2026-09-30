"""
products/sources/base.py
Abstract Base Class defining the PriceSource interface.

Every retailer adapter inherits from PriceSource and declares:
- name: Unique retailer identifier
- access_method: 'official_api' | 'affiliate_api' | 'public_page_read'
- access_permission_rationale: Explicit declaration of why access is permitted
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any
import httpx

from products.models import PriceObservation, ProductData

logger = logging.getLogger(__name__)


class PriceSource(ABC):
    """
    Abstract Base Class for retailer price source adapters.
    Guarantees isolation: adding or modifying a source touches only this module.
    """

    name: str
    access_method: str  # "official_api" | "affiliate_api" | "public_page_read"
    access_permission_rationale: str
    enabled_by_default: bool = True
    rate_limit_per_min: int = 10
    timeout_seconds: float = 15.0

    @abstractmethod
    def matches(self, url: str) -> bool:
        """Return True if this source adapter handles the given URL."""
        raise NotImplementedError

    @abstractmethod
    def extract_external_id(self, url: str) -> str | None:
        """Extract the unique platform identifier (e.g. ASIN, PID, SKU) from URL."""
        raise NotImplementedError

    @abstractmethod
    def canonicalize_url(self, url: str) -> str:
        """Strip tracking query parameters and return a clean canonical product URL."""
        raise NotImplementedError

    @abstractmethod
    def parse_html(self, html_content: str, url: str) -> tuple[ProductData, PriceObservation]:
        """Parse raw HTML / structured markup into ProductData and PriceObservation."""
        raise NotImplementedError

    async def fetch_page(self, url: str, headers: dict[str, str] | None = None) -> str:
        """Fetch URL content via httpx with default bot headers and respectful timeout."""
        default_headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36 DealHunterBot/1.0"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }
        if headers:
            default_headers.update(headers)

        async with httpx.AsyncClient(
            headers=default_headers,
            timeout=self.timeout_seconds,
            follow_redirects=True,
        ) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            return resp.text

    async def get_product(self, url: str) -> ProductData:
        """Fetch and extract Product metadata for the given URL."""
        try:
            html = await self.fetch_page(url)
            product, _ = self.parse_html(html, url)
            return product
        except Exception as exc:
            logger.error("[%s] get_product failed for %s: %s", self.name, url, exc)
            raise

    async def get_price(self, url: str) -> PriceObservation:
        """Fetch and extract latest PriceObservation for the given URL."""
        try:
            html = await self.fetch_page(url)
            _, observation = self.parse_html(html, url)
            return observation
        except Exception as exc:
            logger.error("[%s] get_price failed for %s: %s", self.name, url, exc)
            raise
