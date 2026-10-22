"""
Shared fixtures for the PricePulse API tests.

If DATABASE_URL is already set (as it is in the GitHub Actions workflow, which
provides Postgres) the tests run against that database. Otherwise they fall
back to a throwaway SQLite file, so `pytest` works on a laptop with no setup.
The AI features are always mocked: tests never call the Claude API.
"""
import os
import tempfile

if not os.environ.get("DATABASE_URL"):
    _tmp = tempfile.mkdtemp()
    os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/test.db"

import pytest
from fastapi.testclient import TestClient

from api import models  # noqa: F401  (registers tables)
from api.database import Base, SessionLocal, engine
from api.main import app


@pytest.fixture(autouse=True)
def clean_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture
def client():
    # raise_server_exceptions=False so a crash shows up as a 500 response,
    # which is what a real user would see.
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def make_product(client):
    def _make(name="Sony WH-1000XM5", price=26990.0, category="Electronics"):
        r = client.post("/products", json={"name": name, "current_price": price, "category": category})
        assert r.status_code == 201, r.text
        return r.json()
    return _make
