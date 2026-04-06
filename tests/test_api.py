"""
tests/test_api.py
──────────────────
Integration tests for Phase 4 — FastAPI backend.

Uses httpx.AsyncClient with ASGITransport so no server process is needed.
The LLM adapter is mocked — all other components (FilterEngine, PromptBuilder,
ResponseParser) run for real against the sample_df fixture.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient

import src.api.dependencies as deps
from src.api.main import app
from src.api.dependencies import AppState
from src.filter.engine import FilterEngine as FE
from src.llm.adapter import GroqAdapter


# ── Sample data fixture ───────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def patch_app_state(sample_df):
    """
    Replace the module-level singleton with a test state built from sample_df.
    Patches the LLM adapter with a mock that returns a valid recommendations JSON.
    """
    mock_adapter = AsyncMock(spec=GroqAdapter)
    mock_adapter.complete = AsyncMock(return_value=json.dumps([
        {
            "rank": 1,
            "name": "La Piazza",
            "cuisine": "Italian, Continental",
            "rating": 4.5,
            "estimated_cost": "₹800 for two",
            "explanation": "La Piazza is a top-rated Italian restaurant in Koramangala.",
        }
    ]))

    state = AppState(
        engine=FE(sample_df),
        adapter=mock_adapter,
        llm_provider="groq-mock",
    )
    deps._state = state
    yield
    deps._state = None


@pytest.fixture
def client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


# ── GET /health ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_health_ok(client):
    async with client as c:
        r = await c.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["dataset_loaded"] is True
    assert body["llm_provider"] == "groq-mock"


# ── GET /locations ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_locations_returns_cities(client):
    async with client as c:
        r = await c.get("/locations")
    assert r.status_code == 200
    cities = r.json()["cities"]
    # Now returns location column values (localities)
    assert "Koramangala" in cities
    assert "Indiranagar" in cities
    assert isinstance(cities, list)


# ── GET /cuisines ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_cuisines_returns_list(client):
    async with client as c:
        r = await c.get("/cuisines")
    assert r.status_code == 200
    cuisines = r.json()["cuisines"]
    assert len(cuisines) > 0
    assert all(isinstance(c, str) for c in cuisines)


# ── POST /recommend — happy path ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_recommend_success(client):
    payload = {
        "city": "Koramangala",
        "budget_max": 900,
        "cuisines": ["italian"],
        "min_rating": 3.5,
        "extra_prefs": "cozy",
    }
    async with client as c:
        r = await c.post("/recommend", json=payload)
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "success"
    assert body["total_candidates"] >= 1
    assert len(body["recommendations"]) >= 1
    rec = body["recommendations"][0]
    assert rec["rank"] == 1
    assert rec["name"] == "La Piazza"
    assert "explanation" in rec


# ── POST /recommend — query is echoed ────────────────────────────────────────

@pytest.mark.asyncio
async def test_recommend_echoes_query(client):
    payload = {"city": "Koramangala", "budget_max": 900, "cuisines": ["italian"], "min_rating": 4.0}
    async with client as c:
        r = await c.post("/recommend", json=payload)
    body = r.json()
    assert body["query"]["city"] == "Koramangala"
    assert body["query"]["budget_max"] == 900


# ── POST /recommend — city not found → 404 ───────────────────────────────────

@pytest.mark.asyncio
async def test_recommend_city_not_found(client):
    payload = {"city": "Atlantis", "budget_max": 900, "cuisines": ["italian"], "min_rating": 3.5}
    async with client as c:
        r = await c.post("/recommend", json=payload)
    assert r.status_code == 404
    assert "Atlantis" in r.json()["detail"]


# ── POST /recommend — no results after filters → 404 ─────────────────────────

@pytest.mark.asyncio
async def test_recommend_no_results(client):
    payload = {"city": "Bandra", "budget_max": 100, "cuisines": ["sushi"], "min_rating": 5.0}
    async with client as c:
        r = await c.post("/recommend", json=payload)
    assert r.status_code == 404


# ── POST /recommend — LLM failure triggers fallback ──────────────────────────

@pytest.mark.asyncio
async def test_recommend_llm_fallback(client):
    """If LLM raises an LLM-specific error, fall back gracefully (status=fallback, 200)."""
    import httpx
    deps._state.adapter.complete = AsyncMock(
        side_effect=httpx.TimeoutException("Groq timeout")
    )

    payload = {"city": "Koramangala", "budget_max": 900, "cuisines": ["italian"], "min_rating": 3.5}
    async with client as c:
        r = await c.post("/recommend", json=payload)
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "fallback"
    assert body["llm_used"] is False
    assert len(body["recommendations"]) >= 1


# ── POST /recommend — bad input → 422 ────────────────────────────────────────

@pytest.mark.asyncio
async def test_recommend_missing_budget(client):
    # budget_max is required — omitting it should give 422
    payload = {"city": "Bangalore", "cuisines": ["italian"], "min_rating": 3.5}
    async with client as c:
        r = await c.post("/recommend", json=payload)
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_recommend_negative_budget(client):
    payload = {"city": "Koramangala", "budget_max": -100, "cuisines": ["italian"], "min_rating": 3.5}
    async with client as c:
        r = await c.post("/recommend", json=payload)
    assert r.status_code == 422
