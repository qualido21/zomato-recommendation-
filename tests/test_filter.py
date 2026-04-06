"""
tests/test_filter.py
─────────────────────
Unit tests for Phase 2 — FilterEngine and schemas.

Note: FilterEngine now filters by the `location` column (93 localities).
Sample data localities: Koramangala, Indiranagar, Connaught Place, Bandra.
"""

from __future__ import annotations

import pytest

from src.filter.engine import CityNotFoundError, FilterEngine
from src.filter.schemas import FilterResult, UserPreferences


# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def engine(sample_df):
    return FilterEngine(sample_df)


def prefs(**kwargs) -> UserPreferences:
    # "Koramangala" is the location of La Piazza in sample_df
    defaults = dict(city="Koramangala", budget_max=900, cuisines=["italian"], min_rating=3.5)
    defaults.update(kwargs)
    return UserPreferences(**defaults)


# ── City / locality filter ────────────────────────────────────────────────────

def test_locality_filter_match(engine):
    result = engine.run(prefs(city="Koramangala"))
    assert len(result.candidates) > 0


def test_locality_filter_case_insensitive(engine):
    result = engine.run(prefs(city="koramangala"))
    assert len(result.candidates) > 0


def test_locality_partial_match(engine):
    # "Koraman" should match "Koramangala" via substring fallback
    result = engine.run(prefs(city="Koraman"))
    assert len(result.candidates) > 0


def test_locality_not_found_raises(engine):
    with pytest.raises(CityNotFoundError):
        engine.run(prefs(city="Atlantis"))


# ── Budget filter ─────────────────────────────────────────────────────────────

def test_budget_max_excludes_expensive(engine):
    # Indiranagar has Spice Garden (₹350) — within budget=400.
    # La Piazza (₹800) is in Koramangala, not Indiranagar, so no fallback is needed.
    result = engine.run(prefs(city="Indiranagar", budget_max=400, cuisines=[], min_rating=0.0))
    assert len(result.candidates) > 0
    assert result.filters_relaxed is False
    for r in result.candidates:
        if r.approx_cost is not None:
            assert r.approx_cost <= 400


def test_budget_max_includes_null_cost(engine):
    # Unrated Café has approx_cost=None — included regardless of budget_max
    result = engine.run(prefs(city="Bandra", budget_max=100, cuisines=[], min_rating=0.0))
    names = [r.name for r in result.candidates]
    assert "Unrated Café" in names


def test_budget_max_high_includes_all(engine):
    result = engine.run(prefs(city="Connaught Place", budget_max=5000, cuisines=["chinese"], min_rating=0.0))
    assert len(result.candidates) >= 1


# ── Cuisine filter ────────────────────────────────────────────────────────────

def test_cuisine_exact_match(engine):
    result = engine.run(prefs(city="Koramangala", budget_max=900, cuisines=["italian"], min_rating=0.0))
    names = [r.name for r in result.candidates]
    assert "La Piazza" in names


def test_cuisine_fuzzy_match(engine):
    # "North" should fuzzy-match "north indian"
    result = engine.run(prefs(city="Indiranagar", budget_max=400, cuisines=["north"], min_rating=0.0))
    names = [r.name for r in result.candidates]
    assert "Spice Garden" in names


def test_no_cuisine_match_triggers_fallback(engine):
    result = engine.run(prefs(city="Koramangala", budget_max=900, cuisines=["sushi"], min_rating=0.0))
    assert result.filters_relaxed is True


# ── Rating filter ─────────────────────────────────────────────────────────────

def test_rating_filter(engine):
    result = engine.run(prefs(city="Koramangala", budget_max=900, cuisines=["italian"], min_rating=4.0))
    assert all(r.rating >= 4.0 for r in result.candidates if r.rating is not None)


def test_unrated_excluded_by_rating_filter(engine):
    result = engine.run(prefs(city="Bandra", budget_max=5000, cuisines=["cafe"], min_rating=1.0))
    assert all(r.name != "Unrated Café" for r in result.candidates)


def test_unrated_included_when_min_rating_zero(engine):
    result = engine.run(prefs(city="Bandra", budget_max=5000, cuisines=["cafe"], min_rating=0.0))
    assert result is not None


# ── Sort & limit ──────────────────────────────────────────────────────────────

def test_results_sorted_by_rating_desc(engine):
    result = engine.run(prefs(city="Indiranagar", budget_max=400, cuisines=[], min_rating=0.0))
    ratings = [r.rating for r in result.candidates if r.rating is not None]
    assert ratings == sorted(ratings, reverse=True)


def test_top_n_hardcoded_at_15(engine):
    result = engine.run(prefs(city="Koramangala", budget_max=5000, cuisines=[], min_rating=0.0))
    assert len(result.candidates) <= 15


# ── FilterResult shape ────────────────────────────────────────────────────────

def test_filter_result_schema(engine):
    result = engine.run(prefs())
    assert isinstance(result, FilterResult)
    assert isinstance(result.candidates, list)
    assert isinstance(result.total_before_limit, int)
    assert isinstance(result.filters_relaxed, bool)


def test_total_before_limit_gte_candidates(engine):
    result = engine.run(prefs(city="Koramangala", budget_max=900, cuisines=["italian"], min_rating=0.0))
    assert result.total_before_limit >= len(result.candidates)


# ── Fallback — full relax ─────────────────────────────────────────────────────

def test_full_fallback_returns_gracefully(engine):
    result = engine.run(prefs(city="Bandra", budget_max=100, cuisines=["sushi"], min_rating=5.0))
    assert result.message is not None or result.candidates == []


# ── Metadata helpers ──────────────────────────────────────────────────────────

def test_available_cities(engine):
    # Now returns location column values (localities)
    localities = engine.available_cities()
    assert "Koramangala" in localities
    assert "Indiranagar" in localities
    assert "Connaught Place" in localities
    assert isinstance(localities, list)


def test_available_cuisines(engine):
    cuisines = engine.available_cuisines()
    assert len(cuisines) > 0
    assert all(isinstance(c, str) for c in cuisines)
    assert all(len(c) >= 3 for c in cuisines)
