"""
DealHunter - Telegram Bot
Step 3: Product Tracking Integration

Features:
- /start - Welcome & user onboarding
- /help - Available commands
- /track <url> - Track product from Amazon, Flipkart, Croma, or Myntra
- Direct link message handling (paste any product URL directly)
"""

from __future__ import annotations

import logging
import os
import re
import sys
from decimal import Decimal

from dotenv import load_dotenv
from sqlalchemy import select
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# ---------------------------------------------------------------------------
# Logging - do NOT log the token or any secret
# ---------------------------------------------------------------------------

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger(__name__)

# Suppress noisy httpx logs from python-telegram-bot internals
logging.getLogger("httpx").setLevel(logging.WARNING)


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

PLACEHOLDER_TOKEN = "YOUR_BOT_TOKEN_HERE"


def validate_config() -> None:
    """Validate required environment variables before starting the bot."""
    if not TOKEN:
        logger.error(
            "TELEGRAM_BOT_TOKEN is missing. "
            "Please set it in your .env file and try again."
        )
        sys.exit(1)

    if TOKEN == PLACEHOLDER_TOKEN:
        logger.error(
            "TELEGRAM_BOT_TOKEN is still set to the placeholder value. "
            "Replace 'YOUR_BOT_TOKEN_HERE' in .env with your real bot token "
            "from @BotFather on Telegram."
        )
        sys.exit(1)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

URL_REGEX = re.compile(r"https?://[^\s]+")


async def ensure_db_user(telegram_id: int, username: str | None = None) -> int | None:
    """Ensure user exists in database if DATABASE_URL is configured."""
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        return None

    try:
        from database.models import User
        from database.session import get_session_factory

        factory = get_session_factory()
        async with factory() as session:
            stmt = select(User).where(User.telegram_id == telegram_id)
            res = await session.execute(stmt)
            user = res.scalars().first()
            if not user:
                user = User(
                    telegram_id=telegram_id,
                    username=username,
                    timezone="Asia/Kolkata",
                )
                session.add(user)
                await session.commit()
            return user.id
    except Exception as exc:
        logger.warning("Could not sync user to DB: %s", exc)
        return None


# ---------------------------------------------------------------------------
# Command Handlers
# ---------------------------------------------------------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/start - Send a professional welcome message and onboard user."""
    tg_user = update.effective_user
    if tg_user:
        await ensure_db_user(tg_user.id, tg_user.username)

    welcome_message = (
        "👋 *Welcome to DealHunter!*\n\n"
        "Your personal deal & price-drop assistant for Indian e-commerce.\n\n"
        "⚡ *Supported Stores:*\n"
        "• Amazon India (`amazon.in`)\n"
        "• Flipkart (`flipkart.com`)\n"
        "• Croma (`croma.com`)\n"
        "• Myntra (`myntra.com`)\n\n"
        "💡 *How to Track:*\n"
        "Simply send or paste a product link, or use:\n"
        "`/track <product_url>`\n\n"
        "Use /help to see all commands."
    )
    if update.message:
        await update.message.reply_text(welcome_message, parse_mode="Markdown")
    logger.info("User %s triggered /start", tg_user.id if tg_user else "unknown")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/help - Show available and upcoming commands."""
    help_message = (
        "📖 *DealHunter Commands*\n\n"
        "*Active:*\n"
        "• `/start` — Start DealHunter & welcome menu\n"
        "• `/help` — Show this help guide\n"
        "• `/track <url>` — Track a product price & offers\n\n"
        "*Coming Soon:*\n"
        "• `/watchlist` — View all your tracked products\n"
        "• `/target <price>` — Set a target price threshold\n"
        "• `/deals` — Explore top scored price drops\n"
        "• `/remove` — Untrack a product\n\n"
        "Tip: You can also just paste a link directly into the chat!"
    )
    if update.message:
        await update.message.reply_text(help_message, parse_mode="Markdown")
    logger.info("User %s triggered /help", update.effective_user.id if update.effective_user else "unknown")


async def track_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/track <url> - Parse and track product from URL."""
    if not update.message:
        return

    text = update.message.text or ""
    # Extract url from args or message body
    urls = URL_REGEX.findall(text)
    if not urls:
        await update.message.reply_text(
            "⚠️ Please provide a product URL to track.\n\n"
            "Example: `/track https://www.amazon.in/dp/B0CHX1W1XY`",
            parse_mode="Markdown",
        )
        return

    target_url = urls[0]
    await process_url_tracking(update, target_url)


