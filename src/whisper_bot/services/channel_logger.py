"""Service for logging whispers to an admin-designated Telegram log channel."""

import html

from aiogram import Bot
from aiogram.enums import ParseMode

from whisper_bot.logger import get_logger
from whisper_bot.models.whisper import Whisper

logger = get_logger(__name__)


class ChannelLogger:
    """Sends audit logs of created whispers to a designated Telegram channel."""

    def __init__(self, bot: Bot, log_channel: int | str | None = None) -> None:
        self._bot = bot
        self._log_channel = log_channel

    @property
    def is_enabled(self) -> bool:
        """Check if channel logging is configured."""
        return bool(self._log_channel)

    async def log_whisper(
        self,
        whisper: Whisper,
        mode: str = "group",
        chat_title: str | None = None,
        chat_id: int | None = None,
    ) -> None:
        """Post a whisper log entry to the log channel if configured."""
        if not self._log_channel:
            return

        try:
            sender_name = html.escape(whisper.sender_first_name, quote=False)
            sender_username = (
                f"@{html.escape(whisper.sender_username, quote=False)}"
                if whisper.sender_username
                else "<i>None</i>"
            )
            sender_id = whisper.sender_id
            sender_link = f'<a href="tg://user?id={sender_id}">{sender_name}</a>'

            targets_display = html.escape(whisper.format_targets_display(), quote=False)

            # Escape content and truncate if excessively long for a single Telegram message (max 4096)
            raw_content = whisper.text
            if len(raw_content) > 3000:
                raw_content = raw_content[:3000] + "\n... [Content truncated for log]"
            escaped_content = html.escape(raw_content, quote=False)

            mode_display = "👥 Group Command" if mode == "group" else "⚡ Inline Query"
            type_display = "💣 One-Time Self-Destruct" if whisper.is_one_time else "📬 Standard Whisper"

            chat_info = ""
            if chat_title or chat_id:
                title = html.escape(chat_title, quote=False) if chat_title else "Chat"
                chat_info = f"\n• <b>Chat:</b> {title} (<code>{chat_id}</code>)"

            log_text = (
                "🔒 <b>Whisper Logged</b>\n\n"
                f"📝 <b>Content:</b>\n"
                f"<blockquote>{escaped_content}</blockquote>\n\n"
                f"👤 <b>From:</b>\n"
                f"• <b>User:</b> {sender_link}\n"
                f"• <b>Username:</b> {sender_username}\n"
                f"• <b>ID:</b> <code>{sender_id}</code>\n\n"
                f"🎯 <b>To:</b> <b>{targets_display}</b>\n\n"
                f"⚙️ <b>Details:</b>\n"
                f"• <b>Mode:</b> {mode_display}\n"
                f"• <b>Type:</b> {type_display}\n"
                f"• <b>Whisper ID:</b> <code>{whisper.id}</code>"
                f"{chat_info}"
            )

            await self._bot.send_message(
                chat_id=self._log_channel,
                text=log_text,
                parse_mode=ParseMode.HTML,
            )
            logger.info(
                "whisper_logged_to_channel",
                whisper_id=whisper.id,
                channel=self._log_channel,
            )
        except Exception as exc:
            logger.error(
                "failed_to_log_whisper_to_channel",
                whisper_id=whisper.id,
                channel=self._log_channel,
                error=str(exc),
            )
