from datetime import datetime, timedelta

import pytest

from api import models


# ---------- health ----------

def test_root_and_health(client):
    assert client.get("/").json()["status"] == "online"
    assert client.get("/health").json() == {"status": "healthy"}


# ---------- products ----------

def test_create_product_returns_201_and_seeds_history(client):
    r = client.post("/products", json={"name": "Kindle", "current_price": 13999})
    assert r.status_code == 201
    body = r.json()
    assert body["currency"] == "INR"
    history = client.get(f"/products/{body['id']}/history").json()
    assert len(history["points"]) == 1
    assert history["points"][0]["price"] == 13999


def test_create_product_missing_required_field_is_422(client):
    assert client.post("/products", json={"name": "No price"}).status_code == 422


def test_get_unknown_product_is_404(client):
    r = client.get("/products/9999")
    assert r.status_code == 404
    assert r.json()["detail"] == "Product not found"


def test_list_products_pagination_and_total(client, make_product):
    for i in range(5):
        make_product(name=f"Item {i}")
    page = client.get("/products", params={"limit": 2, "offset": 2}).json()
    assert page["total"] == 5
    assert [p["name"] for p in page["items"]] == ["Item 2", "Item 3"]


def test_list_products_search_is_case_insensitive_on_name_and_category(client, make_product):
    make_product(name="Sony Headphones", category="Electronics")
    make_product(name="Nike Shoes", category="Footwear")
    assert client.get("/products", params={"q": "sony"}).json()["total"] == 1
    assert client.get("/products", params={"q": "FOOTWEAR"}).json()["total"] == 1
    assert client.get("/products", params={"q": "nothing-matches"}).json()["total"] == 0


def test_list_products_category_filter_is_exact(client, make_product):
    make_product(name="A", category="Electronics")
    make_product(name="B", category="Electronic")
    assert client.get("/products", params={"category": "Electronics"}).json()["total"] == 1


@pytest.mark.parametrize("params", [{"limit": 0}, {"limit": 101}, {"offset": -1}])
def test_list_products_rejects_out_of_range_paging(client, params):
    assert client.get("/products", params=params).status_code == 422


# ---------- price history ----------

def test_history_unknown_product_is_404(client):
    assert client.get("/products/9999/history").status_code == 404


def test_add_price_point_updates_current_price_and_history(client, make_product):
    p = make_product(price=100)
    r = client.post(f"/products/{p['id']}/history", params={"price": 90})
    assert r.status_code == 201
    assert client.get(f"/products/{p['id']}").json()["current_price"] == 90
    assert len(client.get(f"/products/{p['id']}/history").json()["points"]) == 2


def test_add_price_point_unknown_product_is_404(client):
    assert client.post("/products/9999/history", params={"price": 10}).status_code == 404


def test_history_is_returned_oldest_first(client, make_product, db):
    p = make_product(price=100)
    now = datetime.utcnow()
    db.add_all([
        models.PriceHistory(product_id=p["id"], price=300, recorded_at=now - timedelta(days=1)),
        models.PriceHistory(product_id=p["id"], price=200, recorded_at=now - timedelta(days=5)),
    ])
    db.commit()
    prices = [pt["price"] for pt in client.get(f"/products/{p['id']}/history").json()["points"]]
    assert prices == [200, 300, 100]


@pytest.mark.parametrize("days", [0, 366])
def test_history_rejects_out_of_range_days(client, make_product, days):
    p = make_product()
    assert client.get(f"/products/{p['id']}/history", params={"days": days}).status_code == 422


# ---------- prediction ----------

def test_predict_unknown_product_is_404(client):
    assert client.get("/products/9999/predict").status_code == 404


def test_predict_uses_stored_history(client, make_product):
    p = make_product(price=100)
    for price in (110, 120):
        client.post(f"/products/{p['id']}/history", params={"price": price})
    r = client.get(f"/products/{p['id']}/predict", params={"days_ahead": 7})
    assert r.status_code == 200
    body = r.json()
    assert body["basis_points"] == 3
    assert body["trend"] == "up"
    assert body["predicted_for_days"] == 7
    assert 0 <= body["confidence"] <= 1


@pytest.mark.parametrize("days", [0, 91])
def test_predict_rejects_out_of_range_days_ahead(client, make_product, days):
    p = make_product()
    assert client.get(f"/products/{p['id']}/predict", params={"days_ahead": days}).status_code == 422


# ---------- tracking / alerts ----------

def test_track_product_happy_path(client, make_product):
    p = make_product()
    r = client.post(f"/products/{p['id']}/track", json={"email": "a@b.com", "target_price": 20000})
    assert r.status_code == 201
    assert r.json()["status"] == "active"
    listed = client.get(f"/products/{p['id']}/track").json()
    assert [t["email"] for t in listed] == ["a@b.com"]


@pytest.mark.parametrize("payload", [
    {"email": "not-an-email", "target_price": 100},
    {"email": "a@b.com", "target_price": 0},
    {"email": "a@b.com", "target_price": -5},
    {"target_price": 100},
])
def test_track_rejects_invalid_payloads(client, make_product, payload):
    p = make_product()
    assert client.post(f"/products/{p['id']}/track", json=payload).status_code == 422


def test_track_unknown_product_is_404(client):
    r = client.post("/products/9999/track", json={"email": "a@b.com", "target_price": 10})
    assert r.status_code == 404


# ---------- known defects (see docs/DEFECT_LOG.md) ----------
# strict xfail: once you fix a bug the test starts passing, pytest reports it,
# and you delete the marker.

@pytest.mark.xfail(strict=True, reason="DEF-B3: negative price accepted when creating a product")
def test_create_product_rejects_negative_price(client):
    assert client.post("/products", json={"name": "Bad", "current_price": -5}).status_code == 422


@pytest.mark.xfail(strict=True, reason="DEF-B3: empty product name accepted")
def test_create_product_rejects_empty_name(client):
    assert client.post("/products", json={"name": "", "current_price": 10}).status_code == 422


@pytest.mark.xfail(strict=True, reason="DEF-B4: negative price accepted when recording a price point")
def test_add_price_point_rejects_negative_price(client, make_product):
    p = make_product()
    assert client.post(f"/products/{p['id']}/history", params={"price": -9}).status_code == 422


@pytest.mark.xfail(strict=True, reason="DEF-B5: the `days` parameter is validated but never used to filter history")
def test_history_respects_days_window(client, make_product, db):
    p = make_product(price=100)
    db.add(models.PriceHistory(product_id=p["id"], price=50, recorded_at=datetime.utcnow() - timedelta(days=60)))
    db.commit()
    points = client.get(f"/products/{p['id']}/history", params={"days": 7}).json()["points"]
    assert [pt["price"] for pt in points] == [100]


@pytest.mark.xfail(strict=True, reason="DEF-B6: LIKE wildcards in the search term are not escaped, so q=% matches everything")
def test_search_treats_percent_sign_literally(client, make_product):
    make_product(name="Sony Headphones")
    assert client.get("/products", params={"q": "%"}).json()["total"] == 0
