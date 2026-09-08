"""Application configuration using pydantic-settings."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Whisper bot configuration loaded from environment variables or .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    bot_token: str = Field(
        default="",
        alias="BOT_TOKEN",
        description="Telegram Bot API Token from @BotFather",
    )
    log_level: str = Field(
        default="INFO",
        alias="LOG_LEVEL",
        description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
    )
    app_env: str = Field(
        default="development",
        alias="APP_ENV",
        description="Environment (development, staging, production)",
    )
    default_whisper_ttl_seconds: int = Field(
        default=86400,
        alias="DEFAULT_WHISPER_TTL_SECONDS",
        description="Default expiration time for whispers in seconds (24 hours)",
    )
    cleanup_interval_seconds: int = Field(
        default=300,
        alias="CLEANUP_INTERVAL_SECONDS",
        description="Interval between expired whisper cleanup sweeps (5 minutes)",
    )
    rate_limit_seconds: float = Field(
        default=0.3,
        alias="RATE_LIMIT_SECONDS",
        description="Minimum cooldown between callback queries per user to prevent spam",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached application settings singleton."""
    return Settings()
