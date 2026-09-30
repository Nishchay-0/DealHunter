"""
products/sources/registry.py
Central registry for resolving URLs to their corresponding PriceSource adapters.
"""

from __future__ import annotations

import logging
from typing import Sequence

from products.sources.amazon import AmazonSource
from products.sources.base import PriceSource
from products.sources.croma import CromaSource
from products.sources.flipkart import FlipkartSource
from products.sources.myntra import MyntraSource

logger = logging.getLogger(__name__)


class UnsupportedPlatformError(ValueError):
    """Raised when an incoming URL does not match any registered PriceSource."""


class SourceRegistry:
    """Registry managing available retailer price sources."""

    def __init__(self, sources: Sequence[PriceSource] | None = None) -> None:
        if sources is None:
            self._sources: list[PriceSource] = [
                AmazonSource(),
                FlipkartSource(),
                CromaSource(),
                MyntraSource(),
            ]
        else:
            self._sources = list(sources)

    def register(self, source: PriceSource) -> None:
        """Register a new source adapter."""
        self._sources.append(source)

    def list_sources(self) -> list[PriceSource]:
        """Return all registered source adapters."""
        return list(self._sources)

    def get_source_by_name(self, name: str) -> PriceSource | None:
        """Retrieve source adapter by name (e.g. 'amazon', 'flipkart')."""
        for src in self._sources:
            if src.name.lower() == name.lower():
                return src
        return None

    def get_source(self, url: str) -> PriceSource:
        """Find the matching PriceSource for a given URL, or raise UnsupportedPlatformError."""
        for src in self._sources:
            if src.matches(url):
                return src
        raise UnsupportedPlatformError(
            f"No supported retailer source found for URL: {url}"
        )

    def resolve(self, url: str) -> tuple[PriceSource, str, str | None]:
        """
        Resolve a URL to its (source_adapter, canonical_url, external_id).
        """
        source = self.get_source(url)
        canonical = source.canonicalize_url(url)
        ext_id = source.extract_external_id(url)
        return source, canonical, ext_id


# Default global registry instance
default_registry = SourceRegistry()
