"""
App configuration, loaded from environment variables (or a .env file).
Drop this in your backend/ folder.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Postgres connection string, e.g.
    # postgresql+psycopg2://user:password@host:5432/pricepulse
    database_url: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/pricepulse"

    redis_url: str = "redis://localhost:6379/0"

    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_price_topic: str = "price-updates"

    # Comma-separated list of allowed frontend origins for CORS.
    # Set this to your deployed frontend URL(s) in production.
    cors_origins: str = "*"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        if self.cors_origins.strip() == "*":
            return ["*"]
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
