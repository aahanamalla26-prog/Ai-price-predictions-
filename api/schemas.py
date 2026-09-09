from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


# ---------- Products ----------

class ProductCreate(BaseModel):
    name: str
    url: str | None = None
    image_url: str | None = None
    category: str | None = None
    currency: str = "INR"
    current_price: float


class ProductOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    url: str | None
    image_url: str | None
    category: str | None
    currency: str
    current_price: float
    updated_at: datetime


class ProductListOut(BaseModel):
    total: int
    items: list[ProductOut]


# ---------- Price history ----------

class PricePoint(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    price: float
    recorded_at: datetime


class PriceHistoryOut(BaseModel):
    product_id: int
    points: list[PricePoint]


# ---------- Prediction ----------

class PredictionOut(BaseModel):
    product_id: int
    current_price: float
    predicted_price: float
    predicted_for_days: int
    trend: str  # "up" | "down" | "flat"
    confidence: float  # 0-1, rough heuristic based on data volume + fit
    basis_points: int  # how many historical points the prediction used


# ---------- Tracking / alerts ----------

class TrackRequest(BaseModel):
    email: EmailStr
    target_price: float = Field(gt=0)


class TrackOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    email: EmailStr
    target_price: float
    status: str
    created_at: datetime
