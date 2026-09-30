"""
database/models.py
SQLAlchemy 2.0 ORM models for every DealHunter table.

Tables (in dependency order):
  sources, users, products, price_history,
  watchlist, alerts_sent, offers, audit_log

Adding a new table: create a class here, then run:
  alembic revision --autogenerate -m "describe change"
  alembic upgrade head
"""

from __future__ import annotations

from datetime import datetime, time
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
    Time,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.base import Base


# ---------------------------------------------------------------------------
# sources
# ---------------------------------------------------------------------------

class Source(Base):
    """
    Represents a price-data source (Amazon, Flipkart, Croma, …).
    Each scraper/API adapter has one row here so the admin can
    enable/disable it and monitor its health.
    """

    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_success_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    rate_limit_per_min: Mapped[int] = mapped_column(Integer, default=10, nullable=False)

    def __repr__(self) -> str:
        return f"<Source name={self.name!r} enabled={self.enabled}>"


# ---------------------------------------------------------------------------
# users
# ---------------------------------------------------------------------------

class User(Base):
    """
    A DealHunter user.
    telegram_id and whatsapp_id are both nullable so a user can exist
    on either or both channels without schema changes.
    """

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, unique=True, nullable=True, index=True
    )
    whatsapp_id: Mapped[Optional[str]] = mapped_column(
        String(20), unique=True, nullable=True, index=True
    )
    username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Notification preferences
    timezone: Mapped[str] = mapped_column(
        String(64), default="Asia/Kolkata", nullable=False
    )
    quiet_hours_start: Mapped[Optional[time]] = mapped_column(Time, nullable=True)
    quiet_hours_end: Mapped[Optional[time]] = mapped_column(Time, nullable=True)
    digest_mode: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    daily_alert_cap: Mapped[int] = mapped_column(Integer, default=20, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    watchlist_items: Mapped[list["Watchlist"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    alerts_sent: Mapped[list["AlertSent"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} telegram_id={self.telegram_id}>"


# ---------------------------------------------------------------------------
# products
# ---------------------------------------------------------------------------

class Product(Base):
    """
    A product that DealHunter tracks.
    canonical_url is the stable, normalised URL used as a dedup key.
    """

    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    canonical_url: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    platform: Mapped[str] = mapped_column(String(50), nullable=False)  # amazon, flipkart, …
    external_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    name: Mapped[str] = mapped_column(Text, nullable=False)
    brand: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    category: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    image_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    list_price: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(12, 2), nullable=True
    )
    currency: Mapped[str] = mapped_column(String(10), default="INR", nullable=False)

    last_checked_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # observation_count and confidence drive the low-confidence suppression rule
    observation_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    confidence: Mapped[str] = mapped_column(
        String(20), default="low", nullable=False
    )  # low | medium | high

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    price_history: Mapped[list["PriceHistory"]] = relationship(
        back_populates="product", cascade="all, delete-orphan"
    )
    watchlist_items: Mapped[list["Watchlist"]] = relationship(
        back_populates="product", cascade="all, delete-orphan"
    )
    alerts_sent: Mapped[list["AlertSent"]] = relationship(
        back_populates="product", cascade="all, delete-orphan"
    )
    offers: Mapped[list["Offer"]] = relationship(
        back_populates="product", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Product id={self.id} platform={self.platform!r} name={self.name!r}>"


# ---------------------------------------------------------------------------
# price_history
# ---------------------------------------------------------------------------

class PriceHistory(Base):
    """
    One price observation for a product.
    Stores both the listed (MRP/sale) price and the effective price
    after all stackable offers, so the deal engine never has to re-compute
    from raw offers on read.

    Index on (product_id, observed_at DESC) is critical for history queries.
    """

    __tablename__ = "price_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), nullable=False
    )

    listed_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    effective_price: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(12, 2), nullable=True
    )

    # Offer breakdown stored per-observation for full auditability
    coupon: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), nullable=True)
    bank_offer: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), nullable=True)
    exchange_offer: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(12, 2), nullable=True
    )
    cashback: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), nullable=True)

    in_stock: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    seller: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    seller_rating: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    source: Mapped[str] = mapped_column(String(50), nullable=False)

    observed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationship
    product: Mapped["Product"] = relationship(back_populates="price_history")

    __table_args__ = (
        # Drives all "last N days" history queries efficiently
        Index("ix_price_history_product_observed", "product_id", "observed_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<PriceHistory product_id={self.product_id} "
            f"listed={self.listed_price} at={self.observed_at}>"
        )


# ---------------------------------------------------------------------------
# watchlist
# ---------------------------------------------------------------------------

class Watchlist(Base):
    """
    A user's tracked product with their personal alert configuration.
    UNIQUE(user_id, product_id) prevents duplicate tracking rows.
    """

    __tablename__ = "watchlist"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), nullable=False
    )

    target_price: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(12, 2), nullable=True
    )
    drop_threshold_pct: Mapped[float] = mapped_column(
        Float, default=5.0, nullable=False
    )
    alert_mode: Mapped[str] = mapped_column(
        String(20), default="instant", nullable=False
    )  # instant | digest | off

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    user: Mapped["User"] = relationship(back_populates="watchlist_items")
    product: Mapped["Product"] = relationship(back_populates="watchlist_items")

    __table_args__ = (
        UniqueConstraint("user_id", "product_id", name="uq_watchlist_user_product"),
    )

    def __repr__(self) -> str:
        return (
            f"<Watchlist user_id={self.user_id} "
            f"product_id={self.product_id} mode={self.alert_mode!r}>"
        )


