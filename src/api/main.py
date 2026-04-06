"""
src/api/main.py
────────────────
FastAPI application entry point.

Startup (lifespan):
  - Load zomato_clean.parquet into memory
  - Initialise FilterEngine
  - Initialise LLMAdapter from LLM_PROVIDER env var
  - Register all routes

Run locally:
  uvicorn src.api.main:app --reload --port 8000
"""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.dependencies import init_state
from src.api.routes import metadata, recommend

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(levelname)s — %(name)s — %(message)s")
logger = logging.getLogger(__name__)

# ── Path to the cleaned dataset ───────────────────────────────────────────────
_PARQUET_PATH = Path(__file__).resolve().parents[2] / "data" / "zomato_clean.parquet"


# ── Lifespan ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up — loading dataset from %s", _PARQUET_PATH)
    init_state(parquet_path=_PARQUET_PATH)
    logger.info("Dataset loaded. LLM provider: %s", os.getenv("LLM_PROVIDER", "groq"))
    yield
    logger.info("Shutting down.")


# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Zomato AI Restaurant Recommender",
    description="AI-powered restaurant recommendations using Groq LLM + Zomato dataset.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow the Streamlit / Next.js frontend origins
_origins = [
    o.strip()
    for o in os.getenv("API_CORS_ORIGINS", "http://localhost:3000,http://localhost:8501").split(",")
    if o.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routes ────────────────────────────────────────────────────────────────────

app.include_router(recommend.router, tags=["Recommendations"])
app.include_router(metadata.router, tags=["Metadata"])
