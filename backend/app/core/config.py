"""
Application settings, loaded from environment variables (see docker-compose.yml).
Uses pydantic-settings so misconfiguration fails fast at startup.
"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- App ---
    APP_NAME: str = "PricePulse API"
    ENV: str = "development"
    API_V1_PREFIX: str = "/api/v1"

    # --- Postgres ---
    POSTGRES_HOST: str = "postgres"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "pricepulse"
    POSTGRES_PASSWORD: str = "pricepulse"
    POSTGRES_DB: str = "pricepulse"

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    # --- Redis ---
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0

    @property
    def REDIS_URL(self) -> str:
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    # --- Kafka ---
    KAFKA_BOOTSTRAP_SERVERS: str = "kafka:9092"
    KAFKA_TOPIC_PRICE_CHECK_REQUESTS: str = "price-check-requests"
    KAFKA_TOPIC_PRICE_UPDATES: str = "price-updates"
    KAFKA_PRODUCER_CLIENT_ID: str = "pricepulse-backend"

    # --- CORS ---
    CORS_ORIGINS: list[str] = ["http://localhost:4200"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
