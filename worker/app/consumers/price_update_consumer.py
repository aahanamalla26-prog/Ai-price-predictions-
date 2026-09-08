"""
Second consumer group on `price-updates`. Persists each event as a
PriceRecord row, updates the check request's status, refreshes the Redis
"latest price" cache, and publishes the raw event on the Redis pub/sub
channel the FastAPI SSE endpoint is subscribed to.

Runs as its own consumer group so it processes every message independently
of the scraper consumer group's offsets — standard Kafka fan-out pattern.
"""
import json
import logging
import uuid
from datetime import datetime

from aiokafka import AIOKafkaConsumer
from redis.asyncio import Redis, from_url
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.core.kafka_clients import make_consumer

logger = logging.getLogger("pricepulse.worker.price_update_consumer")
settings = get_settings()

PRICE_UPDATES_CHANNEL = "pricepulse:price-updates"

# Local, worker-owned copies of the ORM base/models to avoid a cross-service
# import of the backend package (backend and worker are independently
# deployable images with their own dependency sets).
from sqlalchemy import DateTime, Enum, ForeignKey, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
import enum


class Base(DeclarativeBase):
    pass


class CheckStatus(str, enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class PriceCheckRequest(Base):
    __tablename__ = "price_check_requests"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    product_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    status: Mapped[CheckStatus] = mapped_column(Enum(CheckStatus, name="check_status"), nullable=False)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)


class PriceRecord(Base):
    __tablename__ = "price_records"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    check_request_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("price_check_requests.id"), nullable=True
    )
    product_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    product_title: Mapped[str | None] = mapped_column(String(512), nullable=True)
    price_amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(8), default="INR", nullable=False)
    in_stock: Mapped[bool] = mapped_column(default=True, nullable=False)
    promo_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    scraped_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


async def run_price_update_consumer() -> None:
    consumer: AIOKafkaConsumer = make_consumer(
        topic=settings.KAFKA_TOPIC_PRICE_UPDATES,
        group_id=settings.KAFKA_CONSUMER_GROUP_PERSISTENCE,
    )
    engine = create_async_engine(settings.DATABASE_URL, pool_pre_ping=True)
    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)
    redis: Redis = from_url(settings.REDIS_URL, encoding="utf-8", decode_responses=True)

    await consumer.start()
    await redis.ping()
    logger.info(
        "price-updates consumer started (group=%s)", settings.KAFKA_CONSUMER_GROUP_PERSISTENCE
    )

    try:
        async for message in consumer:
            event = message.value
            request_id_raw = event.get("request_id")
            product_url = event.get("product_url")
            status = event.get("status")
            logger.info("Received PriceUpdated request_id=%s status=%s", request_id_raw, status)

            try:
                async with session_factory() as session:
                    request_id = uuid.UUID(request_id_raw) if request_id_raw else None

                    if status == "completed" and event.get("price_amount") is not None:
                        record = PriceRecord(
                            check_request_id=request_id,
                            product_url=product_url,
                            product_title=event.get("product_title"),
                            price_amount=event["price_amount"],
                            currency=event.get("currency", "INR"),
                            in_stock=event.get("in_stock", True),
                            promo_text=event.get("promo_text"),
                        )
                        session.add(record)

                    if request_id is not None:
                        result = await session.execute(
                            select(PriceCheckRequest).where(PriceCheckRequest.id == request_id)
                        )
                        check_request = result.scalar_one_or_none()
                        if check_request is not None:
                            check_request.status = CheckStatus(status)
                            check_request.completed_at = datetime.utcnow()
                            check_request.error_message = event.get("error_message")

                    await session.commit()

                if status == "completed" and event.get("price_amount") is not None:
                    await redis.set(
                        f"pricepulse:latest:{product_url}",
                        json.dumps(event),
                        ex=3600,
                    )

                await redis.publish(PRICE_UPDATES_CHANNEL, json.dumps(event))

            except Exception:
                logger.exception("Failed to persist PriceUpdated for request_id=%s", request_id_raw)
                # Do not commit the Kafka offset on persistence failure —
                # let the consumer redeliver on restart rather than silently
                # dropping a price update.
                continue

            await consumer.commit()

    finally:
        await consumer.stop()
        await redis.aclose()
        await engine.dispose()
        logger.info("price-updates consumer stopped")
