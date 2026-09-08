"""
Factory helpers for aiokafka producer/consumer instances used by the worker's
two consumer loops. Kept separate from consumer logic so tests can mock
these independently.
"""
import json
import logging

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer

from app.core.config import get_settings

logger = logging.getLogger("pricepulse.worker.kafka")
settings = get_settings()


def make_producer() -> AIOKafkaProducer:
    return AIOKafkaProducer(
        bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
        client_id="pricepulse-worker-producer",
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        key_serializer=lambda k: k.encode("utf-8") if k else None,
        acks="all",
        enable_idempotence=True,
        request_timeout_ms=15000,
        retry_backoff_ms=500,
    )


def make_consumer(topic: str, group_id: str) -> AIOKafkaConsumer:
    return AIOKafkaConsumer(
        topic,
        bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
        group_id=group_id,
        value_deserializer=lambda v: json.loads(v.decode("utf-8")),
        key_deserializer=lambda k: k.decode("utf-8") if k else None,
        enable_auto_commit=False,  # commit manually after successful processing
        auto_offset_reset="earliest",
        max_poll_interval_ms=300000,  # scraping is slow; give ourselves room
        session_timeout_ms=45000,
    )
