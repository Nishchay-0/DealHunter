"""
database/__init__.py
Database package for DealHunter.
Exports Base, session functions, and all ORM models.
"""

from database.base import Base
from database.models import (
    AlertSent,
    AuditLog,
    Offer,
    PriceHistory,
    Product,
    Source,
    User,
    Watchlist,
)
from database.session import (
    get_db,
    get_engine,
    get_session_factory,
    normalize_database_url,
    reset_engine,
)

__all__ = [
    "Base",
    "User",
    "Product",
    "PriceHistory",
    "Watchlist",
    "AlertSent",
    "Offer",
    "Source",
    "AuditLog",
    "get_engine",
    "get_session_factory",
    "get_db",
    "normalize_database_url",
    "reset_engine",
]
