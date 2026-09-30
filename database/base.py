"""
database/base.py
Shared SQLAlchemy declarative base.
All models import from here so Alembic can discover them in one place.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Root base class for every ORM model in DealHunter."""
    pass
