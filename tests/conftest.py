"""
tests/conftest.py
─────────────────
Shared pytest fixtures for all test modules.
"""

from __future__ import annotations

import json
import pandas as pd
import pytest

from src.data.schema import Restaurant


# ── Minimal synthetic DataFrame that mirrors cleaned output ───────────────────

@pytest.fixture
def sample_df() -> pd.DataFrame:
    """A small cleaned DataFrame for unit tests (no HuggingFace download needed)."""
    rows = [
        {
            "id": 0,
            "name": "La Piazza",
            "city": "Bangalore",
            "location": "Koramangala",
            "cuisines": json.dumps(["italian", "continental"]),
            "rating": 4.5,
            "votes": 1200,
            "approx_cost": 800,
            "budget_tier": "medium",
            "rest_type": "Casual Dining",
            "book_table": True,
            "online_order": False,
            "listed_type": "Dine-out",
        },
        {
            "id": 1,
            "name": "Spice Garden",
            "city": "Bangalore",
            "location": "Indiranagar",
            "cuisines": json.dumps(["north indian", "mughlai"]),
            "rating": 4.1,
            "votes": 850,
            "approx_cost": 350,
            "budget_tier": "low",
            "rest_type": "Quick Bites",
            "book_table": False,
            "online_order": True,
            "listed_type": "Cafes",
        },
        {
            "id": 2,
            "name": "Dragon Palace",
            "city": "Delhi",
            "location": "Connaught Place",
            "cuisines": json.dumps(["chinese", "thai"]),
            "rating": 3.8,
            "votes": 420,
            "approx_cost": 1200,
            "budget_tier": "high",
            "rest_type": "Casual Dining",
            "book_table": True,
            "online_order": True,
            "listed_type": "Dine-out",
        },
        {
            "id": 3,
            "name": "Unrated Café",
            "city": "Mumbai",
            "location": "Bandra",
            "cuisines": json.dumps(["cafe", "bakery"]),
            "rating": None,
            "votes": 0,
            "approx_cost": None,
            "budget_tier": "medium",
            "rest_type": "Café",
            "book_table": False,
            "online_order": False,
            "listed_type": "Cafes",
        },
    ]
    df = pd.DataFrame(rows)
    # Deserialise cuisines (mirrors load_clean behaviour)
    df["cuisines"] = df["cuisines"].apply(json.loads)
    return df


@pytest.fixture
def sample_restaurants(sample_df) -> list[Restaurant]:
    """List of Restaurant Pydantic models built from sample_df."""
    from src.data.loader import df_to_restaurants
    return df_to_restaurants(sample_df)
