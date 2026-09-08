"""
Core ORM models. `PriceRecord` is the timestamped history table populated by
the persistence consumer. `PriceCheckRequest` tracks the lifecycle of each
user-triggered check (pending -> in_progress -> completed/failed) so the
frontend can poll or subscribe to status. `PromoRule` stores bank/promo
discount text alongside a pgvector embedding for similarity search.
"""
import enum
import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, Enum, ForeignKey, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class CheckStatus(str, enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class PriceCheckRequest(Base):
    __tablename__ = "price_check_requests"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_url: Mapped[str] = mapped_column(String(2048), nullable=False, index=True)
    status: Mapped[CheckStatus] = mapped_column(
        Enum(CheckStatus, name="check_status"), default=CheckStatus.PENDING, nullable=False
    )
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    price_records: Mapped[list["PriceRecord"]] = relationship(back_populates="check_request")


class PriceRecord(Base):
    __tablename__ = "price_records"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    check_request_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("price_check_requests.id"), nullable=True
    )
    product_url: Mapped[str] = mapped_column(String(2048), nullable=False, index=True)
    product_title: Mapped[str | None] = mapped_column(String(512), nullable=True)
    price_amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(8), default="INR", nullable=False)
    in_stock: Mapped[bool] = mapped_column(default=True, nullable=False)
    promo_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    scraped_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

    check_request: Mapped["PriceCheckRequest"] = relationship(back_populates="price_records")


class PromoRule(Base):
    """
    Bank/card promo rules with a vector embedding of their description, so
    the promo-parsing service can retrieve the closest matching rule(s) for
    scraped promo text via cosine similarity (pgvector <=> operator).
    """
    __tablename__ = "promo_rules"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bank_name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    discount_percent: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    max_discount_amount: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    # all-MiniLM-L6-v2 / OpenAI-small-style embeddings are commonly 384 or
    # 1536 dims; 384 keeps the index compact for a local sentence-transformer.
    embedding: Mapped[list[float]] = mapped_column(Vector(384), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
