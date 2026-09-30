"""
watchlist package for DealHunter.
"""

from watchlist.categories import infer_category
from watchlist.service import WatchlistService

__all__ = ["WatchlistService", "infer_category"]
