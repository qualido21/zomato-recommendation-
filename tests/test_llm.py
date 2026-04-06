"""
tests/test_llm.py
─────────────────
Unit tests for Phase 3 — PromptBuilder and ResponseParser.
LLM adapters are tested via mocking (no live API calls).
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.data.schema import Restaurant
from src.filter.schemas import UserPreferences
from src.llm.parser import LLMParseError, Recommendation, parse_response
from src.llm.prompt_builder import PromptBuilder


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def sample_prefs() -> UserPreferences:
    return UserPreferences(
        city="Bangalore",
        budget_max=900,
        cuisines=["Italian"],
        min_rating=3.5,
        extra_prefs="family-friendly",
    )


@pytest.fixture
def sample_candidates() -> list[Restaurant]:
    return [
        Restaurant(
            id=0,
            name="La Piazza",
            city="Bangalore",
            location="Koramangala",
            cuisines=["italian", "continental"],
            rating=4.5,
            votes=1200,
            approx_cost=800,
            budget_tier="medium",
            rest_type="Casual Dining",
            book_table=True,
            online_order=False,
        ),
        Restaurant(
            id=1,
            name="Pasta Street",
            city="Bangalore",
            location="Indiranagar",
            cuisines=["italian"],
            rating=4.2,
            votes=600,
            approx_cost=700,
            budget_tier="medium",
            rest_type="Quick Bites",
            book_table=False,
            online_order=True,
        ),
    ]


@pytest.fixture
def valid_llm_response() -> str:
    return json.dumps([
        {
            "rank": 1,
            "name": "La Piazza",
            "cuisine": "Italian, Continental",
            "rating": 4.5,
            "estimated_cost": "₹800 for two",
            "explanation": "La Piazza offers authentic Italian cuisine in Koramangala.",
        },
        {
            "rank": 2,
            "name": "Pasta Street",
            "cuisine": "Italian",
            "rating": 4.2,
            "estimated_cost": "₹700 for two",
            "explanation": "A cozy Italian spot perfect for families.",
        },
    ])


# ── PromptBuilder tests ───────────────────────────────────────────────────────

class TestPromptBuilder:
    def setup_method(self):
        self.builder = PromptBuilder()

    def test_returns_two_strings(self, sample_prefs, sample_candidates):
        system, user = self.builder.build(sample_prefs, sample_candidates)
        assert isinstance(system, str)
        assert isinstance(user, str)

    def test_system_prompt_fixed(self, sample_prefs, sample_candidates):
        system, _ = self.builder.build(sample_prefs, sample_candidates)
        assert "restaurant recommendation assistant" in system.lower()
        assert "valid JSON only" in system

    def test_user_prompt_contains_city(self, sample_prefs, sample_candidates):
        _, user = self.builder.build(sample_prefs, sample_candidates)
        assert "Bangalore" in user

    def test_user_prompt_contains_budget(self, sample_prefs, sample_candidates):
        _, user = self.builder.build(sample_prefs, sample_candidates)
        assert "Medium" in user or "medium" in user

    def test_user_prompt_contains_cuisine(self, sample_prefs, sample_candidates):
        _, user = self.builder.build(sample_prefs, sample_candidates)
        assert "Italian" in user

    def test_user_prompt_contains_extra_prefs(self, sample_prefs, sample_candidates):
        _, user = self.builder.build(sample_prefs, sample_candidates)
        assert "family-friendly" in user

    def test_user_prompt_contains_candidate_names(self, sample_prefs, sample_candidates):
        _, user = self.builder.build(sample_prefs, sample_candidates)
        assert "La Piazza" in user
        assert "Pasta Street" in user

    def test_empty_cuisines_shows_any(self, sample_candidates):
        prefs = UserPreferences(city="Bangalore", budget_max=900, cuisines=[], min_rating=3.5)
        _, user = self.builder.build(prefs, sample_candidates)
        assert "Any" in user

    def test_no_extra_prefs_shows_none(self, sample_candidates):
        prefs = UserPreferences(city="Bangalore", budget_max=900, cuisines=["Italian"], min_rating=3.5)
        _, user = self.builder.build(prefs, sample_candidates)
        assert "None" in user


# ── parse_response tests ──────────────────────────────────────────────────────

class TestParseResponse:
    def test_valid_json_array(self, valid_llm_response):
        result = parse_response(valid_llm_response)
        assert len(result) == 2
        assert all(isinstance(r, Recommendation) for r in result)

    def test_sorted_by_rank(self, valid_llm_response):
        # Reverse the order in raw response and confirm sorting
        data = json.loads(valid_llm_response)
        data.reverse()
        result = parse_response(json.dumps(data))
        assert result[0].rank == 1
        assert result[1].rank == 2

    def test_strips_markdown_fences(self, valid_llm_response):
        wrapped = f"```json\n{valid_llm_response}\n```"
        result = parse_response(wrapped)
        assert len(result) == 2

    def test_strips_plain_fences(self, valid_llm_response):
        wrapped = f"```\n{valid_llm_response}\n```"
        result = parse_response(wrapped)
        assert len(result) == 2

    def test_recommendation_fields(self, valid_llm_response):
        result = parse_response(valid_llm_response)
        r = result[0]
        assert r.rank == 1
        assert r.name == "La Piazza"
        assert isinstance(r.rating, float)
        assert isinstance(r.explanation, str)
        assert "₹" in r.estimated_cost

    def test_malformed_json_raises_parse_error(self):
        with pytest.raises(LLMParseError):
            parse_response("this is not json at all !!!")

    def test_non_array_raises_parse_error(self):
        with pytest.raises(LLMParseError):
            parse_response('{"rank": 1, "name": "Foo"}')

    def test_empty_array_raises_parse_error(self):
        with pytest.raises(LLMParseError):
            parse_response("[]")

    def test_missing_required_field_raises_parse_error(self):
        bad = json.dumps([{"rank": 1, "name": "Foo"}])  # missing cuisine, rating, etc.
        with pytest.raises(LLMParseError):
            parse_response(bad)


# ── Adapter mock tests ────────────────────────────────────────────────────────

class TestGroqAdapter:
    @pytest.mark.asyncio
    async def test_complete_returns_string(self, valid_llm_response):
        from src.llm.adapter import GroqAdapter

        adapter = GroqAdapter(api_key="test-key", model="llama3-8b-8192")
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": valid_llm_response}}]
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value = mock_client

            result = await adapter.complete("system", "user")

        assert result == valid_llm_response

    def test_build_adapter_groq(self):
        from src.llm.adapter import GroqAdapter, build_adapter

        with patch.dict("os.environ", {"LLM_PROVIDER": "groq", "GROQ_API_KEY": "test"}):
            adapter = build_adapter()
        assert isinstance(adapter, GroqAdapter)

    def test_build_adapter_unknown_raises(self):
        from src.llm.adapter import build_adapter

        with pytest.raises(ValueError, match="Unknown LLM_PROVIDER"):
            build_adapter("foobar")
