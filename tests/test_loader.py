"""
tests/test_loader.py
────────────────────
Unit tests for Phase 1 — Data Foundation.

Tests cover:
  - _parse_rating : all valid, invalid, and edge-case formats
  - _parse_cost   : commas, nulls, plain integers
  - _parse_cuisines : splitting, lowercasing, stripping
  - _parse_bool_yn  : Yes/No/null variants
  - cost_to_budget_tier : Low/Medium/High boundaries
  - clean()       : full pipeline on synthetic raw DataFrame
  - df_to_restaurants() : Pydantic model conversion and validation
  - save_parquet / load_clean : round-trip integrity
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from src.data.loader import (
    _parse_bool_yn,
    _parse_cost,
    _parse_cuisines,
    _parse_rating,
    clean,
    df_to_restaurants,
    load_clean,
    save_parquet,
)
from src.data.schema import Restaurant, cost_to_budget_tier


# ── _parse_rating ──────────────────────────────────────────────────────────────

class TestParseRating:
    def test_fraction_format(self):
        assert _parse_rating("4.1/5") == pytest.approx(4.1)

    def test_fraction_format_no_decimals(self):
        assert _parse_rating("4/5") == pytest.approx(4.0)

    def test_plain_float_string(self):
        assert _parse_rating("3.8") == pytest.approx(3.8)

    def test_new_returns_none(self):
        assert _parse_rating("NEW") is None

    def test_dash_returns_none(self):
        assert _parse_rating("-") is None

    def test_nan_returns_none(self):
        assert _parse_rating(float("nan")) is None

    def test_none_input_returns_none(self):
        assert _parse_rating(None) is None

    def test_empty_string_returns_none(self):
        assert _parse_rating("") is None

    def test_whitespace_string_returns_none(self):
        assert _parse_rating("   ") is None


# ── _parse_cost ────────────────────────────────────────────────────────────────

class TestParseCost:
    def test_plain_integer_string(self):
        assert _parse_cost("800") == 800

    def test_comma_separated(self):
        assert _parse_cost("1,200") == 1200

    def test_float_string(self):
        assert _parse_cost("950.0") == 950

    def test_nan_returns_none(self):
        assert _parse_cost(float("nan")) is None

    def test_none_returns_none(self):
        assert _parse_cost(None) is None

    def test_non_numeric_returns_none(self):
        assert _parse_cost("N/A") is None


# ── _parse_cuisines ────────────────────────────────────────────────────────────

class TestParseCuisines:
    def test_basic_split(self):
        assert _parse_cuisines("North Indian, Chinese") == ["north indian", "chinese"]

    def test_single_cuisine(self):
        assert _parse_cuisines("Italian") == ["italian"]

    def test_extra_whitespace(self):
        assert _parse_cuisines("  Mexican ,  Japanese  ") == ["mexican", "japanese"]

    def test_nan_returns_empty(self):
        assert _parse_cuisines(float("nan")) == []

    def test_none_returns_empty(self):
        assert _parse_cuisines(None) == []

    def test_empty_string_returns_empty(self):
        assert _parse_cuisines("") == []


# ── _parse_bool_yn ─────────────────────────────────────────────────────────────

class TestParseBoolYN:
    def test_yes_returns_true(self):
        assert _parse_bool_yn("Yes") is True

    def test_no_returns_false(self):
        assert _parse_bool_yn("No") is False

    def test_case_insensitive(self):
        assert _parse_bool_yn("YES") is True
        assert _parse_bool_yn("no") is False

    def test_nan_returns_false(self):
        assert _parse_bool_yn(float("nan")) is False

    def test_none_returns_false(self):
        assert _parse_bool_yn(None) is False


# ── cost_to_budget_tier ────────────────────────────────────────────────────────

class TestCostToBudgetTier:
    def test_low_boundary(self):
        assert cost_to_budget_tier(400) == "low"

    def test_medium_lower(self):
        assert cost_to_budget_tier(401) == "medium"

    def test_medium_upper(self):
        assert cost_to_budget_tier(900) == "medium"

    def test_high_boundary(self):
        assert cost_to_budget_tier(901) == "high"

    def test_zero_is_low(self):
        assert cost_to_budget_tier(0) == "low"

    def test_none_defaults_to_medium(self):
        assert cost_to_budget_tier(None) == "medium"


# ── clean() ────────────────────────────────────────────────────────────────────

def _make_raw_df() -> pd.DataFrame:
    """Build a synthetic raw DataFrame that mirrors HuggingFace column names."""
    return pd.DataFrame(
        {
            "name": ["Good Eats", "Bad Eats", None, "Dup Place", "Dup Place"],
            "location": ["Koramangala", "Indiranagar", "Bandra", "MG Road", "MG Road"],
            "rate": ["4.2/5", "NEW", "3.5/5", "4.0/5", "4.0/5"],
            "votes": ["200", "50", "30", "100", "100"],
            "cuisines": ["North Indian, Chinese", "Italian", "Mexican", "Thai", "Thai"],
            "approx_cost(for two people)": ["600", "1,500", "300", "800", "800"],
            "rest_type": ["Casual Dining", "Quick Bites", "Café", "Buffet", "Buffet"],
            "book_table": ["Yes", "No", "No", "Yes", "Yes"],
            "online_order": ["No", "Yes", "Yes", "No", "No"],
            "listed_in(type)": ["Dine-out", "Cafes", "Cafes", "Buffet", "Buffet"],
            "listed_in(city)": ["Bangalore", "Bangalore", "Mumbai", "Delhi", "Delhi"],
        }
    )


class TestClean:
    def test_drops_null_name_rows(self):
        df = clean(_make_raw_df())
        assert df["name"].notna().all()

    def test_drops_duplicates(self):
        df = clean(_make_raw_df())
        assert len(df[df["name"] == "Dup Place"]) == 1

    def test_rating_parsed_correctly(self):
        df = clean(_make_raw_df())
        good_eats = df[df["name"] == "Good Eats"].iloc[0]
        assert good_eats["rating"] == pytest.approx(4.2)

    def test_new_rating_becomes_none(self):
        df = clean(_make_raw_df())
        bad_eats = df[df["name"] == "Bad Eats"].iloc[0]
        assert pd.isna(bad_eats["rating"])

    def test_budget_tier_mapping(self):
        df = clean(_make_raw_df())
        good = df[df["name"] == "Good Eats"].iloc[0]
        assert good["budget_tier"] == "medium"   # 600 → medium

        bad = df[df["name"] == "Bad Eats"].iloc[0]
        assert bad["budget_tier"] == "high"       # 1500 → high

        mexican = df[df["name"] == "Good Eats".replace("Good Eats", "Good Eats")]
        # Just verify all tiers are valid values
        assert set(df["budget_tier"].unique()).issubset({"low", "medium", "high"})

    def test_cuisines_are_lists(self):
        df = clean(_make_raw_df())
        assert all(isinstance(c, list) for c in df["cuisines"])

    def test_cuisines_are_lowercase(self):
        df = clean(_make_raw_df())
        for cuisines in df["cuisines"]:
            for c in cuisines:
                assert c == c.lower()

    def test_city_is_title_case(self):
        df = clean(_make_raw_df())
        assert all(df["city"] == df["city"].str.title())

    def test_id_column_exists(self):
        df = clean(_make_raw_df())
        assert "id" in df.columns
        assert df["id"].is_monotonic_increasing

    def test_votes_are_integers(self):
        df = clean(_make_raw_df())
        assert df["votes"].dtype in (int, "int64", "int32")

    def test_output_columns_complete(self):
        df = clean(_make_raw_df())
        expected = {"id", "name", "city", "location", "cuisines",
                    "rating", "votes", "approx_cost", "budget_tier",
                    "rest_type", "book_table", "online_order"}
        assert expected.issubset(set(df.columns))


# ── df_to_restaurants() ────────────────────────────────────────────────────────

class TestDfToRestaurants:
    def test_returns_list_of_restaurants(self, sample_df):
        results = df_to_restaurants(sample_df)
        assert all(isinstance(r, Restaurant) for r in results)

    def test_count_matches_rows(self, sample_df):
        results = df_to_restaurants(sample_df)
        assert len(results) == len(sample_df)

    def test_null_rating_is_none(self, sample_df):
        results = df_to_restaurants(sample_df)
        unrated = next(r for r in results if r.name == "Unrated Café")
        assert unrated.rating is None

    def test_null_cost_is_none(self, sample_df):
        results = df_to_restaurants(sample_df)
        unrated = next(r for r in results if r.name == "Unrated Café")
        assert unrated.approx_cost is None

    def test_cuisines_is_list(self, sample_df):
        results = df_to_restaurants(sample_df)
        for r in results:
            assert isinstance(r.cuisines, list)

    def test_to_prompt_dict_keys(self, sample_df):
        results = df_to_restaurants(sample_df)
        prompt = results[0].to_prompt_dict()
        assert "name" in prompt
        assert "cuisines" in prompt
        assert "rating" in prompt
        assert "budget_tier" in prompt


# ── save_parquet / load_clean round-trip ──────────────────────────────────────

class TestParquetRoundTrip:
    def test_save_and_load(self, sample_df, tmp_path):
        path = tmp_path / "test_clean.parquet"
        save_parquet(sample_df, path=path)
        assert path.exists()

        loaded = load_clean(path=path)
        assert len(loaded) == len(sample_df)
        assert list(loaded.columns) == list(sample_df.columns)

    def test_cuisines_deserialised_as_list(self, sample_df, tmp_path):
        path = tmp_path / "test_clean.parquet"
        save_parquet(sample_df, path=path)
        loaded = load_clean(path=path)
        for v in loaded["cuisines"]:
            assert isinstance(v, list)

    def test_load_raises_if_missing(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            load_clean(path=tmp_path / "nonexistent.parquet")
