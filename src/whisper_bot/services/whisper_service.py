"""Whisper business logic service."""

import asyncio
import contextlib
import secrets
from datetime import UTC, datetime, timedelta

from whisper_bot.logger import get_logger
from whisper_bot.models.whisper import Whisper
from whisper_bot.services.storage import WhisperStorageProtocol

logger = get_logger(__name__)


class WhisperService:
    """Service managing whisper lifecycle, authorization, and eviction."""

    def __init__(
        self,
        storage: WhisperStorageProtocol,
        default_ttl_seconds: int = 86400,
    ) -> None:
        self._storage = storage
        self._default_ttl = default_ttl_seconds
        self._shutdown_event = asyncio.Event()

    async def create_whisper(
        self,
        sender_id: int,
        sender_first_name: str,
        sender_username: str | None,
        text: str,
        target_usernames: set[str],
        target_user_ids: set[int] | None = None,
        is_one_time: bool = False,
        allow_sender_view: bool = True,
        ttl_seconds: int | None = None,
        chat_id: int | None = None,
        group_message_id: int | None = None,
        custom_id: str | None = None,
    ) -> Whisper:
        """Create and store a new whisper."""
        whisper_id = custom_id or secrets.token_urlsafe(6)
        ttl = ttl_seconds if ttl_seconds is not None else self._default_ttl
        now = datetime.now(UTC)
        expires_at = now + timedelta(seconds=ttl)

        clean_usernames = {u.lstrip("@").strip().lower() for u in target_usernames}
        clean_user_ids = target_user_ids or set()

        whisper = Whisper(
            id=whisper_id,
            sender_id=sender_id,
            sender_first_name=sender_first_name,
            sender_username=sender_username,
            target_usernames=clean_usernames,
            target_user_ids=clean_user_ids,
            text=text,
            is_one_time=is_one_time,
            allow_sender_view=allow_sender_view,
            created_at=now,
            expires_at=expires_at,
            chat_id=chat_id,
            group_message_id=group_message_id,
        )

        await self._storage.save(whisper)
        logger.info(
            "whisper_created",
            whisper_id=whisper.id,
            sender_id=sender_id,
            targets=whisper.format_targets_display(),
            is_one_time=is_one_time,
        )
        return whisper

    async def get_whisper(self, whisper_id: str) -> Whisper | None:
        """Retrieve a whisper by ID."""
        return await self._storage.get(whisper_id)

    async def bind_inline_message(self, whisper_id: str, inline_message_id: str) -> None:
        """Bind an inline message ID to a whisper once sent."""
        whisper = await self._storage.get(whisper_id)
        if whisper:
            whisper.inline_message_id = inline_message_id
            await self._storage.update(whisper)

    async def access_whisper(
        self,
        whisper_id: str,
        user_id: int,
        username: str | None,
    ) -> tuple[Whisper | None, bool, str]:
        """Validate access and consume/reveal whisper content.

        Returns:
            tuple: (whisper, is_authorized, status_code_or_content)
            Status codes if not authorized:
            - "not_found"
            - "expired"
            - "destroyed"
            - "unauthorized"
        """
        whisper = await self._storage.get(whisper_id)
        if whisper is None:
            return None, False, "not_found"

        if whisper.is_destroyed:
            return whisper, False, "destroyed"

        if whisper.is_expired:
            return whisper, False, "expired"

        if not whisper.can_view(user_id, username):
            logger.warning(
                "whisper_access_denied",
                whisper_id=whisper_id,
                attempting_user_id=user_id,
                attempting_username=username,
            )
            return whisper, False, "unauthorized"

        is_recipient = user_id != whisper.sender_id or (
            user_id == whisper.sender_id
            and not whisper.target_usernames
            and not whisper.target_user_ids
        )

        clean_user = username.lstrip("@").strip().lower() if username else None
        already_viewed = user_id in whisper.read_by or (
            clean_user is not None and clean_user in whisper.read_usernames
        )

        if whisper.is_one_time and is_recipient and already_viewed:
            return whisper, False, "already_read"

        # Authorized view
        whisper.read_by.add(user_id)
        if clean_user:
            whisper.read_usernames.add(clean_user)

        # If one-time whisper and opened by intended recipient:
        if whisper.is_one_time and is_recipient:
            all_usernames_done = whisper.target_usernames.issubset(whisper.read_usernames)
            all_ids_done = whisper.target_user_ids.issubset(whisper.read_by)
            if (
                (whisper.target_usernames or whisper.target_user_ids)
                and all_usernames_done
                and all_ids_done
            ):
                whisper.is_destroyed = True
                logger.info("whisper_destroyed_all_recipients_viewed", whisper_id=whisper_id)
            elif not whisper.target_usernames and not whisper.target_user_ids:
                whisper.is_destroyed = True
                logger.info("whisper_destroyed_after_view", whisper_id=whisper_id, read_by=user_id)

        await self._storage.update(whisper)
        return whisper, True, whisper.text

    async def delete_whisper(self, whisper_id: str, user_id: int) -> bool:
        """Allow the sender to delete their whisper early."""
        whisper = await self._storage.get(whisper_id)
        if not whisper or whisper.sender_id != user_id:
            return False

        whisper.is_destroyed = True
        await self._storage.update(whisper)
        logger.info("whisper_manually_deleted", whisper_id=whisper_id, user_id=user_id)
        return True

    def stop_cleanup_worker(self) -> None:
        """Signal the cleanup background worker to stop immediately."""
        self._shutdown_event.set()

    async def run_cleanup_worker(
        self,
        interval_seconds: int = 300,
        initial_wait_seconds: float = 10.0,
    ) -> None:
        """Background task that continuously purges expired whispers with graceful interruptible shutdown."""
        logger.info("cleanup_worker_started", interval_seconds=interval_seconds)

        # Initial wait after startup (interruptible if stopped early)
        if initial_wait_seconds > 0:
            with contextlib.suppress(TimeoutError):
                await asyncio.wait_for(self._shutdown_event.wait(), timeout=initial_wait_seconds)

        while not self._shutdown_event.is_set():
            try:
                logger.debug("running_periodic_whisper_cleanup")
                await self._storage.cleanup_expired()
            except Exception as e:
                logger.error("cleanup_worker_error", error=str(e))

            # Sleep for interval_seconds, waking up immediately if shutdown is signaled
            with contextlib.suppress(TimeoutError):
                await asyncio.wait_for(
                    self._shutdown_event.wait(),
                    timeout=interval_seconds,
                )

        logger.info("cleanup_worker_stopped")
