from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings, populated from environment variables / .env."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # Database (async SQLAlchemy URL).
    database_url: str = "postgresql+asyncpg://shorturl:shorturl@localhost:5432/shorturl"

    # Cache backend: "memory" (single instance) or "redis" (shared).
    cache_backend: Literal["memory", "redis"] = "memory"
    redis_url: str = "redis://localhost:6379/0"
    cache_ttl_seconds: int = 3600
    cache_max_size: int = 10_000  # in-memory LRU capacity

    # Alias generation.
    alias_length: int = 7
    alias_max_retries: int = 5

    # Base URL used to build the returned short_url (no trailing slash).
    base_url: str = "http://localhost:8000"

    # Create DB schema on startup (handy locally; disable if managed externally).
    create_schema_on_startup: bool = True


@lru_cache
def get_settings() -> Settings:
    return Settings()
