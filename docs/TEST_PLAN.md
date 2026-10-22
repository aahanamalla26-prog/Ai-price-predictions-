# PricePulse – Test Plan

**Scope:** PricePulse backend API (FastAPI + SQLAlchemy), its two Claude-powered features, and the React frontend.
**Last updated:** 2026-10-19

## 1. Objectives
- Confirm every API endpoint does what its acceptance criteria say, including invalid input and missing data.
- Confirm the price-prediction maths is correct on known data.
- Measure how reliably the natural-language search turns a shopper's sentence into correct filters.
- Confirm the main frontend journeys work in a real browser, on desktop and phone width.
- Catch regressions automatically on every push (GitHub Actions).

## 2. In scope / out of scope
| In scope | Out of scope (for now) |
|---|---|
| REST API: products, price history, prediction, tracking | Kafka/Redis worker pipeline (`worker/`) |
| `predict_price` (linear regression) | Email delivery of price alerts |
| Natural-language search and trend explainer (model mocked in tests, scored separately in the evaluation) | Load / security / accessibility testing |
| Frontend: landing page, 4 dashboards, alert form | Cross-browser (only Chromium) |

## 3. Test levels and tools
| Level | What | Tool | Where |
|---|---|---|---|
| Unit | `predict_price`, `parse_search_query` | pytest | `tests/test_prediction.py`, `tests/test_ai_features.py` |
| API / integration | Every endpoint against a real database (SQLite locally, Postgres in CI) | pytest + FastAPI TestClient | `tests/test_api.py` |
| AI quality evaluation | 30 shopper queries scored against expected filters | `evals/nl_search_eval.py` | `evals/` |
| End-to-end UI | Real Chromium against the Vite dev server | pytest-playwright | `e2e/` (frontend repo) |
| Regression | All of the above on every push and PR | GitHub Actions | `.github/workflows/` |

## 4. Acceptance criteria (what "correct" means)
| ID | Feature | Acceptance criteria |
|---|---|---|
| AC-1 | Create product | Valid payload returns 201 and seeds one history point. Missing fields return 422. **Name must be non-empty and price greater than 0.** |
| AC-2 | List / search products | `total` counts all matches, `limit` 1-100, `offset` ≥ 0, search is case-insensitive on name and category, category filter is exact. Search text is matched literally. |
| AC-3 | Price history | Oldest first. Unknown product returns 404. **`days` limits how far back points go.** |
| AC-4 | Record price point | Updates `current_price` and adds a history point. **Price must be greater than 0.** |
| AC-5 | Prediction | Known linear data extrapolates exactly. Never negative. Confidence between 0 and 1. `days_ahead` 1-90. |
| AC-6 | Price alert | Valid email and target price > 0 returns 201 and status `active`. Invalid email or price returns 422. |
| AC-7 | NL search | Model reply is parsed into filters. If the reply is not valid JSON the search falls back to plain keywords instead of failing. Endpoint returns 200 with matching products. |
| AC-8 | Trend explainer | Returns the numeric prediction plus a plain-English explanation. Unknown product returns 404. |
| AC-9 | Frontend alert form | Requires a valid email or phone and a positive numeric price; shows confirmation only on valid input; sends the alert to the backend. |
| AC-10 | Frontend layout | No horizontal scroll at 375px width. |

## 5. Test data
- Tests create their own products through the API and reset the database before every test, so they can run in any order.
- The Claude client is replaced with a stub in every automated test. No API key is needed and no money is spent.
- The AI evaluation uses `evals/nl_search_cases.json` (30 queries: price phrases, filler words, paraphrases, "3k"/"lakh", Hinglish, an ambiguous query, a prompt-injection attempt).

## 6. Regression strategy
Everything above runs on each push and pull request. Known bugs are written as strict `xfail` tests: the build stays green while a bug is open, and turns red the moment someone fixes it without removing the marker, so no fixed bug stays hidden.

## 7. Entry and exit criteria
- **Entry:** code builds, database reachable.
- **Exit / release-ready:** all non-xfail tests pass; no open High-severity defect; AI search pass rate reviewed and any failures understood; frontend e2e suite green.

## 8. Risks
| Risk | Mitigation |
|---|---|
| Claude output changes between runs | Evaluation can be repeated with `--runs N` to see drift |
| Tests pass on SQLite but behave differently on Postgres | CI runs the same suite on Postgres |
| Live deployment differs from the repo | Smoke-test the live API after each deploy (`/health`, `/products`, `/products/search/nl`) |

## 9. How to run
```bash
# backend
pip install -r requirements-dev.txt
pytest -q                                   # unit + API tests
python -m evals.nl_search_eval              # AI evaluation (needs ANTHROPIC_API_KEY)
python -m evals.nl_search_eval --dry-run    # harness self-check, no key needed

# frontend
pip install pytest pytest-playwright && playwright install chromium
pytest e2e
```

## 10. Results – 2026-10-19 (before fixes)
| Suite | Result |
|---|---|
| Backend unit + API tests | 46 passed, 7 known-defect tests (xfail) |
| Frontend Playwright | 15 passed, 4 known-defect tests (xfail) |
| AI search evaluation (real model) | *run it and paste your number here* |
