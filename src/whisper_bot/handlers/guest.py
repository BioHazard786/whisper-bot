"""Guest Mode handlers for interacting in chats without joining as a member."""

import re
import secrets

from aiogram import Bot, Router
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InlineQueryResultArticle,
    InputTextMessageContent,
    Message,
)

from whisper_bot.logger import get_logger
from whisper_bot.services.whisper_service import WhisperService
from whisper_bot.utils.query_parser import parse_whisper_query

logger = get_logger(__name__)
guest_router = Router(name="guest_router")


@guest_router.guest_message()
async def handle_guest_message(
    message: Message,
    bot: Bot,
    whisper_service: WhisperService,
) -> None:
    """Handle messages directed to the bot via Telegram Guest Mode."""
    guest_query_id = message.guest_query_id
    if not guest_query_id:
        return

    user = message.from_user
    if not user:
        return

    raw_text = message.text or ""
    entities = message.entities or []
    extra_user_ids: set[int] = set()
    extra_usernames: set[str] = set()
    mention_spans: list[tuple[int, int]] = []

    # Extract targets from text_mention and text_link entities
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

    # Strip mention spans from text
    clean_text = raw_text
    for start, end in sorted(mention_spans, reverse=True):
        clean_text = clean_text[:start] + clean_text[end:]

    # Strip the bot's own username mention (e.g. @psst_whisper_bot)
    try:
        bot_user = await bot.get_me()
        bot_username = bot_user.username or ""
    except Exception:
        bot_username = ""

    if bot_username:
        clean_text = re.sub(rf"(?i)@{re.escape(bot_username)}\b", "", clean_text).strip()

    parsed = parse_whisper_query(clean_text)
    parsed.target_user_ids.update(extra_user_ids)
    parsed.target_usernames.update(extra_usernames)

    # Fallback to reply_to_message:
    if not parsed.has_targets and message.reply_to_message and message.reply_to_message.from_user:
        replied_user = message.reply_to_message.from_user
        parsed.target_user_ids.add(replied_user.id)
        if replied_user.username:
            parsed.target_usernames.add(replied_user.username.lower())

    if not parsed.is_valid:
        guide_card = InlineQueryResultArticle(
            id=f"guide_{secrets.token_urlsafe(4)}",
            title="💡 How to Send a Guest Whisper",
            input_message_content=InputTextMessageContent(
                message_text=(
                    f"💡 **@{user.username or user.first_name}**, to send a whisper in Guest Mode:\n"
                    f"• Mention recipient: `@{bot_username or 'psst_whisper_bot'} @recipient secret message`\n"
                    f"• Or reply to their message: `@{bot_username or 'psst_whisper_bot'} secret message`\n"
                    f"• Add `!1` for self-destructing: `@{bot_username or 'psst_whisper_bot'} !1 secret`"
                ),
                parse_mode="Markdown",
            ),
        )
        await bot.answer_guest_query(guest_query_id=guest_query_id, result=guide_card)
        return

    targets_display = ", ".join(
        [f"@{u}" for u in sorted(parsed.target_usernames)]
        + [f"ID:{i}" for i in sorted(parsed.target_user_ids)]
    )

    whisper_id = f"g_{secrets.token_urlsafe(6)}"
    whisper = await whisper_service.create_whisper(
        sender_id=user.id,
        sender_first_name=user.first_name,
        sender_username=user.username,
        text=parsed.text,
        target_usernames=parsed.target_usernames,
        target_user_ids=parsed.target_user_ids,
        is_one_time=parsed.is_one_time,
        allow_sender_view=parsed.allow_sender_view,
        custom_id=whisper_id,
        chat_id=message.chat.id if message.chat else None,
    )

    open_btn_text = "💣 Open One-Time Whisper" if parsed.is_one_time else "🔒 Open Whisper"
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

    destruct_notice = " _(💥 Self-destructs after reading)_" if parsed.is_one_time else ""
    card_text = (
        f"🤫 **{user.first_name}** sent a private whisper for **{targets_display}**!{destruct_notice}\n\n"
        "_Click below to view. Only authorized recipients can unlock it._"
    )

    result_card = InlineQueryResultArticle(
        id=whisper.id,
        title=f"🤫 Whisper for {targets_display}",
        input_message_content=InputTextMessageContent(
            message_text=card_text,
            parse_mode="Markdown",
        ),
        reply_markup=kb,
    )

    sent_guest = await bot.answer_guest_query(
        guest_query_id=guest_query_id,
        result=result_card,
    )

    if sent_guest and sent_guest.inline_message_id:
        await whisper_service.bind_inline_message(whisper.id, sent_guest.inline_message_id)
        logger.info(
            "guest_whisper_bound",
            whisper_id=whisper.id,
            inline_message_id=sent_guest.inline_message_id,
        )
