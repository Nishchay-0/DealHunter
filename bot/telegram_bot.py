"""
DealHunter - Telegram Bot
Phase 5: Watchlist, Target Prices & Deals Integration

Features:
- /start - Welcome & onboarding
- /help - Full command guide
- /track <url> - Track product from Amazon, Flipkart, Croma, or Myntra
- /watchlist - View all tracked products
- /target <product_id> <price> - Set target price
- /deals [category] - Discover active price drops
- /remove <product_id> - Untrack a product
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
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger(__name__)
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
        "💡 *Key Commands:*\n"
        "• Send any product URL to track it instantly!\n"
        "• `/watchlist` — View your tracked items\n"
        "• `/target <id> <price>` — Set target price\n"
        "• `/deals` — Discover top price drops\n\n"
        "Type /help for full guide."
    )
    if update.message:
        await update.message.reply_text(welcome_message, parse_mode="Markdown")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/help - Show available commands."""
    help_message = (
        "📖 *DealHunter Commands*\n\n"
        "• `/start` — Welcome & onboarding\n"
        "• `/help` — Show command guide\n"
        "• `/track <url>` — Track a product price\n"
        "• `/watchlist` — View all your tracked products\n"
        "• `/target <product_id> <price>` — Set target price threshold\n"
        "• `/deals [category]` — Discover top price drops\n"
        "• `/remove <product_id>` — Untrack a product\n\n"
        "Tip: Send any product URL directly into chat to track it!"
    )
    if update.message:
        await update.message.reply_text(help_message, parse_mode="Markdown")


async def track_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/track <url> - Parse and track product from URL."""
    if not update.message:
        return

    text = update.message.text or ""
    urls = URL_REGEX.findall(text)
    if not urls:
        await update.message.reply_text(
            "⚠️ Please provide a product URL to track.\n\n"
            "Example: `/track https://www.amazon.in/dp/B0CHX1W1XY`",
            parse_mode="Markdown",
        )
        return

    await process_url_tracking(update, urls[0])


async def watchlist_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/watchlist - Display user's tracked products."""
    if not update.message or not update.effective_user:
        return

    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        await update.message.reply_text("⚠️ Database is not configured for persistent watchlists.")
        return

    user_id = await ensure_db_user(update.effective_user.id, update.effective_user.username)
    if not user_id:
        await update.message.reply_text("⚠️ Could not load your watchlist right now.")
        return

    from database.session import get_session_factory
    from watchlist.service import WatchlistService

    svc = WatchlistService()
    factory = get_session_factory()
    async with factory() as session:
        items = await svc.get_user_watchlist(session, user_id)

    if not items:
        await update.message.reply_text(
            "📋 *Your Watchlist is Empty*\n\n"
            "Track your first product by pasting a link or using `/track <url>`!",
            parse_mode="Markdown",
        )
        return

    lines = ["📋 *Your Tracked Watchlist:*\n"]
    for idx, item in enumerate(items, start=1):
        target_str = f"₹{item['target_price']:,.2f}" if item['target_price'] else "Not set"
        lines.append(
            f"*{idx}. {item['name']}*\n"
            f"   • ID: `{item['product_id']}` | Store: {item['platform'].capitalize()}\n"
            f"   • Price: ₹{item['current_price']:,.2f} | Target: {target_str}\n"
            f"   • Category: {item['category']}\n"
            f"   └ 🔗 [View Product]({item['canonical_url']})\n"
        )

    lines.append("💡 *Tip:* Use `/target <id> <price>` or `/remove <id>` to manage your watchlist.")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown", disable_web_page_preview=True)


