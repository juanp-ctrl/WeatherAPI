from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    ingestion_schema: str = "ingestion"
    open_meteo_base_url: str = "https://api.open-meteo.com"
    ingestion_interval_seconds: int = 900
    database_pool_size: int = 5
    database_max_overflow: int = 5
    log_level: str = "INFO"
    api_key: str = "dev-key"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