# ---------------------------------------------------------------------------
# alerts_sent
# ---------------------------------------------------------------------------

class AlertSent(Base):
    """
    Audit log for every outbound alert.
    Used to enforce cooldowns: query MAX(sent_at) WHERE user+product.
    Index on (user_id, product_id, sent_at DESC) powers cooldown checks.
    """

    __tablename__ = "alerts_sent"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), nullable=False
    )

    rule: Mapped[str] = mapped_column(String(50), nullable=False)
    # e.g. TARGET_HIT, PRICE_DROP, ALL_TIME_LOW, STRONG_DEAL, BIG_DEAL, COUPON_ALERT
    deal_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    channel: Mapped[str] = mapped_column(String(20), nullable=False)  # telegram | whatsapp
    sent_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    payload_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="alerts_sent")
    product: Mapped["Product"] = relationship(back_populates="alerts_sent")

    __table_args__ = (
        Index("ix_alerts_sent_user_product_sent", "user_id", "product_id", "sent_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<AlertSent user_id={self.user_id} "
            f"product_id={self.product_id} rule={self.rule!r}>"
        )


# ---------------------------------------------------------------------------
# offers
# ---------------------------------------------------------------------------

class Offer(Base):
    """
    A discrete offer attached to a product.
    Each offer has a type, a monetary value, and the plain-text condition
    so the deal engine can surface it to users accurately.
    """

    __tablename__ = "offers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), nullable=False
    )

    type: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # coupon | bank | exchange | cashback
    value: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    condition_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    valid_from: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    valid_to: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    source: Mapped[str] = mapped_column(String(50), nullable=False)

    # Relationship
    product: Mapped["Product"] = relationship(back_populates="offers")

    def __repr__(self) -> str:
        return (
            f"<Offer product_id={self.product_id} "
            f"type={self.type!r} value={self.value}>"
        )


# ---------------------------------------------------------------------------
# audit_log
# ---------------------------------------------------------------------------

class AuditLog(Base):
    """
    Immutable append-only audit log.
    Captures every significant action (admin mutations, user data deletion
    requests, source enable/disable) for accountability.
    Never contains secrets, tokens, or personal identifiers in plain text.
    """

    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    actor: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    entity: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    meta_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return (
            f"<AuditLog actor={self.actor!r} "
            f"action={self.action!r} entity={self.entity!r}>"
        )
