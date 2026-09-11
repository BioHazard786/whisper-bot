"""Unit tests for SqliteWhisperStorage hybrid storage."""

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from whisper_bot.models.whisper import Whisper
from whisper_bot.services.storage import SqliteWhisperStorage


@pytest.fixture
def sqlite_storage(tmp_path: Path) -> SqliteWhisperStorage:
    """Create a temporary SQLite whisper storage instance."""
    db_file = str(tmp_path / "test_whispers.db")
    return SqliteWhisperStorage(db_path=db_file, enable_cache=True)


@pytest.mark.asyncio
async def test_sqlite_save_and_get(sqlite_storage: SqliteWhisperStorage) -> None:
    """Verify saving a whisper persists to both L1 cache and SQLite."""
    await sqlite_storage.init_db()

    whisper = Whisper(
        id="test1",
        sender_id=1,
        sender_first_name="Alice",
        sender_username="alice",
        target_usernames={"bob", "charlie"},
        target_user_ids={12345, 67890},
        text="Super secret message",
        is_one_time=False,
        expires_at=datetime.now(UTC) + timedelta(hours=1),
    )

    await sqlite_storage.save(whisper)

    # Read back
    retrieved = await sqlite_storage.get("test1")
    assert retrieved is not None
    assert retrieved.id == "test1"
    assert retrieved.sender_id == 1
    assert retrieved.sender_first_name == "Alice"
    assert retrieved.sender_username == "alice"
    assert retrieved.target_usernames == {"bob", "charlie"}
    assert retrieved.target_user_ids == {12345, 67890}
    assert retrieved.text == "Super secret message"
    assert retrieved.is_one_time is False

    await sqlite_storage.close()


@pytest.mark.asyncio
async def test_sqlite_fallback_on_cache_miss(sqlite_storage: SqliteWhisperStorage) -> None:
    """Verify get() falls back to SQLite and repopulates L1 cache when cache is cleared."""
    await sqlite_storage.init_db()

    whisper = Whisper(
        id="test_cache",
        sender_id=2,
        sender_first_name="Bob",
        sender_username="bob",
        target_usernames={"alice"},
        text="Cache fallback test",
        expires_at=datetime.now(UTC) + timedelta(hours=1),
    )

    await sqlite_storage.save(whisper)

    # Manually clear L1 cache to simulate cache eviction
    sqlite_storage._cache.clear()
    assert "test_cache" not in sqlite_storage._cache

    # Retrieve from DB
    retrieved = await sqlite_storage.get("test_cache")
    assert retrieved is not None
    assert retrieved.text == "Cache fallback test"

    # Verify L1 cache was repopulated
    assert "test_cache" in sqlite_storage._cache

    await sqlite_storage.close()


@pytest.mark.asyncio
async def test_sqlite_restart_persistence(tmp_path: Path) -> None:
    """Simulate bot restart: close storage and verify new instance primes cache from DB."""
    db_file = str(tmp_path / "restart_test.db")

    # Instance 1: Create and save
    storage1 = SqliteWhisperStorage(db_path=db_file)
    await storage1.init_db()

    whisper = Whisper(
        id="survive_restart",
        sender_id=1,
        sender_first_name="Alice",
        sender_username="alice",
        target_usernames={"bob"},
        text="I survived the restart!",
        expires_at=datetime.now(UTC) + timedelta(hours=2),
    )
    await storage1.save(whisper)
    await storage1.close()

    # Instance 2: Brand new instance pointing to same file
    storage2 = SqliteWhisperStorage(db_path=db_file)
    await storage2.init_db()

    # Verify primed directly in L1 cache
    assert "survive_restart" in storage2._cache
    retrieved = await storage2.get("survive_restart")
    assert retrieved is not None
    assert retrieved.text == "I survived the restart!"

    await storage2.close()


