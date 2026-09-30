"""
products.sources package.
Exposes base class, registry, and concrete price sources.
"""

from products.sources.amazon import AmazonSource
from products.sources.base import PriceSource
from products.sources.croma import CromaSource
from products.sources.flipkart import FlipkartSource
from products.sources.myntra import MyntraSource
from products.sources.registry import (
    SourceRegistry,
    UnsupportedPlatformError,
    default_registry,
)

__all__ = [
    "PriceSource",
    "AmazonSource",
    "FlipkartSource",
    "CromaSource",
    "MyntraSource",
    "SourceRegistry",
    "UnsupportedPlatformError",
    "default_registry",
]
