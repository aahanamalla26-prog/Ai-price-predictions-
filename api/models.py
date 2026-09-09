import enum
from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from .database import Base


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    url = Column(Text, nullable=True)
    image_url = Column(Text, nullable=True)
    category = Column(String(100), nullable=True, index=True)
    currency = Column(String(8), nullable=False, default="INR")
    current_price = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    price_history = relationship(
        "PriceHistory", back_populates="product", cascade="all, delete-orphan"
    )
    trackers = relationship(
        "TrackedItem", back_populates="product", cascade="all, delete-orphan"
    )


class PriceHistory(Base):
    __tablename__ = "price_history"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    price = Column(Float, nullable=False)
    recorded_at = Column(DateTime, default=datetime.utcnow, index=True)

    product = relationship("Product", back_populates="price_history")


class AlertStatus(str, enum.Enum):
    active = "active"
    triggered = "triggered"
    cancelled = "cancelled"


class TrackedItem(Base):
    """A user's request to be alerted when a product hits a target price."""

    __tablename__ = "tracked_items"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    email = Column(String(255), nullable=False, index=True)
    target_price = Column(Float, nullable=False)
    status = Column(Enum(AlertStatus), default=AlertStatus.active, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    product = relationship("Product", back_populates="trackers")