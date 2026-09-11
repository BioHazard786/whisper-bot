"""Whisper storage protocol, in-memory, and SQLite persistent implementations."""

import asyncio
import json
import os
import sqlite3
from datetime import UTC, datetime
from typing import Protocol

import aiosqlite

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


class SqliteWhisperStorage:
    """Thread-safe hybrid storage: L1 in-memory cache + L2 SQLite persistence with aiosqlite."""

    def __init__(self, db_path: str = "data/whispers.db", enable_cache: bool = True) -> None:
        self._db_path = db_path
        self._enable_cache = enable_cache
        self._cache: dict[str, Whisper] = {}
        self._lock = asyncio.Lock()
        self._db: aiosqlite.Connection | None = None
        self._total_created: int = 0

    async def _init_unlocked(self) -> None:
        """Internal helper to initialize SQLite connection and schema without locking."""
        if self._db is not None:
            return

        db_dir = os.path.dirname(self._db_path)
        if db_dir:
            try:
                os.makedirs(db_dir, exist_ok=True)
            except OSError as exc:
                raise PermissionError(
                    f"Unable to create SQLite directory '{db_dir}': {exc}. "
                    f"Check folder permissions and ownership."
                ) from exc

            if not os.access(db_dir, os.W_OK):
                uid = os.getuid() if hasattr(os, "getuid") else "unknown"
                raise PermissionError(
                    f"SQLite database directory '{db_dir}' is not writable by current user "
                    f"(UID={uid}). If running in Docker, verify volume permissions or ownership."
                )

        try:
            self._db = await aiosqlite.connect(self._db_path)
        except sqlite3.OperationalError as exc:
            uid = os.getuid() if hasattr(os, "getuid") else "unknown"
            raise PermissionError(
                f"Failed to open SQLite database '{self._db_path}' (UID={uid}): {exc}. "
                f"Verify directory permissions and volume mount ownership."
            ) from exc

        self._db.row_factory = aiosqlite.Row

        # Optimize for concurrency and speed
        await self._db.execute("PRAGMA journal_mode=WAL;")
        await self._db.execute("PRAGMA synchronous=NORMAL;")
        await self._db.execute("PRAGMA foreign_keys=ON;")

        await self._db.execute("""
            CREATE TABLE IF NOT EXISTS whispers (
                id TEXT PRIMARY KEY,
                sender_id INTEGER NOT NULL,
                sender_first_name TEXT NOT NULL,
                sender_username TEXT,
                target_usernames TEXT NOT NULL,
                target_user_ids TEXT NOT NULL,
                text TEXT NOT NULL,
                is_one_time INTEGER NOT NULL DEFAULT 0,
                allow_sender_view INTEGER NOT NULL DEFAULT 1,
                read_by TEXT NOT NULL,
                read_usernames TEXT NOT NULL,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                is_destroyed INTEGER NOT NULL DEFAULT 0,
                inline_message_id TEXT,
                chat_id INTEGER,
                group_message_id INTEGER
            );
        """)
        await self._db.execute(
            "CREATE INDEX IF NOT EXISTS idx_whispers_expires_at ON whispers(expires_at);"
        )
        await self._db.execute(
            "CREATE INDEX IF NOT EXISTS idx_whispers_is_destroyed ON whispers(is_destroyed);"
        )
        await self._db.commit()

    async def init_db(self) -> None:
        """Initialize SQLite database, verify schema, and prime L1 cache with active whispers."""
        async with self._lock:
            await self._init_unlocked()
            assert self._db is not None

            # Read lifetime count
            async with self._db.execute("SELECT COUNT(*) FROM whispers;") as cursor:
                row = await cursor.fetchone()
                self._total_created = row[0] if row else 0

            # Prime L1 cache with active, unexpired whispers
            if self._enable_cache:
                loaded_count = 0
                now = datetime.now(UTC)
                async with self._db.execute(
                    "SELECT * FROM whispers WHERE is_destroyed = 0;"
                ) as cursor:
                    rows = await cursor.fetchall()
                    for row in rows:
                        w = self._row_to_whisper(row)
                        if w.expires_at > now:
                            self._cache[w.id] = w
                            loaded_count += 1
                logger.info(
                    "sqlite_storage_initialized",
                    db_path=self._db_path,
                    cache_primed_count=loaded_count,
                    total_records=self._total_created,
                )

    def _row_to_whisper(self, row: aiosqlite.Row) -> Whisper:
        """Deserialize an SQLite Row into a Whisper domain model."""
        created_at = datetime.fromisoformat(row["created_at"])
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=UTC)

        expires_at = datetime.fromisoformat(row["expires_at"])
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)

        return Whisper(
            id=row["id"],
            sender_id=row["sender_id"],
            sender_first_name=row["sender_first_name"],
            sender_username=row["sender_username"],
            target_usernames=set(json.loads(row["target_usernames"])),
            target_user_ids=set(json.loads(row["target_user_ids"])),
            text=row["text"],
            is_one_time=bool(row["is_one_time"]),
            allow_sender_view=bool(row["allow_sender_view"]),
            read_by=set(json.loads(row["read_by"])),
            read_usernames=set(json.loads(row["read_usernames"])),
            created_at=created_at,
            expires_at=expires_at,
            is_destroyed=bool(row["is_destroyed"]),
            inline_message_id=row["inline_message_id"],
            chat_id=row["chat_id"],
            group_message_id=row["group_message_id"],
        )

    async def save(self, whisper: Whisper) -> None:
        """Write whisper to L1 cache and persist to SQLite."""
        async with self._lock:
            if self._db is None:
                await self._init_unlocked()

            if self._enable_cache:
                self._cache[whisper.id] = whisper

            self._total_created += 1

            assert self._db is not None
            await self._db.execute(
                """
                INSERT OR REPLACE INTO whispers (
                    id, sender_id, sender_first_name, sender_username,
                    target_usernames, target_user_ids, text, is_one_time,
                    allow_sender_view, read_by, read_usernames, created_at,
                    expires_at, is_destroyed, inline_message_id, chat_id,
                    group_message_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    whisper.id,
                    whisper.sender_id,
                    whisper.sender_first_name,
                    whisper.sender_username,
                    json.dumps(sorted(whisper.target_usernames)),
                    json.dumps(sorted(whisper.target_user_ids)),
                    whisper.text,
                    int(whisper.is_one_time),
                    int(whisper.allow_sender_view),
                    json.dumps(sorted(whisper.read_by)),
                    json.dumps(sorted(whisper.read_usernames)),
                    whisper.created_at.isoformat(),
                    whisper.expires_at.isoformat(),
                    int(whisper.is_destroyed),
                    whisper.inline_message_id,
                    whisper.chat_id,
                    whisper.group_message_id,
                ),
            )
            await self._db.commit()

    async def get(self, whisper_id: str) -> Whisper | None:
        """Retrieve whisper from L1 cache; fallback to SQLite on cache miss."""
        async with self._lock:
            if self._enable_cache and whisper_id in self._cache:
                return self._cache[whisper_id]

            if self._db is None:
                await self._init_unlocked()

            assert self._db is not None
            async with self._db.execute(
                "SELECT * FROM whispers WHERE id = ?;", (whisper_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if not row:
                    return None

                whisper = self._row_to_whisper(row)
                if self._enable_cache:
                    self._cache[whisper.id] = whisper
                return whisper

    async def update(self, whisper: Whisper) -> None:
        """Update whisper in L1 cache and persist updates to SQLite."""
        async with self._lock:
            if self._db is None:
                await self._init_unlocked()

            if self._enable_cache:
                self._cache[whisper.id] = whisper

            assert self._db is not None
            await self._db.execute(
                """
                UPDATE whispers SET
                    sender_id = ?,
                    sender_first_name = ?,
                    sender_username = ?,
                    target_usernames = ?,
                    target_user_ids = ?,
                    text = ?,
                    is_one_time = ?,
                    allow_sender_view = ?,
                    read_by = ?,
                    read_usernames = ?,
                    created_at = ?,
                    expires_at = ?,
                    is_destroyed = ?,
                    inline_message_id = ?,
                    chat_id = ?,
                    group_message_id = ?
                WHERE id = ?;
                """,
                (
                    whisper.sender_id,
                    whisper.sender_first_name,
                    whisper.sender_username,
                    json.dumps(sorted(whisper.target_usernames)),
                    json.dumps(sorted(whisper.target_user_ids)),
                    whisper.text,
                    int(whisper.is_one_time),
                    int(whisper.allow_sender_view),
                    json.dumps(sorted(whisper.read_by)),
                    json.dumps(sorted(whisper.read_usernames)),
                    whisper.created_at.isoformat(),
                    whisper.expires_at.isoformat(),
                    int(whisper.is_destroyed),
                    whisper.inline_message_id,
                    whisper.chat_id,
                    whisper.group_message_id,
                    whisper.id,
                ),
            )
            await self._db.commit()

    async def delete(self, whisper_id: str) -> bool:
        """Delete whisper from L1 cache and remove from SQLite."""
        async with self._lock:
            if self._db is None:
                await self._init_unlocked()

            if self._enable_cache:
                self._cache.pop(whisper_id, None)

            assert self._db is not None
            async with self._db.execute(
                "DELETE FROM whispers WHERE id = ?;", (whisper_id,)
            ) as cursor:
                await self._db.commit()
                return cursor.rowcount > 0

    async def cleanup_expired(self) -> int:
        """Purge expired and destroyed whispers from L1 cache and SQLite."""
        async with self._lock:
            if self._db is None:
                await self._init_unlocked()

            # Evict from L1 cache
            if self._enable_cache:
                expired_in_cache = [
                    wid for wid, w in self._cache.items() if w.is_expired or w.is_destroyed
                ]
                for wid in expired_in_cache:
                    del self._cache[wid]

            # Evict from SQLite
            assert self._db is not None
            now_iso = datetime.now(UTC).isoformat()
            async with self._db.execute(
                "DELETE FROM whispers WHERE expires_at <= ? OR is_destroyed = 1;",
                (now_iso,),
            ) as cursor:
                removed = cursor.rowcount
                await self._db.commit()

            if removed > 0:
                logger.info("cleaned_up_expired_whispers_sqlite", count=removed)
            return max(removed, 0)

    async def get_stats(self) -> dict[str, int]:
        """Return counts of total, active, and expired whispers."""
        async with self._lock:
            if self._db is None:
                await self._init_unlocked()

            assert self._db is not None
            now_iso = datetime.now(UTC).isoformat()
            async with self._db.execute("SELECT COUNT(*) FROM whispers;") as cursor:
                row = await cursor.fetchone()
                total = row[0] if row else 0

            async with self._db.execute(
                "SELECT COUNT(*) FROM whispers WHERE is_destroyed = 0 AND expires_at > ?;",
                (now_iso,),
            ) as cursor:
                row = await cursor.fetchone()
                active = row[0] if row else 0

            expired_or_destroyed = total - active
            return {
                "current_total": total,
                "active": active,
                "expired_or_destroyed": expired_or_destroyed,
                "lifetime_created": self._total_created,
            }

    async def close(self) -> None:
        """Gracefully close the SQLite connection."""
        async with self._lock:
            if self._db is not None:
                await self._db.close()
                self._db = None
                logger.info("sqlite_storage_closed")
