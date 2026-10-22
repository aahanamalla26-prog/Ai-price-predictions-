"""AI features: the Claude client is always mocked, so these run offline and free."""
import pytest

from api import nl_search, trend_explainer
from api.nl_search import SearchFilters, parse_search_query


def fake_json(result=None, error=None):
    def _call(system_prompt, user_message, max_tokens=300):
        if error:
            raise error
        return result
    return _call


# ---------- natural-language search: parsing ----------

def test_parse_maps_model_json_to_filters(monkeypatch):
    monkeypatch.setattr(nl_search, "call_json", fake_json(
        {"keywords": "headphones", "category": "Electronics", "min_price": None, "max_price": 3000}))
    assert parse_search_query("headphones under 3000") == SearchFilters("headphones", "Electronics", None, 3000)


def test_parse_falls_back_to_raw_query_when_model_returns_bad_json(monkeypatch):
    monkeypatch.setattr(nl_search, "call_json", fake_json(error=ValueError("not json")))
    assert parse_search_query("cheap laptop") == SearchFilters("cheap laptop", None, None, None)


@pytest.mark.parametrize("model_output", [{}, {"keywords": ""}, {"keywords": None}])
def test_parse_uses_query_when_keywords_missing_or_empty(monkeypatch, model_output):
    monkeypatch.setattr(nl_search, "call_json", fake_json(model_output))
    assert parse_search_query("sony tv").keywords == "sony tv"


# ---------- endpoints (known defects) ----------

@pytest.mark.xfail(strict=True, reason="DEF-B1: /products/search/nl calls parse_search_query(query, db) but the function takes only (query), so every request is a 500")
def test_nl_search_endpoint_returns_200(client, make_product, monkeypatch):
    make_product(name="Sony Headphones", price=2500)
    monkeypatch.setattr(nl_search, "call_json", fake_json(
        {"keywords": "headphones", "category": None, "min_price": None, "max_price": 3000}))
    assert client.get("/products/search/nl", params={"query": "headphones under 3000"}).status_code == 200


@pytest.mark.xfail(strict=True, reason="DEF-B2: /predict/explain passes a dict to explain_trend(product_name, current_price, result, days_ahead), so every request is a 500")
def test_explain_endpoint_returns_200(client, make_product, monkeypatch):
    p = make_product(price=100)
    client.post(f"/products/{p['id']}/history", params={"price": 110})
    monkeypatch.setattr(trend_explainer, "call_text", lambda *a, **k: "Price is climbing.")
    assert client.get(f"/products/{p['id']}/predict/explain").status_code == 200


def test_explain_endpoint_unknown_product_is_404(client):
    assert client.get("/products/9999/predict/explain").status_code == 404
