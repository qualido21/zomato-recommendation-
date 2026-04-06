"""
src/api/routes/recommend.py
────────────────────────────
POST /recommend — full recommendation pipeline.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Optional

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.api.dependencies import get_state
from src.filter.engine import CityNotFoundError
from src.filter.schemas import UserPreferences
from src.llm.parser import LLMParseError, Recommendation, parse_response
from src.llm.prompt_builder import PromptBuilder

logger = logging.getLogger(__name__)
router = APIRouter()
_builder = PromptBuilder()


# ── Response schema ───────────────────────────────────────────────────────────

class RecommendResponse(BaseModel):
    status: str
    query: Dict[str, Any]
    total_candidates: int
    filters_relaxed: bool
    llm_used: bool
    message: Optional[str] = None
    recommendations: List[Recommendation]


# ── Endpoint ──────────────────────────────────────────────────────────────────

@router.post("/recommend", response_model=RecommendResponse)
async def recommend(prefs: UserPreferences) -> RecommendResponse:
    """
    Run the full recommendation pipeline:
      1. Filter candidate restaurants from the dataset
      2. Build LLM prompt from candidates
      3. Call the LLM adapter
      4. Parse and return ranked recommendations

    Fallback: if the LLM call or parse fails, return the top-5 filter
    results with no AI explanation (status = "fallback").
    """
    state = get_state()

    # ── Step 1: Filter ────────────────────────────────────────────────────────
    try:
        filter_result = state.engine.run(prefs)
    except CityNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    if not filter_result.candidates:
        raise HTTPException(
            status_code=404,
            detail=f"No restaurants found in '{prefs.city}' matching the given filters.",
        )

    # ── Step 2-3: LLM ─────────────────────────────────────────────────────────
    llm_used = True
    recommendations: List[Recommendation] = []
    status = "success"
    llm_message: str | None = filter_result.message

    try:
        system_prompt, user_prompt = _builder.build(prefs, filter_result.candidates)
        raw = await state.adapter.complete(system_prompt, user_prompt)
        recommendations = parse_response(raw)
    except (
        LLMParseError,
        httpx.HTTPStatusError,
        httpx.TimeoutException,
        asyncio.TimeoutError,
    ) as exc:
        logger.warning("LLM call/parse failed, using filter fallback. Error: %s", exc)
        llm_used = False
        status = "fallback"
        llm_message = "LLM unavailable — showing top results from filter engine."
        recommendations = [
            Recommendation(
                rank=i + 1,
                name=r.name,
                cuisine=", ".join(r.cuisines),
                rating=r.rating or 0.0,
                estimated_cost=f"₹{r.approx_cost} for two" if r.approx_cost else "N/A",
                explanation="",
            )
            for i, r in enumerate(filter_result.candidates[:5])
        ]

    return RecommendResponse(
        status=status,
        query=prefs.model_dump(),
        total_candidates=filter_result.total_before_limit,
        filters_relaxed=filter_result.filters_relaxed,
        llm_used=llm_used,
        message=llm_message,
        recommendations=recommendations,
    )
