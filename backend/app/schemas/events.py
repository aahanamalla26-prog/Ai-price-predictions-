"""
Pydantic v2 schemas. `PriceCheckRequested` / `PriceUpdated` are the Kafka
event contracts — keep these in lockstep with worker/app/schemas if you
change a field, since the worker parses backend-published events by hand
(no shared package across services in this repo, by design, to keep the
two deployable units independent).
"""
import uuid
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class CheckStatusEnum(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class PriceCheckRequested(BaseModel):
    """Event published to `price-check-requests` when a user triggers a check."""
    model_config = ConfigDict(str_strip_whitespace=True)

    request_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    product_url: HttpUrl
    requested_at: datetime = Field(default_factory=datetime.utcnow)


class PriceUpdated(BaseModel):
    """Event published to `price-updates` by the scraper worker once a check completes."""
    model_config = ConfigDict(str_strip_whitespace=True)

    request_id: uuid.UUID
    product_url: HttpUrl
    product_title: str | None = None
    price_amount: float | None = None
    currency: str = "INR"
    in_stock: bool = True
    promo_text: str | None = None
    status: CheckStatusEnum
    error_message: str | None = None
    scraped_at: datetime = Field(default_factory=datetime.utcnow)


# --- REST API request/response models ---

class CheckPriceRequest(BaseModel):
    product_url: HttpUrl


class CheckPriceResponse(BaseModel):
    request_id: uuid.UUID
    status: CheckStatusEnum
    message: str = "Price check queued"


class PriceRecordOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    product_url: str
    product_title: str | None
    price_amount: float
    currency: str
    in_stock: bool
    promo_text: str | None
    scraped_at: datetime


class CheckStatusOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    product_url: str
    status: CheckStatusEnum
    requested_at: datetime
    completed_at: datetime | None
    error_message: str | None
