from datetime import datetime

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import or_
from sqlalchemy.orm import Session

import models
import schemas
from config import settings
from database import Base, engine, get_db
from prediction import predict_price

# Creates tables if they don't exist yet. Fine for early-stage dev;
# switch to Alembic migrations once the schema stabilizes.
Base.metadata.create_all(bind=engine)

app = FastAPI(title="PricePulse API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {"status": "online", "message": "PricePulse Backend API is running"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}


# ---------- Products ----------

@app.get("/products", response_model=schemas.ProductListOut)
def list_products(
    q: str | None = Query(None, description="Search by product name or category"),
    category: str | None = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    query = db.query(models.Product)
    if q:
        like = f"%{q}%"
        query = query.filter(
            or_(models.Product.name.ilike(like), models.Product.category.ilike(like))
        )
    if category:
        query = query.filter(models.Product.category == category)

    total = query.count()
    items = query.order_by(models.Product.name).offset(offset).limit(limit).all()
    return schemas.ProductListOut(total=total, items=items)


@app.post("/products", response_model=schemas.ProductOut, status_code=201)
def create_product(payload: schemas.ProductCreate, db: Session = Depends(get_db)):
    product = models.Product(**payload.model_dump())
    db.add(product)
    db.commit()
    db.refresh(product)

    # Seed the first price-history point so predictions have something to work with.
    db.add(models.PriceHistory(product_id=product.id, price=product.current_price))
    db.commit()
    return product


@app.get("/products/{product_id}", response_model=schemas.ProductOut)
def get_product(product_id: int, db: Session = Depends(get_db)):
    product = db.get(models.Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


# ---------- Price history ----------

@app.get("/products/{product_id}/history", response_model=schemas.PriceHistoryOut)
def get_price_history(
    product_id: int,
    days: int = Query(90, ge=1, le=365),
    db: Session = Depends(get_db),
):
    product = db.get(models.Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    points = (
        db.query(models.PriceHistory)
        .filter(models.PriceHistory.product_id == product_id)
        .order_by(models.PriceHistory.recorded_at)
        .all()
    )
    return schemas.PriceHistoryOut(product_id=product_id, points=points)


@app.post("/products/{product_id}/history", response_model=schemas.PricePoint, status_code=201)
def add_price_point(product_id: int, price: float, db: Session = Depends(get_db)):
    """Record a new price observation (called by your scraper/worker)."""
    product = db.get(models.Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    point = models.PriceHistory(product_id=product_id, price=price)
    db.add(point)
    product.current_price = price
    product.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(point)
    return point


# ---------- Prediction ----------

@app.get("/products/{product_id}/predict", response_model=schemas.PredictionOut)
def predict(
    product_id: int,
    days_ahead: int = Query(7, ge=1, le=90),
    db: Session = Depends(get_db),
):
    product = db.get(models.Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    history = (
        db.query(models.PriceHistory.recorded_at, models.PriceHistory.price)
        .filter(models.PriceHistory.product_id == product_id)
        .all()
    )
    if not history:
        raise HTTPException(status_code=422, detail="No price history to predict from yet")

    result = predict_price([(h.recorded_at, h.price) for h in history], days_ahead=days_ahead)

    return schemas.PredictionOut(
        product_id=product_id,
        current_price=product.current_price,
        predicted_price=result.predicted_price,
        predicted_for_days=days_ahead,
        trend=result.trend,
        confidence=result.confidence,
        basis_points=result.basis_points,
    )


# ---------- Tracking / alerts ----------

@app.post("/products/{product_id}/track", response_model=schemas.TrackOut, status_code=201)
def track_product(product_id: int, payload: schemas.TrackRequest, db: Session = Depends(get_db)):
    product = db.get(models.Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    tracker = models.TrackedItem(
        product_id=product_id,
        email=payload.email,
        target_price=payload.target_price,
    )
    db.add(tracker)
    db.commit()
    db.refresh(tracker)
    return tracker


@app.get("/products/{product_id}/track", response_model=list[schemas.TrackOut])
def list_trackers(product_id: int, db: Session = Depends(get_db)):
    return (
        db.query(models.TrackedItem)
        .filter(models.TrackedItem.product_id == product_id)
        .order_by(models.TrackedItem.created_at.desc())
        .all()
    )
