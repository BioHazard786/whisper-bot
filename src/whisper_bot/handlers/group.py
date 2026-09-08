"""Group chat command handlers with ephemeral support."""

import html
import re

from aiogram import Bot, Router
from aiogram.enums import ParseMode
from aiogram.filters import Filter
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from whisper_bot.logger import get_logger
from whisper_bot.services.whisper_service import WhisperService
from whisper_bot.utils.query_parser import parse_whisper_query

logger = get_logger(__name__)
group_router = Router(name="group_router")


class GroupWhisperFilter(Filter):
    """Matches /whisper, /psst commands or direct @bot mentions in groups."""

    async def __call__(self, message: Message, bot: Bot) -> bool:
        if not message.chat or message.chat.type not in ("group", "supergroup"):
            return False
        text = message.text or message.caption or ""
        if not text:
            return False

        # 1. Slash commands /whisper or /psst
        if text.startswith(("/whisper", "/psst")):
            return True

        # 2. Check for bot mention in entities or text
        try:
            bot_user = await bot.get_me()
            username = getattr(bot_user, "username", None)
            bot_username = username.lower() if isinstance(username, str) else ""
        except Exception:
            bot_username = ""

        if bot_username:
            for ent in message.entities or []:
                if ent.type == "mention":
                    handle = text[ent.offset : ent.offset + ent.length].lower()
                    if handle == f"@{bot_username}":
                        return True
                elif ent.type == "text_mention" and ent.user and ent.user.id == bot.id:
                    return True

            if f"@{bot_username}" in text.lower():
                return True

        return False


@group_router.message(GroupWhisperFilter())
async def handle_group_whisper_command(
    message: Message,
    bot: Bot,
    whisper_service: WhisperService,
) -> None:
    """Handle /whisper, /psst commands, or @bot mentions in groups."""
    raw_text = message.text or ""
    entities = message.entities or []
    extra_user_ids: set[int] = set()
    extra_usernames: set[str] = set()
    mention_spans: list[tuple[int, int]] = []

    # Extract targets from text_mention entities (users tagged without username)
    for ent in entities:
        if ent.type == "text_mention" and ent.user:
            extra_user_ids.add(ent.user.id)
            if ent.user.username:
                extra_usernames.add(ent.user.username.lower())
            mention_spans.append((ent.offset, ent.offset + ent.length))
        elif ent.type == "text_link" and ent.url and "tg://user?id=" in ent.url:
            m = re.search(r"tg://user\?id=(\d+)", ent.url)
            if m:
                extra_user_ids.add(int(m.group(1)))
                mention_spans.append((ent.offset, ent.offset + ent.length))

    # Remove text-mention spans from back to front to preserve offsets
    clean_text = raw_text
    for start, end in sorted(mention_spans, reverse=True):
        clean_text = clean_text[:start] + clean_text[end:]

    # Strip the bot's own username mention if present
    try:
        bot_user = await bot.get_me()
        raw_uname = getattr(bot_user, "username", None)
        bot_username = raw_uname if isinstance(raw_uname, str) else ""
    except Exception:
        bot_username = ""

    if bot_username:
        clean_text = re.sub(rf"(?i)@{re.escape(bot_username)}\b", "", clean_text).strip()

    # Strip the command prefix e.g. /whisper or /whisper@psst_whisper_bot
    clean_text = re.sub(r"^[./]?(?:whisper|psst)\b", "", clean_text, flags=re.I).strip()
    clean_text = clean_text.lstrip(".,!?:; ").strip()
    args = clean_text

    user = message.from_user
    if not user:
        return

    # Attempt to delete the command message to guarantee privacy on legacy clients
    try:
        await message.delete()
    except Exception as del_err:
        logger.debug("could_not_delete_command_message", error=str(del_err))

    parsed = parse_whisper_query(args)
    parsed.target_user_ids.update(extra_user_ids)
    parsed.target_usernames.update(extra_usernames)

    # Fallback: If no targets specified in text, check if message is a reply to another user
    if not parsed.has_targets and message.reply_to_message and message.reply_to_message.from_user:
        replied_user = message.reply_to_message.from_user
        parsed.target_user_ids.add(replied_user.id)
        if replied_user.username:
            parsed.target_usernames.add(replied_user.username.lower())

    if not parsed.is_valid:
        user_display = html.escape(user.username or user.first_name, quote=False)
        guide_text = (
            f"💡 <b>@{user_display}</b>, to send a whisper, use:\n"
            "<code>/whisper @username your secret message</code>\n"
            "<code>/whisper 12345678,87654321 your secret message</code>\n\n"
            "Or use inline mode in any chat:\n"
            "<code>@psst_whisper_bot @username your secret message</code>\n"
            "<code>@psst_whisper_bot 12345678 87654321 your secret message</code>"
        )
        await message.answer(guide_text, parse_mode=ParseMode.HTML)
        return

    targets_display = ", ".join(
        [f"@{u}" for u in sorted(parsed.target_usernames)]
        + [f"ID:{i}" for i in sorted(parsed.target_user_ids)]
    )

    # Create the whisper in service
    whisper = await whisper_service.create_whisper(
        sender_id=user.id,
        sender_first_name=user.first_name,
        sender_username=user.username,
        text=parsed.text,
        target_usernames=parsed.target_usernames,
        target_user_ids=parsed.target_user_ids,
        is_one_time=parsed.is_one_time,
        allow_sender_view=parsed.allow_sender_view,
        chat_id=message.chat.id,
    )

    # Post public notification into group chat
    open_btn_text = "💣 Open One-Time Whisper" if parsed.is_one_time else "📬 Open Whisper"
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=open_btn_text,
                    callback_data=f"w:{whisper.id}:open",
                ),
                InlineKeyboardButton(
                    text="🗑️ Delete",
                    callback_data=f"w:{whisper.id}:delete",
                ),
            ]
        ]
    )

    sender_name = html.escape(user.first_name, quote=False)
    escaped_targets = html.escape(targets_display, quote=False)
    destruct_notice = " <i>(💥 Self-destructs after reading)</i>" if parsed.is_one_time else ""
    announcement = (
        f"🤫 <b>{sender_name}</b> sent a private whisper for <b>{escaped_targets}</b>!{destruct_notice}\n\n"
        "<i>Click below to view. Only authorized recipients can unlock it.</i>"
    )

    sent_msg = await bot.send_message(
        chat_id=message.chat.id,
        text=announcement,
        reply_markup=kb,
        parse_mode=ParseMode.HTML,
    )
    whisper.group_message_id = sent_msg.message_id
    await whisper_service._storage.update(whisper)
