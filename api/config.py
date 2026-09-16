import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

# Get the root directory (one level up from 'api/')
ROOT_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    DATABASE_URL: str
    CORS_ORIGINS: str = "*"

    @property
    def database_url(self) -> str:
        """Alias so database.py can use lowercase settings.database_url"""
        return self.DATABASE_URL

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]

    model_config = SettingsConfigDict(
        env_file=str(ROOT_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()