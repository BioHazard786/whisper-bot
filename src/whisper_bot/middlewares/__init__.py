"""Middlewares package."""

from whisper_bot.middlewares.logging import StructlogEventMiddleware
from whisper_bot.middlewares.throttling import ThrottlingMiddleware

__all__ = ["StructlogEventMiddleware", "ThrottlingMiddleware"]
