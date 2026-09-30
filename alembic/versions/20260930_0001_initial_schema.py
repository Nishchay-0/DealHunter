"""initial schema — all DealHunter tables

Revision ID: 0001
Revises:
Create Date: 2026-09-30
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # -----------------------------------------------------------------
    # sources — no FK dependencies, created first
    # -----------------------------------------------------------------
    op.create_table(
        "sources",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(50), nullable=False, unique=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("last_success_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("error_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("rate_limit_per_min", sa.Integer(), nullable=False, server_default="10"),
    )

    # -----------------------------------------------------------------
    # users
    # -----------------------------------------------------------------
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("telegram_id", sa.BigInteger(), nullable=True, unique=True),
        sa.Column("whatsapp_id", sa.String(20), nullable=True, unique=True),
        sa.Column("username", sa.String(255), nullable=True),
        sa.Column("timezone", sa.String(64), nullable=False, server_default="Asia/Kolkata"),
        sa.Column("quiet_hours_start", sa.Time(), nullable=True),
        sa.Column("quiet_hours_end", sa.Time(), nullable=True),
        sa.Column("digest_mode", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("daily_alert_cap", sa.Integer(), nullable=False, server_default="20"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_users_telegram_id", "users", ["telegram_id"])
    op.create_index("ix_users_whatsapp_id", "users", ["whatsapp_id"])

    # -----------------------------------------------------------------
    # products
    # -----------------------------------------------------------------
    op.create_table(
        "products",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("canonical_url", sa.Text(), nullable=False, unique=True),
        sa.Column("platform", sa.String(50), nullable=False),
        sa.Column("external_id", sa.String(255), nullable=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("brand", sa.String(255), nullable=True),
        sa.Column("category", sa.String(255), nullable=True),
        sa.Column("image_url", sa.Text(), nullable=True),
        sa.Column("list_price", sa.Numeric(12, 2), nullable=True),
        sa.Column("currency", sa.String(10), nullable=False, server_default="INR"),
        sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("observation_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("confidence", sa.String(20), nullable=False, server_default="low"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    # -----------------------------------------------------------------
    # price_history
    # -----------------------------------------------------------------
    op.create_table(
        "price_history",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "product_id",
            sa.Integer(),
            sa.ForeignKey("products.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("listed_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("effective_price", sa.Numeric(12, 2), nullable=True),
        sa.Column("coupon", sa.Numeric(12, 2), nullable=True),
        sa.Column("bank_offer", sa.Numeric(12, 2), nullable=True),
        sa.Column("exchange_offer", sa.Numeric(12, 2), nullable=True),
        sa.Column("cashback", sa.Numeric(12, 2), nullable=True),
        sa.Column("in_stock", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("seller", sa.String(255), nullable=True),
        sa.Column("seller_rating", sa.Float(), nullable=True),
        sa.Column("source", sa.String(50), nullable=False),
        sa.Column(
            "observed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index(
        "ix_price_history_product_observed",
        "price_history",
        ["product_id", "observed_at"],
    )

    # -----------------------------------------------------------------
    # watchlist
    # -----------------------------------------------------------------
    op.create_table(
        "watchlist",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "product_id",
            sa.Integer(),
            sa.ForeignKey("products.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("target_price", sa.Numeric(12, 2), nullable=True),
        sa.Column("drop_threshold_pct", sa.Float(), nullable=False, server_default="5.0"),
        sa.Column("alert_mode", sa.String(20), nullable=False, server_default="instant"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("user_id", "product_id", name="uq_watchlist_user_product"),
    )

    # -----------------------------------------------------------------
    # alerts_sent
    # -----------------------------------------------------------------
    op.create_table(
        "alerts_sent",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "product_id",
            sa.Integer(),
            sa.ForeignKey("products.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("rule", sa.String(50), nullable=False),
        sa.Column("deal_score", sa.Float(), nullable=True),
        sa.Column("channel", sa.String(20), nullable=False),
        sa.Column(
            "sent_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("payload_json", sa.JSON(), nullable=True),
    )
    op.create_index(
        "ix_alerts_sent_user_product_sent",
        "alerts_sent",
        ["user_id", "product_id", "sent_at"],
    )

    # -----------------------------------------------------------------
    # offers
    # -----------------------------------------------------------------
    op.create_table(
        "offers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "product_id",
            sa.Integer(),
            sa.ForeignKey("products.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("type", sa.String(20), nullable=False),
        sa.Column("value", sa.Numeric(12, 2), nullable=False),
        sa.Column("condition_text", sa.Text(), nullable=True),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=True),
        sa.Column("valid_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source", sa.String(50), nullable=False),
    )

    # -----------------------------------------------------------------
    # audit_log
    # -----------------------------------------------------------------
    op.create_table(
        "audit_log",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("actor", sa.String(255), nullable=True),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("entity", sa.String(100), nullable=False),
        sa.Column("entity_id", sa.Integer(), nullable=True),
        sa.Column("meta_json", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )


def downgrade() -> None:
    op.drop_table("audit_log")
    op.drop_table("offers")
    op.drop_index("ix_alerts_sent_user_product_sent", table_name="alerts_sent")
    op.drop_table("alerts_sent")
    op.drop_table("watchlist")
    op.drop_index("ix_price_history_product_observed", table_name="price_history")
    op.drop_table("price_history")
    op.drop_table("products")
    op.drop_index("ix_users_whatsapp_id", table_name="users")
    op.drop_index("ix_users_telegram_id", table_name="users")
    op.drop_table("users")
    op.drop_table("sources")
