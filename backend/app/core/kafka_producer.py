"""
Singleton-style AIOKafkaProducer wrapper, started/stopped from the FastAPI
lifespan handler in main.py. Never instantiate AIOKafkaProducer per-request —
connection setup is expensive and aiokafka producers are safe to share.
"""
import json
import logging
from typing import Any

from aiokafka import AIOKafkaProducer
from aiokafka.errors import KafkaConnectionError, KafkaTimeoutError

from app.core.config import get_settings

logger = logging.getLogger("pricepulse.kafka_producer")
settings = get_settings()


class KafkaProducerClient:
    def __init__(self) -> None:
        self._producer: AIOKafkaProducer | None = None

    async def start(self) -> None:
        if self._producer is not None:
            return
        self._producer = AIOKafkaProducer(
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            client_id=settings.KAFKA_PRODUCER_CLIENT_ID,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            key_serializer=lambda k: k.encode("utf-8") if k else None,
            acks="all",
            enable_idempotence=True,
            request_timeout_ms=15000,
            retry_backoff_ms=500,
        )
        await self._producer.start()
        logger.info("Kafka producer started against %s", settings.KAFKA_BOOTSTRAP_SERVERS)

    async def stop(self) -> None:
        if self._producer is not None:
            await self._producer.stop()
            self._producer = None
            logger.info("Kafka producer stopped")

    async def send(self, topic: str, value: dict[str, Any], key: str | None = None) -> None:
        if self._producer is None:
            raise RuntimeError("Kafka producer accessed before start() was called")
        try:
            await self._producer.send_and_wait(topic, value=value, key=key)
        except (KafkaConnectionError, KafkaTimeoutError):
            logger.exception("Failed to publish message to topic=%s", topic)
            raise


# Module-level singleton, imported by main.py and the API routes.
kafka_producer = KafkaProducerClient()
