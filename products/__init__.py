"""
products package for DealHunter.
Handles retailer platform parsing, price observation extraction, and product tracking.
"""

from products.models import PriceObservation, ProductData
from products.service import ProductTrackingService

__all__ = [
    "ProductData",
    "PriceObservation",
    "ProductTrackingService",
]
