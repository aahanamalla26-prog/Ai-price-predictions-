"""
REST + SSE routes. The SSE endpoint subscribes to the Redis pub/sub channel
that the persistence consumer (worker side) publishes to, so live updates
reach every connected browser regardless of which backend replica handled
the original /check-price call.
"""
import asyncio
import json
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from app.core.redis_client import PRICE_UPDATES_CHANNEL, redis_client
from app.db.session import get_db
from app.schemas.events import CheckPriceRequest, CheckPriceResponse, CheckStatusOut, PriceRecordOut
from app.services.price_service import PriceService

logger = logging.getLogger("pricepulse.api")
router = APIRouter()


@router.post("/check-price", response_model=CheckPriceResponse, status_code=202)
async def check_price(payload: CheckPriceRequest, db: AsyncSession = Depends(get_db)) -> CheckPriceResponse:
    """Queue an async price check. Returns immediately; result arrives via SSE or polling."""
    check_request = await PriceService.trigger_price_check(db, str(payload.product_url))
    return CheckPriceResponse(request_id=check_request.id, status=check_request.status)


@router.get("/check-price/{request_id}", response_model=CheckStatusOut)
async def get_check_status(request_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> CheckStatusOut:
    check_request = await PriceService.get_check_status(db, request_id)
    if check_request is None:
        raise HTTPException(status_code=404, detail="Check request not found")
    return check_request


@router.get("/prices/history", response_model=list[PriceRecordOut])
async def get_price_history(
    product_url: str, limit: int = 50, db: AsyncSession = Depends(get_db)
) -> list[PriceRecordOut]:
    if limit < 1 or limit > 500:
        raise HTTPException(status_code=400, detail="limit must be between 1 and 500")
    return await PriceService.get_price_history(db, product_url, limit)


@router.get("/prices/stream")
async def stream_price_updates(request: Request):
    """
    Server-Sent Events stream of PriceUpdated events, fanned out via Redis
    pub/sub. One Redis subscription per connected client — fine at the
    scale this project targets; swap for a shared fan-out broker if the
    client count grows into the thousands.
    """
    pubsub = redis_client.client.pubsub()
    await pubsub.subscribe(PRICE_UPDATES_CHANNEL)

    async def event_generator():
        try:
            while True:
                if await request.is_disconnected():
                    break
                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=15.0)
                if message is None:
                    yield {"event": "heartbeat", "data": json.dumps({"ok": True})}
                    continue
                data = message["data"]
                logger.debug("Relaying price update over SSE: %s", data)
                yield {"event": "price-update", "data": data}
        except asyncio.CancelledError:
            raise
        finally:
            await pubsub.unsubscribe(PRICE_UPDATES_CHANNEL)
            await pubsub.aclose()

    return EventSourceResponse(event_generator())
