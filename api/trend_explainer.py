"""
Feature 2: Price-trend explainer.

Turns your existing predict_price() output (numbers only) into a short,
plain-English explanation a non-technical user can read on the product
page. The OLS model still does the actual prediction — this only
explains the result, so predict_price() in prediction.py is unchanged.
"""
from .llm_client import call_text
from .prediction import PredictionResult

_SYSTEM_PROMPT = """You explain a price-trend prediction to a shopper in 1-2 plain sentences.

Be concrete and specific to the numbers given. Do not add disclaimers,
do not mention "AI" or "model", do not use technical terms like
"regression" or "confidence interval" or "basis points". Write like a
helpful friend summarizing what the price is doing and whether it's
worth waiting.
"""


def explain_trend(
    product_name: str,
    current_price: float,
    result: PredictionResult,
    days_ahead: int,
) -> str:
    user_message = (
        f"Product: {product_name}\n"
        f"Current price: {current_price}\n"
        f"Predicted price in {days_ahead} days: {result.predicted_price}\n"
        f"Trend direction: {result.trend}\n"
        f"Confidence (0-1): {result.confidence}\n"
        f"Number of price points used: {result.basis_points}\n"
    )
    return call_text(_SYSTEM_PROMPT, user_message)