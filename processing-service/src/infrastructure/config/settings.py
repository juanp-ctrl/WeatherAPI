from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    processing_schema: str = "processing"
    ingestion_service_url: str = "http://ingestion-service:8000"
    processing_interval_seconds: int = 300
    database_pool_size: int = 5
    database_max_overflow: int = 5
    log_level: str = "INFO"
    api_key: str = "dev-key"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
