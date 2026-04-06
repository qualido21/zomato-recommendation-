"""
tests/test_groq_live.py
────────────────────────
Live integration tests — hits the real Groq API.
Requires GROQ_API_KEY set in .env.

Run: python3 -m pytest tests/test_groq_live.py -v -s
"""

from __future__ import annotations

import os

import pytest
from dotenv import load_dotenv

# Load .env before anything else
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

from src.data.schema import Restaurant
from src.filter.schemas import UserPreferences
from src.llm.adapter import GroqAdapter
from src.llm.parser import Recommendation, parse_response
from src.llm.prompt_builder import PromptBuilder


# ── Shared fixtures ───────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def adapter():
    key = os.getenv("GROQ_API_KEY")
    if not key:
        pytest.skip("GROQ_API_KEY not set — skipping live tests.")
    return GroqAdapter(api_key=key, model="llama-3.1-8b-instant")


@pytest.fixture(scope="module")
def candidates() -> list[Restaurant]:
    return [
        Restaurant(
            id=0, name="La Piazza", city="Bangalore", location="Koramangala",
            cuisines=["italian", "continental"], rating=4.5, votes=1200,
            approx_cost=800, budget_tier="medium", rest_type="Casual Dining",
            book_table=True, online_order=False,
        ),
        Restaurant(
            id=1, name="Pasta Street", city="Bangalore", location="Indiranagar",
            cuisines=["italian"], rating=4.2, votes=600, approx_cost=700,
            budget_tier="medium", rest_type="Quick Bites",
            book_table=False, online_order=True,
        ),
        Restaurant(
            id=2, name="Trattoria Roma", city="Bangalore", location="HSR Layout",
            cuisines=["italian", "pizza"], rating=4.0, votes=400, approx_cost=750,
            budget_tier="medium", rest_type="Casual Dining",
            book_table=False, online_order=True,
        ),
    ]


# ── Test 1: Raw API connectivity ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_groq_api_connectivity(adapter):
    """Verify the Groq API responds to a minimal prompt."""
    print("\n[Test 1] Checking Groq API connectivity...")
    response = await adapter.complete(
        system="You are a helpful assistant.",
        user="Reply with exactly one word: OK",
    )
    print(f"  Response: {response!r}")
    assert isinstance(response, str)
    assert len(response.strip()) > 0


# ── Test 2: Full pipeline — PromptBuilder → Groq → parse_response ─────────────

@pytest.mark.asyncio
async def test_full_recommendation_pipeline(adapter, candidates):
    """Run the complete Phase 3 pipeline and validate the output shape."""
    print("\n[Test 2] Running full recommendation pipeline...")

    prefs = UserPreferences(
        city="Bangalore",
        budget_max=900,
        cuisines=["Italian"],
        min_rating=3.5,
        extra_prefs="looking for a cozy dinner spot",
    )

    builder = PromptBuilder()
    system_prompt, user_prompt = builder.build(prefs, candidates)

    raw = await adapter.complete(system_prompt, user_prompt)
    print(f"  Raw LLM output (first 300 chars):\n  {raw[:300]}")

    recommendations = parse_response(raw)
    print(f"  Parsed {len(recommendations)} recommendation(s):")
    for r in recommendations:
        print(f"    #{r.rank} {r.name} | {r.cuisine} | {r.rating} | {r.estimated_cost}")

    assert len(recommendations) >= 1
    assert all(isinstance(r, Recommendation) for r in recommendations)
    assert recommendations[0].rank == 1
    assert all(r.name for r in recommendations)
    assert all(r.explanation for r in recommendations)


# ── Test 3: Response is valid JSON (no markdown leakage) ──────────────────────

@pytest.mark.asyncio
async def test_response_is_parseable_json(adapter, candidates):
    """Confirm the LLM honours the JSON-only instruction."""
    print("\n[Test 3] Checking LLM returns parseable JSON...")

    prefs = UserPreferences(
        city="Bangalore", budget_max=900, cuisines=["Italian"], min_rating=3.5
    )
    builder = PromptBuilder()
    system_prompt, user_prompt = builder.build(prefs, candidates)

    raw = await adapter.complete(system_prompt, user_prompt)
    recommendations = parse_response(raw)   # raises LLMParseError if unparseable

    print(f"  JSON parsed cleanly — {len(recommendations)} result(s).")
    assert len(recommendations) >= 1


# ── Test 4: Ranked order is correct ───────────────────────────────────────────

@pytest.mark.asyncio
async def test_recommendations_are_ranked(adapter, candidates):
    """Verify that returned recommendations have strictly ordered rank values."""
    print("\n[Test 4] Verifying ranked order...")

    prefs = UserPreferences(
        city="Bangalore", budget_max=900, cuisines=["Italian"], min_rating=3.5
    )
    builder = PromptBuilder()
    system_prompt, user_prompt = builder.build(prefs, candidates)

    raw = await adapter.complete(system_prompt, user_prompt)
    recommendations = parse_response(raw)

    ranks = [r.rank for r in recommendations]
    print(f"  Ranks returned: {ranks}")
    assert ranks == sorted(ranks), f"Ranks are not in order: {ranks}"
