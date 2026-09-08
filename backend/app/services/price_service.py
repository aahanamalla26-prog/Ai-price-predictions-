"""
Business logic sitting between the API routes and the DB/Kafka clients.
Keeping this out of api/v1/routes.py means the same logic is unit-testable
without spinning up FastAPI's request/response cycle.
"""
import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.kafka_producer import kafka_producer
from app.models.price import CheckStatus, PriceCheckRequest, PriceRecord
from app.schemas.events import PriceCheckRequested

logger = logging.getLogger("pricepulse.price_service")
settings = get_settings()


class PriceService:
    @staticmethod
    async def trigger_price_check(db: AsyncSession, product_url: str) -> PriceCheckRequest:
        check_request = PriceCheckRequest(product_url=product_url, status=CheckStatus.PENDING)
        db.add(check_request)
        await db.commit()
        await db.refresh(check_request)

        event = PriceCheckRequested(request_id=check_request.id, product_url=product_url)
        try:
            await kafka_producer.send(
                topic=settings.KAFKA_TOPIC_PRICE_CHECK_REQUESTS,
                value=event.model_dump(mode="json"),
                key=str(check_request.id),
            )
        except Exception:
            # Mark as failed rather than leaving it stuck in PENDING forever
            # if Kafka is unreachable at publish time.
            check_request.status = CheckStatus.FAILED
            check_request.error_message = "Failed to publish price-check event to Kafka"
            await db.commit()
            logger.exception("Kafka publish failed for request_id=%s", check_request.id)
            raise

        logger.info("Published PriceCheckRequested request_id=%s url=%s", check_request.id, product_url)
        return check_request

    @staticmethod
    async def get_check_status(db: AsyncSession, request_id: uuid.UUID) -> PriceCheckRequest | None:
        result = await db.execute(
            select(PriceCheckRequest).where(PriceCheckRequest.id == request_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_price_history(db: AsyncSession, product_url: str, limit: int = 50) -> list[PriceRecord]:
        result = await db.execute(
            select(PriceRecord)
            .where(PriceRecord.product_url == product_url)
            .order_by(PriceRecord.scraped_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
