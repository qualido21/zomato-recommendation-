"""
src/llm/parser.py
─────────────────
Parses the raw LLM text response into a validated list of Recommendation objects.

Fallback chain:
  1. Direct json.loads()
  2. Strip markdown fences → json.loads()
  3. json-repair (best-effort fix of malformed JSON)
  4. On total failure → raise LLMParseError (caller falls back to filter results)
"""

from __future__ import annotations

import json
import re
from typing import List

from pydantic import BaseModel, ValidationError


class Recommendation(BaseModel):
    """A single ranked restaurant recommendation returned by the LLM."""

    rank: int
    name: str
    cuisine: str
    rating: float
    estimated_cost: str
    explanation: str


class LLMParseError(ValueError):
    """Raised when the LLM response cannot be parsed into Recommendation objects."""


# ── Helpers ───────────────────────────────────────────────────────────────────

_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)


def _strip_fences(text: str) -> str:
    """Remove ```json ... ``` markdown fences if present."""
    match = _FENCE_RE.search(text)
    if match:
        return match.group(1)
    return text.strip()


def _try_json_repair(text: str) -> list:
    """
    Attempt best-effort repair of malformed JSON using the json-repair library.
    Falls back to raising ValueError if the library is unavailable or repair fails.
    """
    try:
        from json_repair import repair_json  # type: ignore
        repaired = repair_json(text)
        return json.loads(repaired)
    except Exception as exc:
        raise ValueError(f"json-repair could not fix the response: {exc}") from exc


def _validate_items(raw_list: list) -> List[Recommendation]:
    """Validate each dict in *raw_list* against the Recommendation schema."""
    results: List[Recommendation] = []
    for item in raw_list:
        try:
            results.append(Recommendation.model_validate(item))
        except ValidationError as exc:
            raise LLMParseError(f"Recommendation item failed validation: {exc}") from exc
    if not results:
        raise LLMParseError("LLM returned an empty recommendations list.")
    return results


# ── Public API ────────────────────────────────────────────────────────────────

def parse_response(raw: str) -> List[Recommendation]:
    """
    Parse a raw LLM string into a sorted list of Recommendation objects.

    Steps
    -----
    1. Direct json.loads()
    2. Strip markdown fences → json.loads()
    3. json-repair → json.loads()
    4. Validate each item against Recommendation schema
    5. Sort by rank ASC

    Raises
    ------
    LLMParseError
        If all parsing attempts fail or schema validation fails.
    """
    text = raw.strip()

    # Attempt 1 — direct parse
    parsed = None
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        pass

    # Attempt 2 — strip markdown fences
    if parsed is None:
        stripped = _strip_fences(text)
        try:
            parsed = json.loads(stripped)
        except json.JSONDecodeError:
            pass

    # Attempt 3 — json-repair
    if parsed is None:
        try:
            parsed = _try_json_repair(_strip_fences(text))
        except ValueError as exc:
            raise LLMParseError(
                f"Could not parse LLM response after all fallback attempts.\n"
                f"Raw response (first 500 chars): {text[:500]}\n"
                f"Repair error: {exc}"
            ) from exc

    if not isinstance(parsed, list):
        raise LLMParseError(
            f"Expected a JSON array from the LLM, got {type(parsed).__name__}."
        )

    recommendations = _validate_items(parsed)
    return sorted(recommendations, key=lambda r: r.rank)
