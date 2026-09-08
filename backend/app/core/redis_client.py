"""
Async Redis client, shared across the app. Used for:
- caching the latest known price per (product_url) so GET requests are cheap
- pub/sub fan-out of PriceUpdated events to every SSE connection, so
  multiple backend replicas all see live updates, not just the one
  that happens to hold a given client's connection.
"""
import logging

from redis.asyncio import Redis, from_url

from app.core.config import get_settings

logger = logging.getLogger("pricepulse.redis_client")
settings = get_settings()

PRICE_UPDATES_CHANNEL = "pricepulse:price-updates"


class RedisClient:
    def __init__(self) -> None:
        self._redis: Redis | None = None

    async def start(self) -> None:
        if self._redis is not None:
            return
        self._redis = from_url(settings.REDIS_URL, encoding="utf-8", decode_responses=True)
        await self._redis.ping()
        logger.info("Redis connected at %s", settings.REDIS_URL)

    async def stop(self) -> None:
        if self._redis is not None:
            await self._redis.aclose()
            self._redis = None
            logger.info("Redis connection closed")

    @property
    def client(self) -> Redis:
        if self._redis is None:
            raise RuntimeError("Redis client accessed before start() was called")
        return self._redis

    async def cache_latest_price(self, product_url: str, payload: str, ttl_seconds: int = 3600) -> None:
        key = f"pricepulse:latest:{product_url}"
        await self.client.set(key, payload, ex=ttl_seconds)

    async def get_latest_price(self, product_url: str) -> str | None:
        key = f"pricepulse:latest:{product_url}"
        return await self.client.get(key)

    async def publish_price_update(self, payload: str) -> None:
        await self.client.publish(PRICE_UPDATES_CHANNEL, payload)


redis_client = RedisClient()
