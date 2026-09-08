"""Pytest fixtures and configuration."""

import pytest

from whisper_bot.services.storage import MemoryWhisperStorage
from whisper_bot.services.whisper_service import WhisperService


@pytest.fixture
def storage() -> MemoryWhisperStorage:
    """Create a fresh in-memory whisper storage."""
    return MemoryWhisperStorage()


@pytest.fixture
def whisper_service(storage: MemoryWhisperStorage) -> WhisperService:
    """Create a fresh whisper service instance."""
    return WhisperService(storage=storage, default_ttl_seconds=3600)
