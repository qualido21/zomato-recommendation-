"""
src/data/schema.py
──────────────────
Pydantic data model for a cleaned Zomato restaurant record.
This is the canonical shape of data throughout the pipeline.
"""

from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, field_validator


BUDGET_LOW_MAX = 400
BUDGET_HIGH_MIN = 901


def cost_to_budget_tier(cost: Optional[int]) -> str:
    """Map an integer cost-for-two into a budget tier label."""
    if cost is None:
        return "medium"          # sensible default when cost is unknown
    if cost <= BUDGET_LOW_MAX:
        return "low"
    if cost >= BUDGET_HIGH_MIN:
        return "high"
    return "medium"


class Restaurant(BaseModel):
    """
    Cleaned, normalised representation of one Zomato restaurant row.

    Attributes
    ----------
    id              : Row index from the cleaned DataFrame
    name            : Restaurant display name
    city            : Title-cased city (from listed_in(city))
    location        : Neighbourhood / area within the city
    cuisines        : List of lowercase cuisine strings
    rating          : Aggregate rating 0.0–5.0, or None if unavailable
    votes           : Number of user votes
    approx_cost     : Integer rupee cost for two people, or None
    budget_tier     : "low" | "medium" | "high"  (derived from approx_cost)
    rest_type       : Restaurant category (e.g. "Casual Dining")
    book_table      : Whether table booking is supported
    online_order    : Whether online ordering is available
    listed_type     : Zomato listing category (e.g. "Buffet", "Cafes")
    """

    id: int
    name: str
    city: str
    location: str
    cuisines: List[str]
    rating: Optional[float] = None
    votes: int = 0
    approx_cost: Optional[int] = None
    budget_tier: str = "medium"
    rest_type: str = ""
    book_table: bool = False
    online_order: bool = False
    listed_type: str = ""

    @field_validator("budget_tier")
    @classmethod
    def validate_budget_tier(cls, v: str) -> str:
        allowed = {"low", "medium", "high"}
        if v not in allowed:
            raise ValueError(f"budget_tier must be one of {allowed}, got '{v}'")
        return v

    @field_validator("rating")
    @classmethod
    def validate_rating(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and not (0.0 <= v <= 5.0):
            raise ValueError(f"rating must be between 0 and 5, got {v}")
        return v

    def to_prompt_dict(self) -> dict:
        """
        Compact dictionary for injection into the LLM prompt.
        Keeps only the fields that matter for reasoning.
        """
        return {
            "name": self.name,
            "location": f"{self.location}, {self.city}",
            "cuisines": ", ".join(self.cuisines),
            "rating": self.rating,
            "approx_cost_for_two": f"₹{self.approx_cost}" if self.approx_cost else "N/A",
            "budget_tier": self.budget_tier,
            "rest_type": self.rest_type,
            "book_table": self.book_table,
            "online_order": self.online_order,
        }
