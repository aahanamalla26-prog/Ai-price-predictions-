# PricePulse – Defect Log

Found by the automated suites on 2026-10-19 against commit `72a9c7a` (backend) and the current `main` of `price-pulse-frontend`.
Each defect has a strict-`xfail` test that reproduces it. Change **Status** as you fix them.

Severity: **High** = feature unusable / data wrong · **Medium** = bad input accepted or misleading behaviour · **Low** = edge case or cosmetic.

## Backend

| ID | Title | Severity | Status | Test |
|---|---|---|---|---|
| DEF-B1 | `GET /products/search/nl` always returns 500 | High | Open (fix in patch) | `test_nl_search_endpoint_returns_200` |
| DEF-B2 | `GET /products/{id}/predict/explain` always returns 500 | High | Open (fix in patch) | `test_explain_endpoint_returns_200` |
| DEF-B3 | Product can be created with a negative price or empty name | Medium | Open (fix in patch) | `test_create_product_rejects_negative_price`, `..._empty_name` |
| DEF-B4 | Negative price accepted when recording a price point | Medium | Open (fix in patch) | `test_add_price_point_rejects_negative_price` |
| DEF-B5 | `days` parameter on price history is ignored | Medium | Open (fix in patch) | `test_history_respects_days_window` |
| DEF-B6 | `%` and `_` in search text act as wildcards | Low | Open (fix in patch) | `test_search_treats_percent_sign_literally` |
| DEF-B7 | CI cannot install the app: root `requirements.txt` lists only worker packages | High | Open (fix: `requirements-dev.txt` + new `ci.yml`) | CI run |
| DEF-B8 | `anthropic` is missing from `pyproject.toml` (what Vercel installs) but `llm_client.py` imports it at start-up | High (needs checking) | Open: verify against the live deployment | — |
| DEF-B9 | `tests/test_basic.py` was `assert True`, so CI passed with zero real tests | Medium | Fixed (replaced by real suite) | — |

### DEF-B1 – `/products/search/nl` returns 500
- **Steps:** `GET /products/search/nl?query=headphones under 3000` (Claude call mocked to return valid JSON).
- **Expected:** 200 with products matching the filters.
- **Actual:** 500. `main.py` calls `parse_search_query(query, db)` but the function is defined as `parse_search_query(query)`, so it raises `TypeError`. The filters are also never applied to the database.
- **Fix:** call `parse_search_query(query)`, then filter products by the returned keywords, category and price range.

### DEF-B2 – `/products/{id}/predict/explain` returns 500
- **Steps:** create a product with two price points, `GET /products/1/predict/explain` (Claude call mocked).
- **Expected:** 200 with prediction and explanation.
- **Actual:** 500. `main.py` passes one dict to `explain_trend`, which expects `(product_name, current_price, result, days_ahead)`: `TypeError`.
- **Fix:** `explain_trend(product.name, product.current_price, result, days_ahead)`.

### DEF-B3 / B4 – Invalid prices and names accepted
- **Steps:** `POST /products {"name": "", "current_price": -5}`; `POST /products/1/history?price=-9`.
- **Expected:** 422. **Actual:** 201. Bad data then flows into predictions.
- **Fix:** `Field(min_length=1)` on `name`, `Field(gt=0)` on prices.

### DEF-B5 – `days` ignored
- **Steps:** add a price point dated 60 days ago, `GET /products/1/history?days=7`.
- **Expected:** only points from the last 7 days. **Actual:** all points returned; the value is validated and then never used.

### DEF-B6 – LIKE wildcards not escaped
- **Steps:** `GET /products?q=%`. **Expected:** only names containing a literal `%`. **Actual:** every product.

### DEF-B7 / B8 – Dependency gaps
- Root `requirements.txt` has `aiokafka, playwright, sqlalchemy, asyncpg, redis, pydantic, pydantic-settings` and no `fastapi`, `uvicorn`, `psycopg2` or `anthropic`, so the old CI could not even import the app.
- `pyproject.toml` (used by Vercel) does not list `anthropic`, while `api/llm_client.py` runs `from anthropic import Anthropic` at import time and `main.py` imports it. If the deployed build comes from this commit the whole API would fail to start. Check the live API (`curl https://ai-price-predictions.vercel.app/health` and `.../products/search/nl?query=test`) and add `anthropic` to `pyproject.toml` if needed.

## Frontend

| ID | Title | Severity | Status | Test |
|---|---|---|---|---|
| DEF-F1 | Alert form accepts non-numeric target price ("abc") | Medium | Open (fix in patch) | `test_alert_rejects_non_numeric_target_price` |
| DEF-F2 | Alert form accepts a contact that is neither email nor phone | Medium | Open (fix in patch) | `test_alert_rejects_invalid_contact` |
| DEF-F3 | Alert form shows "you're officially locked in" but sends nothing; alert is never saved | High (misleading) | Open (needs wiring to `POST /products/{id}/track`, or label it as a demo) | `test_alert_submission_sends_a_request_to_the_backend` |
| DEF-F4 | Page scrolls sideways by 8px on a 375px phone | Low | Open (fix in patch) | `test_page_has_no_horizontal_scroll_on_phone` |

- **DEF-F4 cause:** the root element is `width: 100vw` and `<body>` keeps the browser's default 8px margin. Fix: `body { margin: 0 }`.
- **DEF-F3:** the form only calls `setSubmitted(true)`.

## Observations (not bugs, but worth knowing before an interview)
- `src/PricePulse.jsx` (the component that talks to the live API: product search, history chart, prediction, real alert POST) is **not rendered** by `App.jsx`. The deployed page shows the landing page and four dashboards driven by local, simulated data.
- The landing page and README describe a "sub-second websocket feed". The dashboards are simulated with timers; there is no WebSocket in the frontend.
