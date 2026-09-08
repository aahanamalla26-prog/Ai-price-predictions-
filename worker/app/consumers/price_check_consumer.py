"""
Consumes `price-check-requests`, drives the Playwright scraper, and
publishes the outcome to `price-updates` (success or failure — the
downstream persistence consumer records both so a failed check still shows
up as FAILED in the UI instead of silently vanishing).

Messages that fail scraping on every retry are routed to the DLQ topic with
the original payload plus the error, rather than being dropped or committed
as if handled — that's the whole point of having a DLQ.
"""
import logging
from datetime import datetime, timezone

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer

from app.core.config import get_settings
from app.core.kafka_clients import make_consumer, make_producer
from app.scrapers.scraper import PlaywrightScraper, ScrapeError

logger = logging.getLogger("pricepulse.worker.price_check_consumer")
settings = get_settings()


async def run_price_check_consumer(scraper: PlaywrightScraper) -> None:
    consumer: AIOKafkaConsumer = make_consumer(
        topic=settings.KAFKA_TOPIC_PRICE_CHECK_REQUESTS,
        group_id=settings.KAFKA_CONSUMER_GROUP_SCRAPER,
    )
    producer: AIOKafkaProducer = make_producer()

    await consumer.start()
    await producer.start()
    logger.info(
        "price-check-requests consumer started (group=%s)", settings.KAFKA_CONSUMER_GROUP_SCRAPER
    )

    try:
        async for message in consumer:
            event = message.value
            request_id = event.get("request_id")
            product_url = event.get("product_url")
            logger.info("Received PriceCheckRequested request_id=%s url=%s", request_id, product_url)

            try:
                result = await scraper.scrape(product_url)
                update = {
                    "request_id": request_id,
                    "product_url": product_url,
                    "product_title": result.product_title,
                    "price_amount": result.price_amount,
                    "currency": result.currency,
                    "in_stock": result.in_stock,
                    "promo_text": result.promo_text,
                    "status": "completed",
                    "error_message": None,
                    "scraped_at": datetime.now(timezone.utc).isoformat(),
                }
                await producer.send_and_wait(
                    settings.KAFKA_TOPIC_PRICE_UPDATES, value=update, key=str(request_id)
                )
                logger.info("Published PriceUpdated (completed) request_id=%s", request_id)

            except ScrapeError as exc:
                logger.error("Scrape failed permanently for request_id=%s: %s", request_id, exc)
                failure_update = {
                    "request_id": request_id,
                    "product_url": product_url,
                    "product_title": None,
                    "price_amount": None,
                    "currency": "INR",
                    "in_stock": False,
                    "promo_text": None,
                    "status": "failed",
                    "error_message": str(exc),
                    "scraped_at": datetime.now(timezone.utc).isoformat(),
                }
                await producer.send_and_wait(
                    settings.KAFKA_TOPIC_PRICE_UPDATES, value=failure_update, key=str(request_id)
                )
                await producer.send_and_wait(
                    settings.KAFKA_TOPIC_PRICE_CHECK_REQUESTS_DLQ,
                    value={**event, "error": str(exc)},
                    key=str(request_id),
                )

            except Exception:
                # Unexpected/non-scrape errors (bad payload, etc.) also go to
                # the DLQ so nothing is committed-and-lost silently.
                logger.exception("Unexpected error processing request_id=%s", request_id)
                await producer.send_and_wait(
                    settings.KAFKA_TOPIC_PRICE_CHECK_REQUESTS_DLQ,
                    value={**event, "error": "unexpected_processing_error"},
                    key=str(request_id),
                )

            finally:
                # Commit only after the message has produced either a
                # PriceUpdated event or a DLQ entry — never lose it silently.
                await consumer.commit()

    finally:
        await consumer.stop()
        await producer.stop()
        logger.info("price-check-requests consumer stopped")
