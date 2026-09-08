"""Unit tests for Whisper storage."""

from datetime import UTC, datetime, timedelta

import pytest

from whisper_bot.models.whisper import Whisper
from whisper_bot.services.storage import MemoryWhisperStorage


@pytest.mark.asyncio
async def test_save_and_get_whisper(storage: MemoryWhisperStorage) -> None:
    whisper = Whisper(
        id="test1",
        sender_id=100,
        sender_first_name="Alice",
        sender_username="alice",
        target_usernames={"bob"},
        text="secret",
    )
    await storage.save(whisper)

    retrieved = await storage.get("test1")
    assert retrieved is not None
    assert retrieved.id == "test1"
    assert retrieved.text == "secret"
    assert retrieved.sender_id == 100


@pytest.mark.asyncio
async def test_delete_whisper(storage: MemoryWhisperStorage) -> None:
    whisper = Whisper(
        id="test2",
        sender_id=100,
        sender_first_name="Alice",
        sender_username="alice",
        target_usernames={"bob"},
        text="secret",
    )
    await storage.save(whisper)
    deleted = await storage.delete("test2")
    assert deleted is True

    retrieved = await storage.get("test2")
    assert retrieved is None


@pytest.mark.asyncio
async def test_cleanup_expired(storage: MemoryWhisperStorage) -> None:
    past = datetime.now(UTC) - timedelta(hours=1)
    future = datetime.now(UTC) + timedelta(hours=1)

    expired_whisper = Whisper(
        id="exp",
        sender_id=100,
        sender_first_name="Alice",
        sender_username="alice",
        target_usernames={"bob"},
        text="old",
        expires_at=past,
    )
    active_whisper = Whisper(
        id="act",
        sender_id=101,
        sender_first_name="Bob",
        sender_username="bob",
        target_usernames={"alice"},
        text="new",
        expires_at=future,
    )
    destroyed_whisper = Whisper(
        id="des",
        sender_id=102,
        sender_first_name="Charlie",
        sender_username="charlie",
        target_usernames={"alice"},
        text="destroyed",
        expires_at=future,
        is_destroyed=True,
    )

    await storage.save(expired_whisper)
    await storage.save(active_whisper)
    await storage.save(destroyed_whisper)

    removed = await storage.cleanup_expired()
    assert removed == 2

    assert await storage.get("exp") is None
    assert await storage.get("des") is None
    assert await storage.get("act") is not None


@pytest.mark.asyncio
async def test_storage_stats(storage: MemoryWhisperStorage) -> None:
    whisper = Whisper(
        id="stat1",
        sender_id=100,
        sender_first_name="Alice",
        sender_username="alice",
        target_usernames={"bob"},
        text="stat text",
        expires_at=datetime.now(UTC) + timedelta(hours=1),
    )
    await storage.save(whisper)
    stats = await storage.get_stats()
    assert stats["current_total"] == 1
    assert stats["active"] == 1
    assert stats["lifetime_created"] == 1
