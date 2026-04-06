"""
src/llm/prompt_builder.py
─────────────────────────
Builds the system + user prompts sent to the LLM.

Usage
-----
builder = PromptBuilder()
system_prompt, user_prompt = builder.build(prefs, candidates)
"""

from __future__ import annotations

import json
from typing import List, Tuple

from src.data.schema import Restaurant
from src.filter.schemas import UserPreferences

_SYSTEM_PROMPT = """\
You are an expert restaurant recommendation assistant for India.
Your job is to rank the provided restaurants based on how well they
match the user's preferences, and explain your choices clearly.
Always respond in valid JSON only — no markdown, no extra text.\
"""

_USER_PROMPT_TEMPLATE = """\
User Preferences:
- Location: {city}
- Cuisine(s): {cuisines}
- Max Budget: ₹{budget_max} for two people
- Minimum Rating: {min_rating} / 5
- Additional Preferences: {extra_prefs}

Candidate Restaurants (choose and rank your TOP 5):
{candidates_json}

Respond ONLY with a JSON array in this exact format:
[
  {{
    "rank": 1,
    "name": "Restaurant Name",
    "cuisine": "Primary Cuisine",
    "rating": 4.3,
    "estimated_cost": "₹600 for two",
    "explanation": "2-3 sentence explanation of why this fits the user's needs"
  }}
]\
"""


class PromptBuilder:
    """Constructs LLM prompts from structured preferences and candidate restaurants."""

    def build(
        self,
        prefs: UserPreferences,
        candidates: List[Restaurant],
    ) -> Tuple[str, str]:
        """
        Return ``(system_prompt, user_prompt)`` ready to pass to an LLMAdapter.

        Parameters
        ----------
        prefs      : UserPreferences — the structured query from the user
        candidates : List[Restaurant] — shortlist from the FilterEngine
        """
        candidates_json = json.dumps(
            [r.to_prompt_dict() for r in candidates], indent=2, ensure_ascii=False
        )

        user_prompt = _USER_PROMPT_TEMPLATE.format(
            city=prefs.city,
            cuisines=", ".join(prefs.cuisines) if prefs.cuisines else "Any",
            budget_max=prefs.budget_max,
            min_rating=prefs.min_rating,
            extra_prefs=prefs.extra_prefs or "None",
            candidates_json=candidates_json,
        )

        return _SYSTEM_PROMPT, user_prompt
