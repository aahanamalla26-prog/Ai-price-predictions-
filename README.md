# 🛒 PricePulse

**Track prices. Spot the drop before it happens.**

PricePulse is a full-stack price tracking and forecasting platform. It watches product prices over time, predicts where they're headed next, and lets you set alerts for when something hits your target price.

<p align="center">
  <img src="https://img.shields.io/badge/FastAPI-009688?style=flat&logo=fastapi&logoColor=white" alt="FastAPI"/>
  <img src="https://img.shields.io/badge/React-61DAFB?style=flat&logo=react&logoColor=black" alt="React"/>
  <img src="https://img.shields.io/badge/PostgreSQL-4169E1?style=flat&logo=postgresql&logoColor=white" alt="PostgreSQL"/>
  <img src="https://img.shields.io/badge/Vercel-000000?style=flat&logo=vercel&logoColor=white" alt="Vercel"/>
</p>

**🔗 Live API:** [ai-price-predictions.vercel.app](https://ai-price-predictions.vercel.app) · **📄 Docs:** [/docs](https://ai-price-predictions.vercel.app/docs)

---

## ✨ Features (implemented)

| | |
|---|---|
| 🔍 **Product Search** | Find tracked products by name or category |
| 📈 **Price History** | See how a price has moved over the last 30–90 days |
| 🔮 **Price Prediction** | A trend model forecasts where the price is headed next |
| 🔔 **Price Alerts** | Set a target price and get flagged when a product drops to it |
| 💻 **Interactive Frontend** | Search, chart, predict, and track — all in one page |

---

## 🏗️ Architecture (current)

```
┌──────────────────┐        ┌──────────────────┐        ┌──────────────────┐
│  React Frontend    │◄─────►│  FastAPI Backend    │◄─────►│  PostgreSQL (Neon) │
│  (Vite, deployed    │        │  (deployed on        │        │                    │
│   on Vercel)         │        │   Vercel serverless) │        │                    │
└──────────────────┘        └──────────────────┘        └──────────────────┘
```

The backend is a single FastAPI app deployed as a Vercel serverless function. The frontend is a separate static React/Vite build, also on Vercel, calling the backend's public API.

---

## 🔌 API Reference

Base URL: `https://ai-price-predictions.vercel.app`

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Health check |
| `GET` | `/products?q=&category=&limit=&offset=` | Search / list products |
| `POST` | `/products` | Add a new product |
| `GET` | `/products/{id}` | Get product details |
| `GET` | `/products/{id}/history?days=` | Get price history |
| `POST` | `/products/{id}/history` | Record a new price observation |
| `GET` | `/products/{id}/predict?days_ahead=` | Get a price trend prediction |
| `POST` | `/products/{id}/track` | Set a price-drop alert |
| `GET` | `/products/{id}/track` | List alerts on a product |

Full interactive docs (Swagger UI) live at [`/docs`](https://ai-price-predictions.vercel.app/docs).

The prediction endpoint uses a dependency-free ordinary-least-squares trend model — no external ML library required. See `api/prediction.py`.

---

## 🚀 Getting Started

### Backend

```bash
cd api
pip install -r requirements.txt
```

Create a `.env` file in `api/`:

```env
DATABASE_URL=postgresql+psycopg2://user:password@host:5432/pricepulse
```

Seed the database with sample products and price history, then run the server:

```bash
python seed.py
uvicorn main:app --reload
```

Visit `http://127.0.0.1:8000/docs` to explore the API.

### Frontend

```bash
cd pricepulse-frontend
npm install
npm run dev
```

The frontend probes the live API on load and automatically falls back to demo data if it can't reach it — so it always renders something usable.

### Deploying

Both the backend and frontend deploy independently on Vercel.

The backend's `pyproject.toml` tells Vercel where the FastAPI app lives:

```toml
[tool.vercel]
entrypoint = "api.main:app"
```

Set `DATABASE_URL` under the backend project's **Settings → Environment Variables** on Vercel.

---

## 🗂️ Project Structure

```
Ai-price-predictions-/
├── api/
│   ├── main.py          # FastAPI app & routes
│   ├── models.py        # SQLAlchemy models
│   ├── schemas.py        # Pydantic schemas
│   ├── prediction.py    # Price trend predictor
│   ├── database.py      # DB session setup
│   ├── config.py         # Settings
│   └── seed.py            # Sample data loader
├── pyproject.toml        # Vercel entrypoint config
└── requirements.txt
```

The frontend lives in a separate repository (`pricepulse-frontend`), built with Vite + React + Recharts.

---

## 🛣️ Roadmap

The original vision for this project was a larger event-driven system. These pieces are **not built yet**:

- [ ] Event-driven scraping with Playwright workers publishing to Kafka
- [ ] Angular admin/scraper dashboard
- [ ] Semantic promo/product matching via pgvector
- [ ] Redis caching layer
- [ ] Swap the linear-trend predictor for a proper ML forecasting model
- [ ] Email delivery for triggered price alerts (currently stored, not sent)
- [ ] Multi-retailer price comparison

---

## 📄 License

MIT
