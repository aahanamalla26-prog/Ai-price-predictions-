"""
Thin wrapper around the Anthropic API for the two AI features:
- natural-language search query parsing (nl_search.py)
- price-trend plain-English explanations (trend_explainer.py)

Keeps the client setup, JSON parsing, and error handling in one place
so both features share the same code instead of duplicating it.

Setup:
    pip install anthropic
    export ANTHROPIC_API_KEY=sk-ant-...   (also add this to Vercel's
    project env vars, same place you set DATABASE_URL)
"""
import json
import os

from anthropic import Anthropic

_client: Anthropic | None = None


def get_client() -> Anthropic:
    global _client
    if _client is None:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY is not set. Add it to your environment "
                "(and to Vercel's project env vars for production)."
            )
        _client = Anthropic(api_key=api_key)
    return _client


def call_json(system_prompt: str, user_message: str, max_tokens: int = 300) -> dict:
    """
    Calls Claude with instructions to return ONLY a JSON object (no prose,
    no markdown fences) and parses the result.

    Raises ValueError if the model didn't return valid JSON, so callers
    can decide how to fall back (e.g. treat the whole query as keywords).
    """
    client = get_client()
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=max_tokens,
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}],
    )
    text = "".join(block.text for block in response.content if block.type == "text").strip()
    text = text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise ValueError(f"Model did not return valid JSON: {text!r}") from e


def call_text(system_prompt: str, user_message: str, max_tokens: int = 200) -> str:
    """Calls Claude for a plain-text response (used by the trend explainer)."""
    client = get_client()
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=max_tokens,
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}],
    )
    return "".join(block.text for block in response.content if block.type == "text").strip()