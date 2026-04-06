"""
src/api/routes/metadata.py
───────────────────────────
GET /locations, GET /cuisines, GET /health
"""

from __future__ import annotations

from typing import List

from fastapi import APIRouter
from pydantic import BaseModel

from src.api.dependencies import get_state

router = APIRouter()


class LocationsResponse(BaseModel):
    cities: List[str]


class CuisinesResponse(BaseModel):
    cuisines: List[str]


class HealthResponse(BaseModel):
    status: str
    dataset_loaded: bool
    llm_provider: str


@router.get("/locations", response_model=LocationsResponse)
def get_locations() -> LocationsResponse:
    """Return all distinct cities available in the dataset."""
    state = get_state()
    return LocationsResponse(cities=state.engine.available_cities())


@router.get("/cuisines", response_model=CuisinesResponse)
def get_cuisines() -> CuisinesResponse:
    """Return all distinct cuisines available in the dataset."""
    state = get_state()
    return CuisinesResponse(cuisines=state.engine.available_cuisines())


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Liveness check — confirms the dataset is loaded and the LLM provider in use."""
    try:
        state = get_state()
        return HealthResponse(
            status="ok",
            dataset_loaded=True,
            llm_provider=state.llm_provider,
        )
    except RuntimeError:
        return HealthResponse(status="starting", dataset_loaded=False, llm_provider="unknown")
