# 🛒 PricePulse

**Track prices. Spot the drop before it happens.**

PricePulse is a full-stack, event-driven price tracking and promo-matching platform. It watches product prices over time, predicts where they're headed, and alerts you when something you're watching hits your target.

<p align="center">
  <img src="https://img.shields.io/badge/FastAPI-009688?style=flat&logo=fastapi&logoColor=white" alt="FastAPI"/>
  <img src="https://img.shields.io/badge/Angular-DD0031?style=flat&logo=angular&logoColor=white" alt="Angular"/>
  <img src="https://img.shields.io/badge/PostgreSQL-4169E1?style=flat&logo=postgresql&logoColor=white" alt="PostgreSQL"/>
  <img src="https://img.shields.io/badge/Apache_Kafka-231F20?style=flat&logo=apachekafka&logoColor=white" alt="Kafka"/>
  <img src="https://img.shields.io/badge/Redis-DC382D?style=flat&logo=redis&logoColor=white" alt="Redis"/>
  <img src="https://img.shields.io/badge/Playwright-2EAD33?style=flat&logo=playwright&logoColor=white" alt="Playwright"/>
</p>

---

## ✨ Features

| | |
|---|---|
| 🔍 **Product Search** | Find any tracked product by name or category |
| 📈 **Price History** | See how a price has moved over the last 30, 60, or 90 days |
| 🔮 **Price Prediction** | A trend model forecasts where the price is headed next |
| 🔔 **Price Alerts** | Set a target price and get notified when a product drops to it |
| ⚡ **Event-Driven Scraping** | Playwright workers publish price updates onto Kafka in real time |
| 🧠 **Semantic Matching** | pgvector powers promo/product matching across retailers |

---

## 🏗️ Architecture

```
┌─────────────┐      ┌──────────────┐      ┌─────────────────┐
│   Angular    │◄────►│   FastAPI    │◄────►│   PostgreSQL      │
│  Frontend    │      │   Backend    │      │   + pgvector      │
└─────────────┘      └──────┬───────┘      └─────────────────┘
                             │
                      ┌──────▼───────┐      ┌─────────────────┐
                      │    Redis     │      │  Apache Kafka     │
                      │   (cache)    │      │  (price events)   │
                      └──────────────┘      └────────┬────────┘
                                                       │
                                              ┌────────▼────────┐
                                              │  Playwright      │
                                              │  Scraper Worker  │
                                              └─────────────────┘
```

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

Full interactive docs live at [`/docs`](https://ai-price-predictions.vercel.app/docs).

---

## 🚀 Getting Started

### Prerequisites
- Python 3.12+
- A PostgreSQL database ([Neon](https://neon.tech) or [Supabase](https://supabase.com) both offer free tiers)

### Backend Setup

```bash
cd backend
pip install -r requirements.txt
```

Create a `.env` file in `backend/`:

```env
DATABASE_URL=postgresql+psycopg2://user:password@host:5432/pricepulse
REDIS_URL=redis://localhost:6379/0
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
```

Seed the database with sample products and 60 days of price history:

```bash
python seed.py
```

Run the server:

```bash
uvicorn main:app --reload
```

Visit `http://127.0.0.1:8000/docs` to explore the API.

### Deploying to Vercel

This project deploys as a serverless FastAPI function. The repo root includes a `pyproject.toml` pointing Vercel at the app:

```toml
[tool.vercel]
entrypoint = "backend.main:app"
```

Add `DATABASE_URL` (and any other secrets) under **Project Settings → Environment Variables** on Vercel, then push to `main` to trigger a deploy.

---

## 🗂️ Project Structure

```
Ai-price-predictions-/
├── backend/
│   ├── main.py          # FastAPI app & routes
│   ├── models.py        # SQLAlchemy models
│   ├── schemas.py        # Pydantic schemas
│   ├── prediction.py    # Price trend predictor
│   ├── database.py      # DB session setup
│   ├── config.py         # Settings
│   └── seed.py            # Sample data loader
├── frontend/              # Angular app
├── worker/                # Playwright scraping workers
├── requirements.txt
└── pyproject.toml
```

---

## 🛣️ Roadmap

- [ ] Swap the linear-trend predictor for a proper ML model
- [ ] Email/push notifications for triggered alerts
- [ ] Browser extension for one-click tracking
- [ ] Multi-retailer price comparison

---

## 📄 License

MIT
