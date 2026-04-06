"""
src/filter/schemas.py
─────────────────────
Pydantic schemas for Phase 2 — Filtering & Query Engine.
"""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field

from src.data.schema import Restaurant


class UserPreferences(BaseModel):
    """Structured user preferences passed to the FilterEngine."""

    city: str
    budget_max: int = Field(
        description="Maximum budget (rupees for two people), e.g. 800",
        ge=1,
    )
    cuisines: List[str]
    min_rating: float = Field(default=3.5, ge=0.0, le=5.0)
    extra_prefs: Optional[str] = ""


class FilterResult(BaseModel):
    """Output of the FilterEngine — candidates ready for the LLM prompt builder."""

    candidates: List[Restaurant]
    total_before_limit: int
    filters_relaxed: bool
    message: Optional[str] = None
