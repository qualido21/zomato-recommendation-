"""
src/data/supabase_loader.py
────────────────────────────
Load the restaurant dataset from Supabase instead of a local parquet file.

The Supabase `restaurants` table mirrors the cleaned parquet schema:
  id, name, city, location, cuisines (jsonb), rating, votes,
  approx_cost, budget_tier, rest_type, book_table, online_order, listed_type

Usage
-----
df = load_from_supabase(url, key)
"""

from __future__ import annotations

import json
import logging
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)

_PAGE_SIZE = 1000  # Supabase max rows per request


def load_from_supabase(url: str, key: str) -> pd.DataFrame:
    """
    Fetch all rows from the `restaurants` table and return a cleaned DataFrame
    compatible with FilterEngine.

    Parameters
    ----------
    url : str  — Supabase project URL  (e.g. https://xxxx.supabase.co)
    key : str  — Supabase anon/service key
    """
    try:
        from supabase import create_client  # type: ignore
    except ImportError as exc:
        raise ImportError("Install supabase: pip install supabase>=2.4.0") from exc

    client = create_client(url, key)

    rows: list[dict] = []
    offset = 0

    while True:
        resp = (
            client.table("restaurants")
            .select("*")
            .range(offset, offset + _PAGE_SIZE - 1)
            .execute()
        )
        batch = resp.data or []
        rows.extend(batch)
        if len(batch) < _PAGE_SIZE:
            break
        offset += _PAGE_SIZE

    if not rows:
        raise ValueError("Supabase returned 0 rows from the restaurants table.")

    df = pd.DataFrame(rows)

    # Deserialise cuisines: jsonb comes back as a Python list already,
    # but handle the string case too (defensive).
    def _parse_cuisines(v):
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            try:
                return json.loads(v)
            except Exception:
                return []
        return []

    df["cuisines"] = df["cuisines"].apply(_parse_cuisines)

    # Coerce numeric columns
    df["rating"] = pd.to_numeric(df["rating"], errors="coerce")
    df["votes"] = pd.to_numeric(df["votes"], errors="coerce").fillna(0).astype(int)
    df["approx_cost"] = pd.to_numeric(df["approx_cost"], errors="coerce")
    df["id"] = pd.to_numeric(df["id"], errors="coerce").fillna(0).astype(int)

    # Ensure bool columns
    df["book_table"] = df["book_table"].astype(bool)
    df["online_order"] = df["online_order"].astype(bool)

    # Fill missing text columns
    for col in ("budget_tier", "rest_type", "listed_type", "city", "location"):
        if col in df.columns:
            df[col] = df[col].fillna("").astype(str)
        else:
            df[col] = ""

    logger.info("Loaded %d restaurants from Supabase.", len(df))
    return df
