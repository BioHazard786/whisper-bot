"""Whisper storage protocol and thread-safe in-memory implementation."""

import asyncio
from typing import Protocol

from whisper_bot.logger import get_logger
from whisper_bot.models.whisper import Whisper

logger = get_logger(__name__)


class WhisperStorageProtocol(Protocol):
    """Abstract interface for whisper message storage."""

    async def save(self, whisper: Whisper) -> None:
        """Save a new whisper."""
        ...

    async def get(self, whisper_id: str) -> Whisper | None:
        """Retrieve a whisper by its identifier."""
        ...

    async def update(self, whisper: Whisper) -> None:
        """Update an existing whisper."""
        ...

    async def delete(self, whisper_id: str) -> bool:
        """Delete a whisper by its identifier."""
        ...

    async def cleanup_expired(self) -> int:
        """Remove all expired or destroyed whispers past TTL. Returns count removed."""
        ...

    async def get_stats(self) -> dict[str, int]:
        """Return counts of total, active, and expired whispers."""
        ...


class MemoryWhisperStorage:
    """Thread-safe and asyncio-safe in-memory storage for whispers."""

    def __init__(self) -> None:
        self._store: dict[str, Whisper] = {}
        self._lock = asyncio.Lock()
        self._total_created: int = 0

    async def save(self, whisper: Whisper) -> None:
        async with self._lock:
            self._store[whisper.id] = whisper
            self._total_created += 1

    async def get(self, whisper_id: str) -> Whisper | None:
        async with self._lock:
            return self._store.get(whisper_id)

    async def update(self, whisper: Whisper) -> None:
        async with self._lock:
            self._store[whisper.id] = whisper

    async def delete(self, whisper_id: str) -> bool:
        async with self._lock:
            return self._store.pop(whisper_id, None) is not None

    async def cleanup_expired(self) -> int:
        removed = 0
        async with self._lock:
            expired_keys = [
                wid
                for wid, whisper in self._store.items()
                if whisper.is_expired or whisper.is_destroyed
            ]
            for key in expired_keys:
                del self._store[key]
                removed += 1

        if removed > 0:
            logger.info("cleaned_up_expired_whispers", count=removed)
        return removed

    async def get_stats(self) -> dict[str, int]:
        async with self._lock:
            active = sum(1 for w in self._store.values() if not w.is_expired and not w.is_destroyed)
            expired = sum(1 for w in self._store.values() if w.is_expired or w.is_destroyed)
            return {
                "current_total": len(self._store),
                "active": active,
                "expired_or_destroyed": expired,
                "lifetime_created": self._total_created,
            }
