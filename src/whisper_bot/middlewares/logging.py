"""Structlog middleware tracking updates, execution latency, and errors."""

import time
from collections.abc import Awaitable, Callable
from typing import Any

import structlog
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Update

from whisper_bot.logger import get_logger

logger = get_logger(__name__)


class StructlogEventMiddleware(BaseMiddleware):
    """Middleware for structured request context logging with timing."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        start_time = time.perf_counter()
        update_id: int | None = None
        user_id: int | None = None
        event_type = type(event).__name__

        if isinstance(event, Update):
            update_id = event.update_id
            event_type = event.event_type
            user = getattr(event.event, "from_user", None)
            if user:
                user_id = user.id
            logger.info(
                "incoming_telegram_update",
                update_id=update_id,
                event_type=event_type,
                user_id=user_id,
            )

        structlog.contextvars.clear_contextvars()
        if update_id is not None:
            structlog.contextvars.bind_contextvars(update_id=update_id)
        if user_id is not None:
            structlog.contextvars.bind_contextvars(user_id=user_id)

        try:
            result = await handler(event, data)
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            logger.info(
                "telegram_event_processed",
                event_type=event_type,
                latency_ms=round(elapsed_ms, 2),
            )
            return result
        except Exception as exc:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            logger.error(
                "telegram_event_failed",
                event_type=event_type,
                error=str(exc),
                latency_ms=round(elapsed_ms, 2),
                exc_info=True,
            )
            raise
