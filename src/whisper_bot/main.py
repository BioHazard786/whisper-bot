"""Application entry point and lifecycle management."""

import asyncio
import contextlib
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand, BotCommandScopeAllGroupChats, BotCommandScopeDefault

from whisper_bot.config import get_settings
from whisper_bot.handlers import (
    callbacks_router,
    common_router,
    group_router,
    inline_router,
)
from whisper_bot.logger import get_logger, setup_logging
from whisper_bot.middlewares import StructlogEventMiddleware, ThrottlingMiddleware
from whisper_bot.services.channel_logger import ChannelLogger
from whisper_bot.services.storage import (
    MemoryWhisperStorage,
    SqliteWhisperStorage,
    WhisperStorageProtocol,
)
from whisper_bot.services.whisper_service import WhisperService

logger = get_logger(__name__)


async def setup_bot_commands(bot: Bot) -> None:
    """Register bot commands with Telegram, enabling Ephemeral Commands for groups."""
    # Default commands for all chats
    default_commands = [
        BotCommand(command="start", description="Start Psst! and open home menu"),
        BotCommand(command="help", description="How to send whispers"),
        BotCommand(command="stats", description="Show bot performance statistics"),
    ]
    await bot.set_my_commands(commands=default_commands, scope=BotCommandScopeDefault())

    # Ephemeral group commands: Telegram hides the user's input from other members!
    group_commands = [
        BotCommand(
            command="whisper",
            description="Send a private whisper to someone in this chat",
            is_ephemeral=True,
        ),
        BotCommand(
            command="psst",
            description="Send a private whisper to someone in this chat",
            is_ephemeral=True,
        ),
        BotCommand(command="help", description="How to use Psst! Whisper Bot"),
    ]
    try:
        await bot.set_my_commands(
            commands=group_commands,
            scope=BotCommandScopeAllGroupChats(),
        )
        logger.info("ephemeral_group_commands_registered")
    except Exception as exc:
        logger.warning("could_not_set_group_commands", error=str(exc))


async def run_bot() -> None:
    """Initialize dependencies and start bot polling."""
    settings = get_settings()
    setup_logging(log_level=settings.log_level, app_env=settings.app_env)

    logger.info(
        "starting_whisper_bot",
        env=settings.app_env,
        log_level=settings.log_level,
    )

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN),
    )

    storage: WhisperStorageProtocol | None = None
    whisper_service: WhisperService | None = None
    cleanup_task: asyncio.Task[None] | None = None

    try:
        if settings.storage_backend.lower() == "memory":
            storage = MemoryWhisperStorage()
            logger.info("storage_backend_initialized", backend="memory")
        else:
            sqlite_storage = SqliteWhisperStorage(db_path=settings.sqlite_db_path)
            try:
                await sqlite_storage.init_db()
            except Exception as exc:
                logger.error(
                    "storage_initialization_failed",
                    backend="sqlite",
                    db_path=settings.sqlite_db_path,
                    error=str(exc),
                )
                raise
            storage = sqlite_storage
            logger.info(
                "storage_backend_initialized",
                backend="sqlite",
                db_path=settings.sqlite_db_path,
            )

        whisper_service = WhisperService(
            storage=storage,
            default_ttl_seconds=settings.default_whisper_ttl_seconds,
        )

        channel_logger = ChannelLogger(bot=bot, log_channel=settings.log_channel)
        if channel_logger.is_enabled:
            logger.info("whisper_channel_logger_enabled", log_channel=settings.log_channel)
        else:
            logger.info("whisper_channel_logger_disabled_no_channel_configured")

        dp = Dispatcher()

        # Provide services via workflow data
        dp["whisper_service"] = whisper_service
        dp["channel_logger"] = channel_logger

        # Register Middlewares
        dp.update.outer_middleware(StructlogEventMiddleware())
        dp.callback_query.middleware(ThrottlingMiddleware(settings.rate_limit_seconds))

        # Register Routers
        dp.include_router(common_router)
        dp.include_router(inline_router)
        dp.include_router(callbacks_router)
        dp.include_router(group_router)

        # Register commands with Telegram Bot API
        await setup_bot_commands(bot)

        # Start cleanup background task
        cleanup_task = asyncio.create_task(
            whisper_service.run_cleanup_worker(settings.cleanup_interval_seconds)
        )

        bot_info = await bot.get_me()
        logger.info(
            "bot_connected",
            username=bot_info.username,
            name=bot_info.first_name,
            supports_inline=bot_info.supports_inline_queries,
        )

        # Resolve update types used by handlers and log them
        allowed_updates = dp.resolve_used_update_types()
        logger.info("polling_with_allowed_updates", allowed_updates=allowed_updates)

        # Drop pending updates before polling to avoid processing backlog
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot, allowed_updates=allowed_updates)
    finally:
        logger.info("shutting_down_bot")
        if whisper_service is not None:
            whisper_service.stop_cleanup_worker()
        if cleanup_task is not None:
            cleanup_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await cleanup_task
        if isinstance(storage, SqliteWhisperStorage):
            await storage.close()
        await bot.session.close()
        logger.info("bot_shutdown_complete")


def main() -> None:
    """Script entry point."""
    try:
        asyncio.run(run_bot())
    except (KeyboardInterrupt, SystemExit):
        logger.info("bot_stopped_by_user")
        sys.exit(0)


if __name__ == "__main__":
    main()
