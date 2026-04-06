"""
src/api/dependencies.py
────────────────────────
Shared application state — loaded once at startup, injected into routes.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from src.filter.engine import FilterEngine
from src.llm.adapter import LLMAdapter, build_adapter


@dataclass
class AppState:
    engine: FilterEngine
    adapter: LLMAdapter
    llm_provider: str


# Singleton — populated during lifespan startup
_state: AppState | None = None


def get_state() -> AppState:
    if _state is None:
        raise RuntimeError("AppState not initialised — has the app started up?")
    return _state


def init_state(parquet_path: Path | str, provider: str | None = None) -> AppState:
    """Load the dataset, build the engine and adapter, store in module-level singleton."""
    global _state
    df = pd.read_parquet(parquet_path)

    # Deserialise cuisines if stored as JSON strings (matches loader output)
    if df["cuisines"].dtype == object and isinstance(df["cuisines"].iloc[0], str):
        df["cuisines"] = df["cuisines"].apply(json.loads)

    engine = FilterEngine(df)
    adapter = build_adapter(provider)
    _state = AppState(
        engine=engine,
        adapter=adapter,
        llm_provider=(provider or os.getenv("LLM_PROVIDER", "groq")).lower(),
    )
    return _state
