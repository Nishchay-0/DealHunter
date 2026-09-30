"""
backend/main.py
DealHunter FastAPI application — Phase 2 (foundation).

Current endpoints:
  GET /          → redirect to /health
  GET /health    → service + DB liveness check

Future phases will add:
  /api/v1/users, /api/v1/products, /api/v1/watchlist,
  /api/v1/deals, /api/v1/alerts, /api/v1/admin …
"""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy import text

from database.session import get_engine

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("DealHunter API starting up.")
    yield
    try:
        engine = get_engine()
        await engine.dispose()
        logger.info("DealHunter API shut down — DB connections closed.")
    except Exception as exc:
        logger.debug("Shutdown engine cleanup note: %s", exc)


# ---------------------------------------------------------------------------
# App instance
# ---------------------------------------------------------------------------

app = FastAPI(
    title="DealHunter API",
    description="Backend API for the DealHunter deal-alert platform.",
    version="0.2.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/", include_in_schema=False)
async def root() -> RedirectResponse:
    return RedirectResponse(url="/health")


@app.get("/health", tags=["System"])
async def health_check() -> JSONResponse:
    """
    Returns the API status and tests the database connection.
    Used by the diagnose script and future load-balancer probes.
    """
    db_ok = False
    db_error: str | None = None

    try:
        engine = get_engine()
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        db_ok = True
    except Exception as exc:
        db_error = str(exc)
        logger.warning("Health check: DB connection failed — %s", exc)

    status = "ok" if db_ok else "degraded"
    return JSONResponse(
        status_code=200 if db_ok else 503,
        content={
            "status": status,
            "service": "DealHunter API",
            "version": app.version,
            "database": "connected" if db_ok else f"error: {db_error}",
        },
    )