async def message_url_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle text messages containing raw URLs directly."""
    if not update.message or not update.message.text:
        return

    text = update.message.text
    if text.startswith("/"):
        return  # handled by command handlers

    urls = URL_REGEX.findall(text)
    if urls:
        await process_url_tracking(update, urls[0])
    else:
        await update.message.reply_text(
            "Send me an Amazon, Flipkart, Croma, or Myntra product link to start tracking it!\n\n"
            "Or type /help for commands."
        )


async def process_url_tracking(update: Update, target_url: str) -> None:
    """Execute product tracking pipeline and return formatted response."""
    if not update.message:
        return

    from products.sources.registry import UnsupportedPlatformError, default_registry
    from products.service import ProductTrackingService

    try:
        source = default_registry.get_source(target_url)
    except UnsupportedPlatformError:
        await update.message.reply_text(
            "❌ *Unsupported Store*\n\n"
            "DealHunter currently supports:\n"
            "• Amazon India (`amazon.in`)\n"
            "• Flipkart (`flipkart.com`)\n"
            "• Croma (`croma.com`)\n"
            "• Myntra (`myntra.com`)",
            parse_mode="Markdown",
        )
        return

    status_msg = await update.message.reply_text("🔍 Fetching product & price details...")

    try:
        service = ProductTrackingService()
        db_url = os.getenv("DATABASE_URL")

        if db_url:
            from database.session import get_session_factory

            user_id = await ensure_db_user(
                update.effective_user.id, update.effective_user.username
            ) if update.effective_user else None

            factory = get_session_factory()
            async with factory() as session:
                product, obs, is_new = await service.track_product(
                    url=target_url,
                    session=session,
                    user_id=user_id,
                )
                prod_name = product.name
                platform_name = product.platform.capitalize()
                canonical_link = product.canonical_url
        else:
            # Standalone extraction without DB
            prod_data, obs = await service.get_or_fetch_observation(source, target_url)
            prod_name = prod_data.name
            platform_name = source.name.capitalize()
            canonical_link = prod_data.canonical_url
            is_new = True

        # Format price response
        stock_badge = "✅ In Stock" if obs.in_stock else "🔴 Currently Out of Stock"
        discount_lines = []
        if obs.coupon:
            discount_lines.append(f"🎟️ *Coupon:* ₹{obs.coupon:,.2f}")
        if obs.bank_offer:
            discount_lines.append(f"💳 *Bank Offer:* ₹{obs.bank_offer:,.2f}")

        discount_block = ("\n" + "\n".join(discount_lines)) if discount_lines else ""
        eff_line = ""
        if obs.effective_price < obs.price:
            eff_line = f"\n🔥 *Effective Price:* ₹{obs.effective_price:,.2f}"

        action_title = "🎯 *Product Added to Tracking!*" if is_new else "🔄 *Price Observation Updated!*"

        card = (
            f"{action_title}\n\n"
            f"📦 *{prod_name}*\n"
            f"🏪 *Store:* {platform_name}\n"
            f"💰 *Listed Price:* ₹{obs.price:,.2f}"
            f"{eff_line}"
            f"{discount_block}\n"
            f"📊 *Status:* {stock_badge}\n\n"
            f"🔗 [View Product on {platform_name}]({canonical_link})"
        )

        await status_msg.edit_text(card, parse_mode="Markdown", disable_web_page_preview=False)
        logger.info("Successfully tracked %s for user %s", target_url, update.effective_user.id if update.effective_user else "unknown")

    except Exception as exc:
        logger.error("Failed to track URL %s: %s", target_url, exc)
        await status_msg.edit_text(
            f"⚠️ Could not extract product details right now.\n"
            f"Reason: {exc}\n\n"
            "Please verify the link or try again in a few moments."
        )


async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle any command that DealHunter does not recognise yet."""
    response = (
        "I don't recognise that command.\n\n"
        "Use /help to see all supported commands."
    )
    if update.message:
        await update.message.reply_text(response)
    logger.info(
        "User %s sent unknown command: %s",
        update.effective_user.id if update.effective_user else "unknown",
        update.message.text if update.message else "unknown",
    )


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log unexpected errors raised by handlers."""
    logger.error("An error occurred while handling an update: %s", context.error)


# ---------------------------------------------------------------------------
# Bot entry point
# ---------------------------------------------------------------------------

def main() -> None:
    """Build and start the DealHunter Telegram bot."""
    validate_config()

    app = Application.builder().token(TOKEN).build()

    # Register command handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("track", track_command))

    # Handle text messages with links
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_url_handler))

    # Catch-all handler for unknown commands (must be last command handler)
    app.add_handler(MessageHandler(filters.COMMAND, unknown_command))

    # Global error handler
    app.add_error_handler(error_handler)

    print("DealHunter is running with Product Tracking...")
    logger.info("DealHunter bot started. Polling for updates.")

    # Start polling
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
