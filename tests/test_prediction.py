from datetime import datetime, timedelta

import pytest

from api.prediction import predict_price

T0 = datetime(2026, 1, 1)


def series(prices, step_days=1):
    return [(T0 + timedelta(days=i * step_days), p) for i, p in enumerate(prices)]


def test_empty_history_raises():
    with pytest.raises(ValueError):
        predict_price([])


def test_single_point_is_flat_with_low_confidence():
    r = predict_price(series([500.0]))
    assert (r.predicted_price, r.trend, r.confidence, r.basis_points) == (500.0, "flat", 0.2, 1)


def test_linear_rise_extrapolates_exactly():
    # +10/day over 3 days; 7 days past the last point (day 2) -> day 9 -> 100 + 10*9
    r = predict_price(series([100, 110, 120]), days_ahead=7)
    assert r.predicted_price == 190.0
    assert r.trend == "up"


def test_falling_prices_are_classified_down():
    assert predict_price(series([200, 190, 180, 170])).trend == "down"


def test_constant_prices_are_flat():
    r = predict_price(series([300, 300, 300, 300]))
    assert r.trend == "flat"
    assert r.predicted_price == 300.0


def test_prediction_is_never_negative():
    r = predict_price(series([100, 60, 20]), days_ahead=90)
    assert r.predicted_price == 0.0


def test_input_order_does_not_matter():
    ordered = series([100, 110, 120, 130])
    shuffled = [ordered[2], ordered[0], ordered[3], ordered[1]]
    assert predict_price(ordered) == predict_price(shuffled)


def test_identical_timestamps_do_not_crash():
    same = [(T0, 100.0), (T0, 120.0)]
    r = predict_price(same)
    assert r.predicted_price == 110.0


@pytest.mark.parametrize("n", [2, 5, 15, 30, 60])
def test_confidence_stays_between_0_and_1(n):
    r = predict_price(series([100 + (i % 7) * 3 for i in range(n)]))
    assert 0.0 <= r.confidence <= 1.0
    assert r.basis_points == n


def test_more_data_gives_higher_confidence_for_the_same_fit():
    few = predict_price(series([100 + i for i in range(5)]))
    many = predict_price(series([100 + i for i in range(40)]))
    assert many.confidence > few.confidence
