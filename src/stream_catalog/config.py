"""Application settings, environment-driven (prefix ``CATALOG_``)."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="CATALOG_")

    mongo_url: str = "mongodb://localhost:27017"
    mongo_db: str = "stream_catalog"
    es_url: str = "http://localhost:9200"
    es_index: str = "titles"
    # "wait_for" refresh on writes: enable only in tests, hurts write throughput.
    es_refresh_on_write: bool = False
    es_retry_attempts: int = 3
    es_retry_base_delay: float = 0.1
