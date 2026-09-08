"""Anti-spam throttling middleware."""

import time
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, InlineQuery, Message, TelegramObject

from whisper_bot.logger import get_logger

logger = get_logger(__name__)


class ThrottlingMiddleware(BaseMiddleware):
    """Simple in-memory cooldown rate limiter per user."""

    def __init__(self, rate_limit_seconds: float = 0.3) -> None:
        self._rate_limit = rate_limit_seconds
        self._user_timestamps: dict[int, float] = {}

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user_id: int | None = None
        if isinstance(event, (Message, CallbackQuery, InlineQuery)) and event.from_user:
            user_id = event.from_user.id

        if user_id is not None:
            now = time.perf_counter()
            last_time = self._user_timestamps.get(user_id, 0.0)

            if now - last_time < self._rate_limit:
                logger.warning("user_throttled", user_id=user_id)
                if isinstance(event, CallbackQuery):
                    await event.answer("⏳ Please slow down...", show_alert=False)
                return None

            self._user_timestamps[user_id] = now

            # Periodic cleanup of old timestamps if dict grows too large
            if len(self._user_timestamps) > 5000:
                cutoff = now - 60.0
                self._user_timestamps = {
                    uid: ts for uid, ts in self._user_timestamps.items() if ts > cutoff
                }

        return await handler(event, data)
