import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.routes import router as v1_router
from app.core.config import get_settings
from app.core.kafka_producer import kafka_producer
from app.core.redis_client import redis_client

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("pricepulse.main")
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting %s (%s)", settings.APP_NAME, settings.ENV)
    await kafka_producer.start()
    await redis_client.start()
    yield
    await kafka_producer.stop()
    await redis_client.stop()
    logger.info("Shutdown complete")


app = FastAPI(title=settings.APP_NAME, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(v1_router, prefix=settings.API_V1_PREFIX)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
