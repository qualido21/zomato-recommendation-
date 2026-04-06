"""
src/data/loader.py
──────────────────
Phase 1 — Data Foundation

Responsibilities:
  1. Pull the Zomato dataset from Hugging Face
  2. Clean & normalise all fields (see architecture.md Phase 1)
  3. Persist the result as data/zomato_clean.parquet

Public API
----------
load_dataset()   → pd.DataFrame   (raw HF dataset as a DataFrame)
clean(df)        → pd.DataFrame   (cleaned DataFrame)
save_parquet(df) → Path           (path to saved file)
load_clean()     → pd.DataFrame   (load already-cleaned parquet)
run()            → pd.DataFrame   (full pipeline: load → clean → save)
df_to_restaurants(df) → List[Restaurant]
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import List, Optional

import pandas as pd

from src.data.schema import Restaurant, cost_to_budget_tier

logger = logging.getLogger(__name__)

# ── Paths ─────────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parents[2]   # …/zomato-ai-recommender/
DATA_DIR = PROJECT_ROOT / "data"
PARQUET_PATH = DATA_DIR / "zomato_clean.parquet"

# ── Hugging Face dataset identifier ───────────────────────────────────────────
HF_DATASET_ID = "ManikaSaini/zomato-restaurant-recommendation"


# ── Step 1: Load from Hugging Face ────────────────────────────────────────────

def load_dataset() -> pd.DataFrame:
    """
    Download the Zomato dataset from Hugging Face and return it as a
    pandas DataFrame.  Requires the `datasets` package.
    """
    try:
        from datasets import load_dataset as hf_load  # type: ignore
    except ImportError as exc:
        raise ImportError(
            "Install the 'datasets' package:  pip install datasets"
        ) from exc

    logger.info("Downloading dataset '%s' from Hugging Face …", HF_DATASET_ID)
    ds = hf_load(HF_DATASET_ID, trust_remote_code=True)

    # HF datasets may have multiple splits; take 'train' or the first available
    split_names = list(ds.keys()) if hasattr(ds, "keys") else ["train"]
    split = "train" if "train" in split_names else split_names[0]
    df = ds[split].to_pandas()

    logger.info("Loaded %d rows, %d columns from Hugging Face.", len(df), len(df.columns))
    logger.debug("Columns: %s", df.columns.tolist())
    return df


# ── Step 2: Clean & Normalise ─────────────────────────────────────────────────

def _parse_rating(value) -> Optional[float]:
    """
    Convert rating strings like "4.1/5", "4.1", "NEW", "-", NaN → float or None.
    """
    if pd.isna(value):
        return None
    s = str(value).strip()
    if s in ("NEW", "-", ""):
        return None
    # Handle "4.1/5" format
    match = re.match(r"^(\d+\.?\d*)\s*/\s*\d+", s)
    if match:
        return float(match.group(1))
    # Plain float string
    try:
        return float(s)
    except ValueError:
        return None


def _parse_cost(value) -> Optional[int]:
    """
    Convert cost strings like "1,200", "800", NaN → integer or None.
    """
    if pd.isna(value):
        return None
    s = str(value).strip().replace(",", "")
    try:
        return int(float(s))
    except ValueError:
        return None


def _parse_cuisines(value) -> List[str]:
    """
    Split comma-separated cuisines into a list of lowercase, stripped strings.
    E.g. "North Indian, Chinese" → ["north indian", "chinese"]
    """
    if pd.isna(value):
        return []
    return [c.strip().lower() for c in str(value).split(",") if c.strip()]


def _parse_bool_yn(value) -> bool:
    """Convert "Yes"/"No" strings (case-insensitive) to bool."""
    if pd.isna(value):
        return False
    return str(value).strip().lower() == "yes"


def clean(df: pd.DataFrame) -> pd.DataFrame:
    """
    Apply all cleaning steps from the architecture and return a tidy DataFrame.

    Cleaning pipeline:
      [1] Drop rows where name or location is null
      [2] Parse rating  ("4.1/5" → 4.1, "NEW"/"–" → None)
      [3] Parse cost    ("1,200" → 1200) and derive budget_tier
      [4] Normalise cuisines into a list
      [5] Normalise city and location (title-case, strip)
      [6] Drop duplicates (name + location)
      [7] Reset index and add id column
    """
    logger.info("Starting data cleaning on %d rows …", len(df))

    # ── Rename columns to clean internal names ──────────────────────────────
    # The HF dataset may use different casing; normalise first
    df.columns = [c.strip() for c in df.columns]

    rename_map = {
        "approx_cost(for two people)": "approx_cost_raw",
        "listed_in(type)": "listed_type",
        "listed_in(city)": "city_raw",
        "rate": "rate_raw",
    }
    df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})

    # ── [1] Drop rows with null name or location ────────────────────────────
    before = len(df)
    df = df.dropna(subset=["name", "location"])
    logger.info("[1] Dropped %d rows with null name/location.", before - len(df))

    # ── [2] Parse rating ────────────────────────────────────────────────────
    df["rating"] = df["rate_raw"].apply(_parse_rating) if "rate_raw" in df.columns else None
    logger.info("[2] Parsed rating. Null ratings: %d", df["rating"].isna().sum())

    # ── [3] Parse cost → budget tier ────────────────────────────────────────
    cost_col = "approx_cost_raw" if "approx_cost_raw" in df.columns else None
    if cost_col:
        df["approx_cost"] = df[cost_col].apply(_parse_cost)
    else:
        df["approx_cost"] = None
    df["budget_tier"] = df["approx_cost"].apply(cost_to_budget_tier)
    logger.info("[3] Parsed cost. Budget tiers: %s", df["budget_tier"].value_counts().to_dict())

    # ── [4] Normalise cuisines ──────────────────────────────────────────────
    df["cuisines"] = df["cuisines"].apply(_parse_cuisines)
    logger.info("[4] Cuisines parsed.")

    # ── [5] Normalise city & location ──────────────────────────────────────
    city_col = "city_raw" if "city_raw" in df.columns else "listed_in(city)"
    if city_col in df.columns:
        df["city"] = df[city_col].apply(
            lambda v: str(v).strip().title() if not pd.isna(v) else "Unknown"
        )
    elif "location" in df.columns:
        # Fallback: use location as city proxy
        df["city"] = df["location"].apply(
            lambda v: str(v).strip().title() if not pd.isna(v) else "Unknown"
        )
    else:
        df["city"] = "Unknown"

    df["location"] = df["location"].apply(
        lambda v: str(v).strip().title() if not pd.isna(v) else "Unknown"
    )
    logger.info("[5] City/location normalised.")

    # ── [6] Drop duplicates ─────────────────────────────────────────────────
    before = len(df)
    df = df.drop_duplicates(subset=["name", "location"])
    logger.info("[6] Dropped %d duplicate (name, location) pairs.", before - len(df))

    # ── [7] Normalise remaining fields ──────────────────────────────────────
    if "votes" in df.columns:
        df["votes"] = pd.to_numeric(df["votes"], errors="coerce").fillna(0).astype(int)
    else:
        df["votes"] = 0

    df["rest_type"] = df.get("rest_type", pd.Series("", index=df.index)).fillna("")
    df["rest_type"] = df["rest_type"].astype(str).str.strip()

    df["book_table"] = df.get("book_table", pd.Series("No", index=df.index)).apply(_parse_bool_yn)
    df["online_order"] = df.get("online_order", pd.Series("No", index=df.index)).apply(_parse_bool_yn)

    if "listed_type" in df.columns:
        df["listed_type"] = df["listed_type"].fillna("").astype(str).str.strip()
    else:
        df["listed_type"] = ""

    # ── Final: keep only the columns we care about ──────────────────────────
    keep_cols = [
        "name", "city", "location", "cuisines",
        "rating", "votes", "approx_cost", "budget_tier",
        "rest_type", "book_table", "online_order", "listed_type",
    ]
    df = df[[c for c in keep_cols if c in df.columns]].copy()

    # ── [7] Reset index → id column ─────────────────────────────────────────
    df = df.reset_index(drop=True)
    df.insert(0, "id", df.index)

    logger.info("Cleaning complete. Final dataset: %d rows.", len(df))
    return df


# ── Step 3: Save / Load Parquet ───────────────────────────────────────────────

def save_parquet(df: pd.DataFrame, path: Path = PARQUET_PATH) -> Path:
    """
    Persist a cleaned DataFrame as a Parquet file.
    The `cuisines` column (List[str]) is serialised as a JSON string so that
    Parquet can store it without a complex schema.
    """
    import json

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # Serialise list columns to JSON strings for Parquet compatibility
    df_save = df.copy()
    df_save["cuisines"] = df_save["cuisines"].apply(json.dumps)

    df_save.to_parquet(path, index=False)
    logger.info("Saved cleaned dataset to '%s' (%d rows).", path, len(df_save))
    return path


def load_clean(path: Path = PARQUET_PATH) -> pd.DataFrame:
    """
    Load the pre-cleaned Parquet file and deserialise list columns.
    Raises FileNotFoundError if the parquet hasn't been generated yet.
    """
    import json

    if not path.exists():
        raise FileNotFoundError(
            f"Cleaned dataset not found at '{path}'. "
            "Run `python -m src.data.loader` to generate it."
        )

    df = pd.read_parquet(path)

    # Deserialise cuisines back to List[str]
    if "cuisines" in df.columns and df["cuisines"].dtype == object:
        df["cuisines"] = df["cuisines"].apply(
            lambda v: json.loads(v) if isinstance(v, str) else v
        )

    logger.info("Loaded cleaned dataset from '%s' (%d rows).", path, len(df))
    return df


# ── Step 4: DataFrame → Pydantic models ──────────────────────────────────────

def df_to_restaurants(df: pd.DataFrame) -> List[Restaurant]:
    """Convert a (subset of a) cleaned DataFrame into a list of Restaurant models."""
    restaurants: List[Restaurant] = []
    for row in df.itertuples(index=False):
        try:
            r = Restaurant(
                id=int(getattr(row, "id", 0)),
                name=str(row.name),
                city=str(row.city),
                location=str(row.location),
                cuisines=row.cuisines if isinstance(row.cuisines, list) else [],
                rating=float(row.rating) if pd.notna(row.rating) else None,
                votes=int(row.votes),
                approx_cost=int(row.approx_cost) if pd.notna(row.approx_cost) else None,
                budget_tier=str(row.budget_tier),
                rest_type=str(row.rest_type),
                book_table=bool(row.book_table),
                online_order=bool(row.online_order),
                listed_type=str(getattr(row, "listed_type", "")),
            )
            restaurants.append(r)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Skipping row due to validation error: %s", exc)
    return restaurants


# ── Full Pipeline ─────────────────────────────────────────────────────────────

def run() -> pd.DataFrame:
    """
    Run the full Phase 1 pipeline:
      load from HuggingFace → clean → save Parquet → return DataFrame
    """
    df_raw = load_dataset()
    df_clean = clean(df_raw)
    save_parquet(df_clean)
    return df_clean


# ── CLI Entry-point ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    )
    df = run()
    print(f"\n✅ Done. {len(df)} restaurants saved to {PARQUET_PATH}")
    print("\nSample rows:")
    print(df[["name", "city", "cuisines", "rating", "budget_tier"]].head(10).to_string(index=False))
