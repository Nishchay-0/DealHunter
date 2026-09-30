"""
tests/api/test_health.py
API contract tests for FastAPI health and root endpoints.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine


@pytest.mark.asyncio
async def test_root_redirects_to_health(client: AsyncClient):
    """GET / should redirect to /health."""
    response = await client.get("/", follow_redirects=False)
    assert response.status_code == 307
    assert response.headers["location"] == "/health"


@pytest.mark.asyncio
async def test_health_check_healthy(client: AsyncClient, test_engine: AsyncEngine):
    """GET /health should return 200 and status 'ok' when DB check passes."""
    with patch("backend.main.get_engine", return_value=test_engine):
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == "DealHunter API"
        assert data["database"] == "connected"


@pytest.mark.asyncio
async def test_health_check_degraded(client: AsyncClient):
    """GET /health should return 503 and status 'degraded' when DB fails."""
    mock_engine = MagicMock()
    mock_engine.connect.side_effect = RuntimeError("DB connection timeout")

    with patch("backend.main.get_engine", return_value=mock_engine):
        response = await client.get("/health")
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "degraded"
        assert "DB connection timeout" in data["database"]