async def target_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/target <product_id> <price> - Set target price for a watched item."""
    if not update.message or not update.effective_user:
        return

    args = context.args or []
    if len(args) < 2:
        await update.message.reply_text(
            "⚠️ Usage: `/target <product_id> <target_price>`\n\n"
            "Example: `/target 1 70000`\n"
            "Find product IDs in your `/watchlist`.",
            parse_mode="Markdown",
        )
        return

    try:
        product_id = int(args[0])
        target_price = Decimal(args[1].replace(",", "").strip())
    except ValueError:
        await update.message.reply_text("⚠️ Product ID must be an integer and target price a valid number.")
        return

    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        await update.message.reply_text("⚠️ Database is not configured.")
        return

    user_id = await ensure_db_user(update.effective_user.id, update.effective_user.username)
    if not user_id:
        await update.message.reply_text("⚠️ Could not load user profile.")
        return

    from database.session import get_session_factory
    from watchlist.service import WatchlistService

    svc = WatchlistService()
    factory = get_session_factory()
    async with factory() as session:
        item = await svc.set_target_price(session, user_id, product_id, target_price)

    if item:
        await update.message.reply_text(
            f"🎯 Target price set to *₹{target_price:,.2f}* for product ID `{product_id}`!\n"
            "You will be alerted instantly when the price hits this threshold.",
            parse_mode="Markdown",
        )
    else:
        await update.message.reply_text(f"⚠️ Product ID `{product_id}` is not in your watchlist.")


async def deals_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/deals [category] - Discover active top price drops."""
    if not update.message:
        return

    category_filter = " ".join(context.args).strip() if context.args else None

    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        await update.message.reply_text("⚠️ Database is not configured for deal discovery.")
        return

    from database.session import get_session_factory
    from deals.service import DealsService

    svc = DealsService()
    factory = get_session_factory()
    async with factory() as session:
        top_deals = await svc.get_top_deals(session, category=category_filter, min_drop_pct=3.0, limit=8)

    if not top_deals:
        msg = f"🔥 *No Active Deals Found*"
        if category_filter:
            msg += f" for category `{category_filter}`"
        msg += "\n\nKeep tracking more products with `/track <url>` to discover price drops!"
        await update.message.reply_text(msg, parse_mode="Markdown")
        return

    lines = ["🔥 *Top Price Drops & Deals:*\n"]
    for idx, d in enumerate(top_deals, start=1):
        lines.append(
            f"*{idx}. {d['name']}*\n"
            f"   • Store: {d['platform'].capitalize()} | Category: {d['category']}\n"
            f"   • Price: ₹{d['current_price']:,.2f} *(Save ₹{d['drop_amount']:,.2f} / -{d['drop_pct']:.1f}%)*\n"
            f"   └ 🔗 [View Deal]({d['canonical_url']})\n"
        )

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown", disable_web_page_preview=True)


async def remove_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/remove <product_id> - Untrack a product."""
    if not update.message or not update.effective_user:
        return

    args = context.args or []
    if not args:
        await update.message.reply_text(
            "⚠️ Usage: `/remove <product_id>`\n\n"
            "Example: `/remove 1`\n"
            "Find product IDs in your `/watchlist`.",
            parse_mode="Markdown",
        )
        return

    try:
        product_id = int(args[0])
    except ValueError:
        await update.message.reply_text("⚠️ Product ID must be an integer.")
        return

    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        await update.message.reply_text("⚠️ Database is not configured.")
        return

    user_id = await ensure_db_user(update.effective_user.id, update.effective_user.username)
    if not user_id:
        await update.message.reply_text("⚠️ Could not load user profile.")
        return

    from database.session import get_session_factory
    from watchlist.service import WatchlistService

    svc = WatchlistService()
    factory = get_session_factory()
    async with factory() as session:
        removed = await svc.remove_from_watchlist(session, user_id, product_id)

    if removed:
        await update.message.reply_text(f"🗑️ Product ID `{product_id}` removed from your watchlist.")
    else:
        await update.message.reply_text(f"⚠️ Product ID `{product_id}` was not found in your watchlist.")


async def message_url_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle text messages containing raw URLs directly."""
    if not update.message or not update.message.text:
        return

    text = update.message.text
    if text.startswith("/"):
        return

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
                prod_id = product.id
        else:
            prod_data, obs = await service.get_or_fetch_observation(source, target_url)
            prod_name = prod_data.name
            platform_name = source.name.capitalize()
            canonical_link = prod_data.canonical_url
            prod_id = "N/A"
            is_new = True

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

        action_title = "🎯 *Product Added to Watchlist!*" if is_new else "🔄 *Price Observation Updated!*"

        card = (
            f"{action_title}\n\n"
            f"📦 *{prod_name}*\n"
            f"🆔 *Product ID:* `{prod_id}`\n"
            f"🏪 *Store:* {platform_name}\n"
            f"💰 *Listed Price:* ₹{obs.price:,.2f}"
            f"{eff_line}"
            f"{discount_block}\n"
            f"📊 *Status:* {stock_badge}\n\n"
            f"💡 *Set Target Price:* `/target {prod_id} <desired_price>`\n"
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
    app.add_handler(CommandHandler("watchlist", watchlist_command))
    app.add_handler(CommandHandler("target", target_command))
    app.add_handler(CommandHandler("deals", deals_command))
    app.add_handler(CommandHandler("remove", remove_command))

    # Handle text messages with links
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_url_handler))

    # Catch-all handler for unknown commands (must be last command handler)
    app.add_handler(MessageHandler(filters.COMMAND, unknown_command))

    # Global error handler
    app.add_error_handler(error_handler)

    print("DealHunter is running with Watchlist & Deals support...")
    logger.info("DealHunter bot started. Polling for updates.")

    # Start polling
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
