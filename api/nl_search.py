"""
Feature 1: Natural-language product search.

Parses a query like "headphones under 3000 with good battery" into
structured filters that map onto your existing Product fields
(name/category for keywords, current_price for the range) — no schema
changes needed.
"""
from dataclasses import dataclass

from .llm_client import call_json

_SYSTEM_PROMPT = """You convert a shopper's natural-language product search into a JSON filter object.

Return ONLY a JSON object with these keys, no other text, no markdown fences:
{
  "keywords": string,       // core product terms to search by name/category, e.g. "wireless headphones"
  "category": string|null,  // a likely product category if one is clearly implied, else null
  "min_price": number|null, // minimum price in INR if the user implied one, else null
  "max_price": number|null  // maximum price in INR if the user implied one, else null
}

Rules:
- "under X" / "below X" / "less than X" -> max_price = X
- "above X" / "over X" / "at least X" -> min_price = X
- "between X and Y" -> min_price = X, max_price = Y
- Strip filler words (good, best, nice, cheap) from keywords; keep only concrete product terms.
- If no price is mentioned, both min_price and max_price must be null.
- Never invent a category that wasn't implied by the query.
"""


@dataclass
class SearchFilters:
    keywords: str
    category: str | None
    min_price: float | None
    max_price: float | None


def parse_search_query(query: str) -> SearchFilters:
    """
    Raises no exception on a malformed model response — falls back to
    using the raw query as keywords with no price/category filter, so a
    parsing hiccup degrades to a normal keyword search instead of a 500.
    """
    try:
        data = call_json(_SYSTEM_PROMPT, query)
    except ValueError:
        return SearchFilters(keywords=query, category=None, min_price=None, max_price=None)

    return SearchFilters(
        keywords=data.get("keywords") or query,
        category=data.get("category"),
        min_price=data.get("min_price"),
        max_price=data.get("max_price"),
    )