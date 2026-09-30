"""
alembic/env.py
Alembic migration environment — async-aware.

Design decisions:
- Uses asyncio.run() + AsyncEngine so migrations run in the same async
  context as the application; no sync psycopg2 driver needed.
- DATABASE_URL is read from the environment (via .env) at run time.
  The .ini file contains no credentials.
- All models are imported here so --autogenerate can detect every table.
"""

from __future__ import annotations

import asyncio
import os
from logging.config import fileConfig

from alembic import context
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine

# Load .env so DATABASE_URL is available when running alembic from the CLI
load_dotenv()

# Alembic Config object — gives access to values in alembic.ini
config = context.config

# Set up Python logging from the ini file (optional but useful)
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Import the declarative base and all models so Alembic can see them
from database.base import Base  # noqa: E402
import database.models  # noqa: E402, F401 — registers all models on Base
from database.session import normalize_database_url  # noqa: E402

target_metadata = Base.metadata


def get_url() -> str:
    url = os.getenv("DATABASE_URL", "")
    if not url:
        raise RuntimeError(
            "DATABASE_URL is not set. "
            "Add it to your .env file before running alembic."
        )
    return normalize_database_url(url)


# ---------------------------------------------------------------------------
# Offline mode (generates SQL without a live connection)
# ---------------------------------------------------------------------------

def run_migrations_offline() -> None:
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


# ---------------------------------------------------------------------------
# Online mode (runs against a live database)
# ---------------------------------------------------------------------------

def do_run_migrations(connection):
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    url = get_url()
    engine_kwargs: dict = {}
    if not url.startswith("sqlite"):
        engine_kwargs["pool_pre_ping"] = True

    engine = create_async_engine(url, **engine_kwargs)
    async with engine.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await engine.dispose()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
