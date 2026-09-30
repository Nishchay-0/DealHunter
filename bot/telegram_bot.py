"""
DealHunter - Telegram Bot
Step 1: Project Foundation

This is the entry point for the DealHunter Telegram bot.
Future steps will add database, product tracking, price monitoring,
deal discovery, notifications, and more.
"""

import logging
import os
import sys

from dotenv import load_dotenv
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
# Command Handlers
# ---------------------------------------------------------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/start - Send a professional welcome message."""
    welcome_message = (
        "Welcome to DealHunter!\n\n"
        "Your personal deal & price-drop assistant.\n\n"
        "I can help you:\n"
        "- Track product prices\n"
        "- Detect price drops\n"
        "- Set target prices\n"
        "- Monitor deals\n"
        "- Get alerts when prices change\n\n"
        "Deal tracking is currently being built.\n\n"
        "Use /help to see available commands."
    )
    await update.message.reply_text(welcome_message)
    logger.info("User %s triggered /start", update.effective_user.id)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/help - Show available and upcoming commands."""
    help_message = (
        "DealHunter Help\n\n"
        "Available commands:\n"
        "/start - Start DealHunter\n"
        "/help - Show this help message\n\n"
        "Coming soon:\n"
        "/track - Track a product\n"
        "/watchlist - View tracked products\n"
        "/deals - Find deals\n"
        "/target - Set a target price\n"
        "/remove - Remove a product\n\n"
        "More features will be added step by step."
    )
    await update.message.reply_text(help_message)
    logger.info("User %s triggered /help", update.effective_user.id)


async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle any command that DealHunter does not recognise yet."""
    response = (
        "I don't recognise that command yet.\n\n"
        "Use /help to see what DealHunter currently supports."
    )
    await update.message.reply_text(response)
    logger.info(
        "User %s sent an unknown command: %s",
        update.effective_user.id,
        update.message.text,
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

    # Catch-all handler for any unrecognised command (must be registered last)
    app.add_handler(MessageHandler(filters.COMMAND, unknown_command))

    # Global error handler
    app.add_error_handler(error_handler)

    print("DealHunter is running...")
    logger.info("DealHunter bot started. Polling for updates.")

    # Start polling - blocks until the process is interrupted (Ctrl+C)
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
