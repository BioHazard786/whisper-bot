"""Group chat command handlers with ephemeral support."""

import html
import re

from aiogram import Bot, F, Router
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.filters.command import CommandObject
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


@group_router.message(
    Command("whisper", "psst", ignore_case=True),
    F.chat.type.in_({"group", "supergroup"}),
)
async def handle_group_whisper_command(
    message: Message,
    bot: Bot,
    whisper_service: WhisperService,
    command: CommandObject | None = None,
) -> None:
    """Handle /whisper or /psst slash commands in group chats."""
    user = message.from_user
    if not user:
        return

    raw_text = message.text or message.caption or ""
    entities = message.entities or []
    extra_user_ids: set[int] = set()
    extra_usernames: set[str] = set()
    mention_spans: list[tuple[int, int]] = []

    # Extract targets from text_mention entities (users tagged without username)
    for ent in entities:
        if ent.type == "text_mention" and ent.user:
            if not ent.user.is_bot:
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

    # Strip the slash command prefix e.g. /whisper or /whisper@psst_whisper_bot or /psst
    clean_text = re.sub(r"^/(?:whisper|psst)(?:@\w+)?(?:\s+|$)", "", clean_text, flags=re.I).strip()
    clean_text = clean_text.lstrip(".,!?:; ").strip()
    args = clean_text

    # Attempt to delete the command message to guarantee privacy on legacy clients
    try:
        await message.delete()
    except Exception as del_err:
        logger.debug("could_not_delete_command_message", error=str(del_err))

    parsed = parse_whisper_query(args)
    parsed.target_user_ids.update(extra_user_ids)
    parsed.target_usernames.update(extra_usernames)

    if not parsed.is_valid:
        user_display = html.escape(user.username or user.first_name, quote=False)
        guide_text = (
            f"💡 <b>@{user_display}</b>, to send a whisper, use:\n"
            "<code>/whisper @username your secret message</code>\n"
            "<code>/whisper 12345678 your secret message</code>\n\n"
            "💡 <i>Tip: Group whispers support long messages (up to 4,096 chars) directly on the timeline without popup dialog limits!</i>\n\n"
            "Or use inline mode in any chat:\n"
            "<code>@psst_whisper_bot @username your secret message</code>"
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
