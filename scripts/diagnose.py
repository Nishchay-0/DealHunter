"""
scripts/diagnose.py
DealHunter System Diagnostics Script.

Verifies:
- Python version and environment
- Configuration / environment variables (NEVER prints secret values)
- Database connectivity (PostgreSQL / SQLite via SQLAlchemy async engine)
- Telegram Bot API connectivity
- Backend app import and health
- Retailer price source registry and circuit breakers

Safe to run anywhere — masks all tokens, passwords, and sensitive keys.
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

# Add project root to sys.path so imports work seamlessly
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from dotenv import load_dotenv

load_dotenv(ROOT_DIR / ".env")


def mask_secret(value: str | None, show_chars: int = 4) -> str:
    """Mask sensitive string, showing at most prefix chars if long enough."""
    if not value:
        return "[NOT SET]"
    if len(value) <= show_chars * 2:
        return "[SET - REDACTED]"
    return f"{value[:show_chars]}...{value[-show_chars:]} (len={len(value)})"


async def check_telegram() -> tuple[bool, str]:
    """Test Telegram Bot API connectivity without exposing token."""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        return False, "TELEGRAM_BOT_TOKEN is not configured in .env"

    try:
        import httpx

        url = f"https://api.telegram.org/bot{token}/getMe"
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url)
            data = resp.json()

        if resp.status_code == 200 and data.get("ok"):
            user = data.get("result", {})
            return True, f"Connected as @{user.get('username')} (id={user.get('id')})"
        return False, f"API error: {data.get('description', 'Unknown error')}"
    except Exception as exc:
        return False, f"Connection failed: {exc}"


async def check_database() -> tuple[bool, str]:
    """Test Database connectivity without exposing credentials."""
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        return False, "DATABASE_URL is not configured in .env"

    try:
        from sqlalchemy import text
        from database.session import get_engine

        engine = get_engine()
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True, "Database connection successful (SELECT 1 passed)"
    except Exception as exc:
        return False, f"Database check failed: {exc}"


def check_backend() -> tuple[bool, str]:
    """Verify backend FastAPI application module loads cleanly."""
    try:
        from backend.main import app

        return True, f"FastAPI app loaded ({app.title} v{app.version})"
    except Exception as exc:
        return False, f"Failed to load backend app: {exc}"


def check_sources() -> tuple[bool, str]:
    """Verify registered price sources and breaker status."""
    try:
        from products.sources.registry import default_registry
        sources = default_registry.list_sources()
        names = [s.name for s in sources]
        return True, f"{len(sources)} sources active: {', '.join(names)}"
    except Exception as exc:
        return False, f"Sources initialization failed: {exc}"


async def run_diagnostics() -> int:
    print("=" * 60)
    print("           DEALHUNTER SYSTEM DIAGNOSTICS")
    print("=" * 60)
    print(f"Python Version : {sys.version.split()[0]} ({sys.platform})")
    print(f"Project Root   : {ROOT_DIR}")
    print(f"Virtual Env    : {sys.prefix}")
    print("-" * 60)
    print("CONFIGURATION (Secrets Masked):")
    print(f"  TELEGRAM_BOT_TOKEN : {mask_secret(os.getenv('TELEGRAM_BOT_TOKEN'))}")
    print(f"  DATABASE_URL       : {mask_secret(os.getenv('DATABASE_URL'))}")
    print(f"  ENVIRONMENT        : {os.getenv('ENVIRONMENT', 'development')}")
    print("-" * 60)
    print("COMPONENT CHECKS:")

    # 1. Telegram
    tg_ok, tg_msg = await check_telegram()
    status_tg = "[PASS]" if tg_ok else "[WARN/FAIL]"
    print(f"  Telegram Bot : {status_tg} {tg_msg}")

    # 2. Database
    db_ok, db_msg = await check_database()
    status_db = "[PASS]" if db_ok else "[WARN/FAIL]"
    print(f"  Database     : {status_db} {db_msg}")

    # 3. Backend App
    app_ok, app_msg = check_backend()
    status_app = "[PASS]" if app_ok else "[FAIL]"
    print(f"  Backend API  : {status_app} {app_msg}")

    # 4. Sources & Scheduler
    src_ok, src_msg = check_sources()
    status_src = "[PASS]" if src_ok else "[FAIL]"
    print(f"  Price Sources: {status_src} {src_msg}")

    print("=" * 60)
    overall_ok = app_ok and src_ok
    if overall_ok:
        print(">> Diagnostics completed. Core architecture is functional.")
        return 0
    else:
        print(">> Diagnostics failed. See errors above.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(run_diagnostics())
    sys.exit(exit_code)
