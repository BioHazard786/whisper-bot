"""Handlers package."""

from whisper_bot.handlers.callbacks import callbacks_router
from whisper_bot.handlers.common import common_router
from whisper_bot.handlers.group import group_router
from whisper_bot.handlers.guest import guest_router
from whisper_bot.handlers.inline import inline_router

__all__ = [
    "callbacks_router",
    "common_router",
    "group_router",
    "guest_router",
    "inline_router",
]
