"""
database/session.py
Async SQLAlchemy engine and session factory.

Design decisions:
- AsyncEngine + AsyncSession throughout the app so we never block
  the event loop (the Telegram bot and FastAPI both run async).
- Normalizes connection URLs (e.g. postgresql:// -> postgresql+asyncpg://,
  sqlite:// -> sqlite+aiosqlite://) for standard connection strings.
- get_db() is a FastAPI dependency that yields a session and
  commits/rolls back automatically.
- engine is created lazily the first time get_engine() is called
  so tests can swap DATABASE_URL before importing or between tests.
"""

from __future__ import annotations

import os
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def normalize_database_url(url: str) -> str:
    """Normalize common database URLs to async dialects."""
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+asyncpg://", 1)
    if url.startswith("postgresql://") and not url.startswith("postgresql+"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if url.startswith("sqlite://") and not url.startswith("sqlite+"):
        return url.replace("sqlite://", "sqlite+aiosqlite://", 1)
    return url


def get_engine() -> AsyncEngine:
    """Return (or lazily create) the shared async engine."""
    global _engine
    if _engine is None:
        raw_url = os.getenv("DATABASE_URL")
        if not raw_url:
            raise RuntimeError(
                "DATABASE_URL is not set. "
                "Add it to your .env file before starting the server."
            )
        url = normalize_database_url(raw_url)
        engine_kwargs: dict = {
            "echo": False,
        }
        if not url.startswith("sqlite"):
            engine_kwargs["pool_pre_ping"] = True
            engine_kwargs["pool_size"] = 10
            engine_kwargs["max_overflow"] = 20

        _engine = create_async_engine(url, **engine_kwargs)
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Return (or lazily create) the shared session factory."""
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            bind=get_engine(),
            expire_on_commit=False,  # objects remain usable after commit
            autoflush=False,
        )
    return _session_factory


async def reset_engine() -> None:
    """Dispose and reset the current engine (primarily for test teardown)."""
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
        _engine = None
    _session_factory = None


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that provides one AsyncSession per request.
    Commits on success, rolls back on any exception, always closes.
    """
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
