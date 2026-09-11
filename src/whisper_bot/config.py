"""Application configuration using pydantic-settings."""

from functools import lru_cache
from typing import Any

from pydantic import Field, field_validator
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
    storage_backend: str = Field(
        default="sqlite",
        alias="STORAGE_BACKEND",
        description="Storage backend: 'sqlite' (dual in-memory + sqlite) or 'memory'",
    )
    sqlite_db_path: str = Field(
        default="data/whispers.db",
        alias="SQLITE_DB_PATH",
        description="File path for SQLite database",
    )
    log_channel: int | str | None = Field(
        default=None,
        alias="LOG_CHANNEL",
        description="Telegram log channel ID (-100...) or @username to log whispers",
    )

    @field_validator("log_channel", mode="before")
    @classmethod
    def parse_log_channel(cls, v: Any) -> int | str | None:
        """Parse LOG_CHANNEL into integer ID, @channel username, or None if omitted/empty."""
        if v is None:
            return None
        if isinstance(v, str):
            v_str = v.strip()
            if not v_str or v_str.lower() in ("none", "null", "false", "0"):
                return None
            if (v_str.startswith("-") and v_str[1:].isdigit()) or v_str.isdigit():
                return int(v_str)
            return v_str
        if isinstance(v, int):
            return v if v != 0 else None
        return None


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached application settings singleton."""
    return Settings()
