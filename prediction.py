"""
Minimal price-trend predictor with zero extra dependencies.

This is intentionally simple (ordinary least-squares linear regression,
implemented by hand) so it works today with only what's already in
requirements.txt. When you're ready for a real model, swap the body of
`predict_price` for a scikit-learn / statsmodels forecast and keep the
same PredictionResult shape so the API and frontend don't need to change.
"""
from dataclasses import dataclass
from datetime import datetime


@dataclass
class PredictionResult:
    predicted_price: float
    trend: str  # "up" | "down" | "flat"
    confidence: float
    basis_points: int


def _linear_regression(xs: list[float], ys: list[float]) -> tuple[float, float]:
    """Returns (slope, intercept) for the best-fit line through (xs, ys)."""
    n = len(xs)
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    num = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    den = sum((x - mean_x) ** 2 for x in xs)
    if den == 0:
        return 0.0, mean_y
    slope = num / den
    intercept = mean_y - slope * mean_x
    return slope, intercept


def predict_price(
    history: list[tuple[datetime, float]],
    days_ahead: int = 7,
) -> PredictionResult:
    """
    history: list of (recorded_at, price) tuples, any order, at least 1 point.
    """
    if not history:
        raise ValueError("Cannot predict with no price history")

    history = sorted(history, key=lambda p: p[0])
    n = len(history)

    if n == 1:
        price = history[0][1]
        return PredictionResult(
            predicted_price=round(price, 2),
            trend="flat",
            confidence=0.2,
            basis_points=1,
        )

    t0 = history[0][0]
    xs = [(t - t0).total_seconds() / 86400.0 for t, _ in history]  # days since first point
    ys = [p for _, p in history]

    slope, intercept = _linear_regression(xs, ys)
    target_x = xs[-1] + days_ahead
    predicted = intercept + slope * target_x
    predicted = max(predicted, 0.0)

    # Trend classification: ignore noise smaller than ~0.5% of current price per day
    current_price = ys[-1]
    threshold = max(current_price * 0.001, 0.01)
    if slope > threshold:
        trend = "up"
    elif slope < -threshold:
        trend = "down"
    else:
        trend = "flat"

    # Confidence heuristic: more points + tighter fit to the line = higher confidence.
    mean_y = sum(ys) / n
    ss_tot = sum((y - mean_y) ** 2 for y in ys)
    ss_res = sum((y - (intercept + slope * x)) ** 2 for x, y in zip(xs, ys))
    r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0.0
    data_volume_factor = min(n / 30, 1.0)  # ramps up to 1.0 at 30+ data points
    confidence = max(0.0, min(1.0, 0.5 * r_squared + 0.5 * data_volume_factor))

    return PredictionResult(
        predicted_price=round(predicted, 2),
        trend=trend,
        confidence=round(confidence, 2),
        basis_points=n,
    )
