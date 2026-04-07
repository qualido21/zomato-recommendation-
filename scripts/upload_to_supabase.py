"""
scripts/upload_to_supabase.py
──────────────────────────────
One-time script to upload the cleaned parquet dataset to Supabase.

Usage
-----
1. Create the table in Supabase SQL Editor:
       supabase/create_restaurants_table.sql

2. Set env vars (or create a .env file):
       SUPABASE_URL=https://xxxx.supabase.co
       SUPABASE_SERVICE_KEY=your-service-role-key  ← use service key (bypasses RLS)

3. Run:
       python scripts/upload_to_supabase.py
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Load .env if present
env_file = ROOT / ".env"
if env_file.exists():
    for line in env_file.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"'))

import pandas as pd
from supabase import create_client

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")

PARQUET_PATH = ROOT / "data" / "zomato_clean.parquet"
BATCH_SIZE = 500


def main() -> None:
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("ERROR: Set SUPABASE_URL and SUPABASE_SERVICE_KEY in your .env file.")
        sys.exit(1)

    print(f"Loading dataset from {PARQUET_PATH} …")
    df = pd.read_parquet(PARQUET_PATH)

    # Deserialise cuisines from JSON string → list
    def parse_cuisines(v):
        if isinstance(v, list):
            return v
        try:
            return json.loads(v)
        except Exception:
            return []

    df["cuisines"] = df["cuisines"].apply(parse_cuisines)

    # Convert to list of dicts, replacing NaN with None
    records = []
    for row in df.itertuples(index=False):
        records.append({
            "id":           int(row.id),
            "name":         str(row.name),
            "city":         str(row.city),
            "location":     str(row.location),
            "cuisines":     row.cuisines if isinstance(row.cuisines, list) else [],
            "rating":       float(row.rating) if pd.notna(row.rating) else None,
            "votes":        int(row.votes),
            "approx_cost":  int(row.approx_cost) if pd.notna(row.approx_cost) else None,
            "budget_tier":  str(row.budget_tier),
            "rest_type":    str(row.rest_type),
            "book_table":   bool(row.book_table),
            "online_order": bool(row.online_order),
            "listed_type":  str(row.listed_type) if hasattr(row, "listed_type") else "",
        })

    print(f"Uploading {len(records)} rows in batches of {BATCH_SIZE} …")
    client = create_client(SUPABASE_URL, SUPABASE_KEY)

    for i in range(0, len(records), BATCH_SIZE):
        batch = records[i : i + BATCH_SIZE]
        client.table("restaurants").upsert(batch).execute()
        print(f"  Uploaded rows {i + 1}–{i + len(batch)}")

    print(f"\n✅ Done. {len(records)} rows uploaded to Supabase.")


if __name__ == "__main__":
    main()
