"""
src/filter/engine.py
────────────────────
FilterEngine — accepts UserPreferences and returns a shortlist of candidate
restaurants ready to be ranked by the LLM.

Filter pipeline (in order):
  1. City filter       — exact match first, partial-substring fallback
  2. Budget filter     — approx_cost <= budget_max (unknown cost included)
  3. Cuisine filter    — fuzzy substring match via rapidfuzz
  4. Rating filter     — df['rating'] >= min_rating
  5. Sort & limit      — rating DESC, votes DESC, take top 15

Fallback strategy:
  - City yields 0   → raise CityNotFoundError
  - All filters → 0 → relax cuisine → retry
  - Still 0          → relax budget  → retry
  - Still 0          → return empty FilterResult with no_results flag
"""

from __future__ import annotations

import json
import logging
from typing import List

import pandas as pd
from rapidfuzz import fuzz

from src.data.schema import Restaurant
from src.filter.schemas import FilterResult, UserPreferences

logger = logging.getLogger(__name__)

_CUISINE_SCORE_THRESHOLD = 60
_TOP_N = 15  # Fixed number of candidates sent to the LLM


class CityNotFoundError(ValueError):
    """Raised when the requested city is not in the dataset."""


def _parse_cuisines(value) -> List[str]:
    """Handle cuisines stored as a JSON string or already a list."""
    if isinstance(value, list):
        return value
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return []


def _cuisine_matches(restaurant_cuisines: List[str], wanted: List[str]) -> bool:
    """
    Return True if *any* wanted cuisine fuzzy-matches *any* restaurant cuisine.
    Direct substring check first (fast path), then rapidfuzz partial_ratio.
    """
    for want in wanted:
        want_lower = want.lower().strip()
        for have in restaurant_cuisines:
            have_lower = have.lower().strip()
            if want_lower in have_lower or have_lower in want_lower:
                return True
            if fuzz.partial_ratio(want_lower, have_lower) >= _CUISINE_SCORE_THRESHOLD:
                return True
    return False


def _df_to_restaurants(df: pd.DataFrame) -> List[Restaurant]:
    restaurants: List[Restaurant] = []
    for row in df.itertuples(index=False):
        cuisines = _parse_cuisines(row.cuisines)
        restaurants.append(
            Restaurant(
                id=row.id,
                name=row.name,
                city=row.city,
                location=row.location,
                cuisines=cuisines,
                rating=row.rating if pd.notna(row.rating) else None,
                votes=int(row.votes),
                approx_cost=int(row.approx_cost) if pd.notna(row.approx_cost) else None,
                budget_tier=row.budget_tier,
                rest_type=row.rest_type,
                book_table=bool(row.book_table),
                online_order=bool(row.online_order),
                listed_type=row.listed_type if hasattr(row, "listed_type") else "",
            )
        )
    return restaurants


def _sort_and_limit(df: pd.DataFrame, top_n: int = _TOP_N) -> pd.DataFrame:
    """Sort by rating DESC (NaN last), votes DESC, then take top_n rows."""
    return (
        df.sort_values(
            by=["rating", "votes"],
            ascending=[False, False],
            na_position="last",
        )
        .head(top_n)
    )


class FilterEngine:
    """
    Stateful filter engine loaded once at startup with the full restaurant DataFrame.

    Usage
    -----
    engine = FilterEngine(df)
    result = engine.run(prefs)
    """

    def __init__(self, df: pd.DataFrame) -> None:
        df = df.copy()
        df["cuisines"] = df["cuisines"].apply(_parse_cuisines)
        self._df = df

    # ── Public API ─────────────────────────────────────────────────────────────

    def run(self, prefs: UserPreferences) -> FilterResult:
        """
        Apply the full filter pipeline and return a FilterResult.

        Raises
        ------
        CityNotFoundError
            If no restaurants exist for the requested city (exact or partial match).
        """
        # Step 1 — city filter (exact first, partial-substring fallback)
        city_df = self._filter_city(prefs.city)
        if city_df.empty:
            raise CityNotFoundError(
                f"No restaurants found for location: '{prefs.city}'. "
                "Check available locations via GET /locations."
            )

        # Steps 2–4 — full filter
        filtered = self._apply_filters(city_df, prefs, relax_cuisine=False, relax_budget=False)

        filters_relaxed = False
        message: str | None = None

        if filtered.empty:
            logger.info("No results with full filters; relaxing cuisine filter.")
            filtered = self._apply_filters(city_df, prefs, relax_cuisine=True, relax_budget=False)
            filters_relaxed = True
            message = "Cuisine filter was relaxed to find results."

        if filtered.empty:
            logger.info("Still no results; relaxing budget filter too.")
            filtered = self._apply_filters(city_df, prefs, relax_cuisine=True, relax_budget=True)
            message = "Cuisine and budget filters were relaxed to find results."

        if filtered.empty:
            logger.warning("No restaurants found even after all fallbacks.")
            return FilterResult(
                candidates=[],
                total_before_limit=0,
                filters_relaxed=filters_relaxed,
                message="no_results",
            )

        total_before_limit = len(filtered)
        limited = _sort_and_limit(filtered, _TOP_N)
        candidates = _df_to_restaurants(limited)

        return FilterResult(
            candidates=candidates,
            total_before_limit=total_before_limit,
            filters_relaxed=filters_relaxed,
            message=message,
        )

    # ── Metadata helpers ───────────────────────────────────────────────────────

    def available_cities(self) -> List[str]:
        """Return all distinct locality names from the location column (93 values)."""
        return sorted(self._df["location"].dropna().unique().tolist())

    def available_cuisines(self) -> List[str]:
        """Return all distinct cuisines (cleaned: alpha + space only, length >= 3)."""
        all_cuisines: set[str] = set()
        for cuisines in self._df["cuisines"]:
            for c in cuisines:
                cleaned = c.strip().title()
                # Filter out garbage entries (single chars, punctuation, etc.)
                if len(cleaned) >= 3 and all(ch.isalpha() or ch.isspace() for ch in cleaned):
                    all_cuisines.add(cleaned)
        return sorted(all_cuisines)

    # ── Private helpers ────────────────────────────────────────────────────────

    def _filter_city(self, city: str) -> pd.DataFrame:
        """
        Filter by the `location` column (93 distinct localities).
        Exact match first; partial-substring fallback if 0 rows returned.
        """
        city_lower = city.lower()
        exact = self._df[self._df["location"].str.lower() == city_lower]
        if not exact.empty:
            return exact
        return self._df[self._df["location"].str.lower().str.contains(city_lower, regex=False)]

    def _apply_filters(
        self,
        df: pd.DataFrame,
        prefs: UserPreferences,
        *,
        relax_cuisine: bool,
        relax_budget: bool,
    ) -> pd.DataFrame:
        # Step 2 — budget: include restaurants with unknown cost OR cost within budget
        if not relax_budget:
            df = df[df["approx_cost"].isna() | (df["approx_cost"] <= prefs.budget_max)]

        # Step 3 — cuisine (fuzzy)
        if not relax_cuisine and prefs.cuisines:
            mask = df["cuisines"].apply(
                lambda c: _cuisine_matches(c, prefs.cuisines)
            )
            df = df[mask]

        # Step 4 — rating
        if not df.empty and prefs.min_rating > 0.0:
            df = df[df["rating"].notna() & (df["rating"] >= prefs.min_rating)]

        return df
