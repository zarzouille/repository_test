"""Application configuration module."""
from functools import lru_cache
from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    """Configuration loaded from environment variables."""

    app_name: str = Field("Countdown Service", description="Human readable service name")
    default_timezone: str = Field(
        "UTC", description="Timezone used when one is not supplied in the request"
    )
    cache_ttl_seconds: int = Field(60, description="Cache time-to-live in seconds")

    class Config:
        env_prefix = "COUNTDOWN_"


@lru_cache
def get_settings() -> Settings:
    """Return cached settings instance."""

    return Settings()