@pytest.mark.asyncio
async def test_sqlite_update(sqlite_storage: SqliteWhisperStorage) -> None:
    """Verify updates apply to both L1 cache and SQLite."""
    await sqlite_storage.init_db()

    whisper = Whisper(
        id="up1",
        sender_id=1,
        sender_first_name="Alice",
        sender_username="alice",
        target_usernames={"bob"},
        text="Original text",
        expires_at=datetime.now(UTC) + timedelta(hours=1),
    )
    await sqlite_storage.save(whisper)

    # Mark as read and update
    whisper.read_by.add(2)
    whisper.read_usernames.add("bob")
    whisper.is_destroyed = True
    await sqlite_storage.update(whisper)

    # Evict cache to verify SQLite has updated fields
    sqlite_storage._cache.clear()
    updated = await sqlite_storage.get("up1")
    assert updated is not None
    assert updated.is_destroyed is True
    assert 2 in updated.read_by
    assert "bob" in updated.read_usernames

    await sqlite_storage.close()


@pytest.mark.asyncio
async def test_sqlite_delete(sqlite_storage: SqliteWhisperStorage) -> None:
    """Verify deleting removes from both L1 cache and SQLite."""
    await sqlite_storage.init_db()

    whisper = Whisper(
        id="del1",
        sender_id=1,
        sender_first_name="Alice",
        sender_username="alice",
        target_usernames={"bob"},
        text="To be deleted",
        expires_at=datetime.now(UTC) + timedelta(hours=1),
    )
    await sqlite_storage.save(whisper)

    deleted = await sqlite_storage.delete("del1")
    assert deleted is True
    assert "del1" not in sqlite_storage._cache

    # Verify not found in DB
    retrieved = await sqlite_storage.get("del1")
    assert retrieved is None

    # Delete non-existent
    assert await sqlite_storage.delete("nonexistent") is False

    await sqlite_storage.close()


@pytest.mark.asyncio
async def test_sqlite_cleanup_expired(sqlite_storage: SqliteWhisperStorage) -> None:
    """Verify expired and destroyed whispers are purged from both cache and DB."""
    await sqlite_storage.init_db()

    # 1. Active whisper
    active = Whisper(
        id="active1",
        sender_id=1,
        sender_first_name="Alice",
        sender_username="alice",
        target_usernames={"bob"},
        text="Active",
        expires_at=datetime.now(UTC) + timedelta(hours=1),
    )
    # 2. Expired whisper
    expired = Whisper(
        id="expired1",
        sender_id=1,
        sender_first_name="Alice",
        sender_username="alice",
        target_usernames={"bob"},
        text="Expired",
        expires_at=datetime.now(UTC) - timedelta(minutes=10),
    )
    # 3. Destroyed whisper
    destroyed = Whisper(
        id="destroyed1",
        sender_id=1,
        sender_first_name="Alice",
        sender_username="alice",
        target_usernames={"bob"},
        text="Destroyed",
        is_destroyed=True,
        expires_at=datetime.now(UTC) + timedelta(hours=1),
    )

    await sqlite_storage.save(active)
    await sqlite_storage.save(expired)
    await sqlite_storage.save(destroyed)

    removed = await sqlite_storage.cleanup_expired()
    assert removed == 2

    assert await sqlite_storage.get("active1") is not None
    assert await sqlite_storage.get("expired1") is None
    assert await sqlite_storage.get("destroyed1") is None

    await sqlite_storage.close()


@pytest.mark.asyncio
async def test_sqlite_stats(sqlite_storage: SqliteWhisperStorage) -> None:
    """Verify stats accurately reflect active, total, and expired counts."""
    await sqlite_storage.init_db()

    w1 = Whisper(
        id="stat1",
        sender_id=1,
        sender_first_name="Alice",
        sender_username="alice",
        target_usernames={"bob"},
        text="Active",
        expires_at=datetime.now(UTC) + timedelta(hours=1),
    )
    w2 = Whisper(
        id="stat2",
        sender_id=1,
        sender_first_name="Alice",
        sender_username="alice",
        target_usernames={"bob"},
        text="Destroyed",
        is_destroyed=True,
        expires_at=datetime.now(UTC) + timedelta(hours=1),
    )

    await sqlite_storage.save(w1)
    await sqlite_storage.save(w2)

    stats = await sqlite_storage.get_stats()
    assert stats["current_total"] == 2
    assert stats["active"] == 1
    assert stats["expired_or_destroyed"] == 1
    assert stats["lifetime_created"] == 2

    await sqlite_storage.close()
