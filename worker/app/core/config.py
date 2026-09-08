from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    ENV: str = "development"

    # --- Postgres (persistence consumer writes directly) ---
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

    # --- Redis (cache + SSE fan-out publish) ---
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
    KAFKA_TOPIC_PRICE_CHECK_REQUESTS_DLQ: str = "price-check-requests.dlq"
    KAFKA_CONSUMER_GROUP_SCRAPER: str = "pricepulse-scraper-workers"
    KAFKA_CONSUMER_GROUP_PERSISTENCE: str = "pricepulse-persistence-workers"

    # --- Scraper ---
    SCRAPER_NAV_TIMEOUT_MS: int = 20000
    SCRAPER_MAX_RETRIES: int = 3
    SCRAPER_RETRY_BACKOFF_SECONDS: float = 2.0
    SCRAPER_PROXY_LIST: str = ""  # comma-separated, e.g. "http://user:pass@host:port,..."
    SCRAPER_HEADLESS: bool = True

    @property
    def proxy_list(self) -> list[str]:
        return [p.strip() for p in self.SCRAPER_PROXY_LIST.split(",") if p.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
