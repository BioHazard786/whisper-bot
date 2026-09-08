"""Guest Mode handlers for interacting in chats without joining as a member."""

import html
import re
import secrets

from aiogram import Bot, Router
from aiogram.enums import ParseMode
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InlineQueryResultArticle,
    InputTextMessageContent,
    Message,
    MessageOriginChannel,
    MessageOriginChat,
    MessageOriginUser,
)

from whisper_bot.logger import get_logger
from whisper_bot.services.whisper_service import WhisperService
from whisper_bot.utils.query_parser import parse_whisper_query

logger = get_logger(__name__)
guest_router = Router(name="guest_router")


def _extract_reply_target(message: Message) -> tuple[int | None, str | None]:
    """Extract the user ID and username from a reply context.

    Checks both ``reply_to_message`` (regular in-chat replies) and
    ``external_reply`` (guest mode replies where the bot isn't a member).

    Returns:
        A ``(user_id, username)`` tuple, either or both may be ``None``.
    """
    # 1. Standard reply_to_message (populated when bot is a chat member)
    if message.reply_to_message:
        if message.reply_to_message.from_user:
            u = message.reply_to_message.from_user
            return u.id, u.username
        if message.reply_to_message.sender_chat:
            sc = message.reply_to_message.sender_chat
            return sc.id, sc.username

    # 2. external_reply — used by Telegram when the bot is NOT a member
    #    (i.e. guest mode). The origin carries the sender information.
    if message.external_reply:
        origin = message.external_reply.origin
        if isinstance(origin, MessageOriginUser):
            u = origin.sender_user
            return u.id, u.username
        if isinstance(origin, MessageOriginChat):
            sc = origin.sender_chat
            return sc.id, sc.username
        if isinstance(origin, MessageOriginChannel):
            sc = origin.chat
            return sc.id, sc.username
        if message.external_reply.chat:
            c = message.external_reply.chat
            return c.id, c.username

    return None, None


@guest_router.guest_message()
async def handle_guest_message(
    message: Message,
    bot: Bot,
    whisper_service: WhisperService,
) -> None:
    """Handle messages directed to the bot via Telegram Guest Mode."""
    guest_query_id = message.guest_query_id
    user = message.from_user
    raw_text = message.text or ""

    # Extract reply target from either reply_to_message or external_reply
    reply_target_id, reply_target_username = _extract_reply_target(message)

    logger.info(
        "guest_message_handler_triggered",
        guest_query_id=guest_query_id,
        user_id=user.id if user else None,
        raw_text=raw_text,
        has_reply_to_message=message.reply_to_message is not None,
        has_external_reply=message.external_reply is not None,
        reply_target_id=reply_target_id,
        reply_target_username=reply_target_username,
    )

    if not guest_query_id:
        logger.warning("guest_message_missing_guest_query_id")
        return

    if not user:
        return

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

    # Also strip optional command prefixes like /whisper, /psst, whisper, psst, or leading punctuation (preserving ! for flags)
    clean_text = re.sub(r"^[./]?(?:whisper|psst)\b", "", clean_text, flags=re.I).strip()
    clean_text = re.sub(r"^[,.:; ]+", "", clean_text).strip()

    parsed = parse_whisper_query(clean_text)
    parsed.target_user_ids.update(extra_user_ids)
    parsed.target_usernames.update(extra_usernames)

    # Fallback to reply context (reply_to_message or external_reply):
    if not parsed.has_targets and reply_target_id is not None:
        parsed.target_user_ids.add(reply_target_id)
        if reply_target_username:
            parsed.target_usernames.add(reply_target_username.lower())

    if not parsed.is_valid:
        user_display = html.escape(user.username or user.first_name, quote=False)
        bot_name = html.escape(bot_username or "psst_whisper_bot", quote=False)
        guide_card = InlineQueryResultArticle(
            id=f"guide_{secrets.token_urlsafe(4)}",
            title="💡 How to Send a Guest Whisper",
            input_message_content=InputTextMessageContent(
                message_text=(
                    f"💡 <b>@{user_display}</b>, to send a whisper in Guest Mode:\n"
                    f"• Mention recipient: <code>@{bot_name} @recipient secret message</code>\n"
                    f"• Or reply to their message: <code>@{bot_name} secret message</code>\n"
                    f"• Add <code>!1</code> for self-destructing: <code>@{bot_name} !1 secret</code>"
                ),
                parse_mode=ParseMode.HTML,
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

    sender_name = html.escape(user.first_name, quote=False)
    escaped_targets = html.escape(targets_display, quote=False)
    destruct_notice = " <i>(💥 Self-destructs after reading)</i>" if parsed.is_one_time else ""
    card_text = (
        f"🤫 <b>{sender_name}</b> sent a private whisper for <b>{escaped_targets}</b>!{destruct_notice}\n\n"
        "<i>Click below to view. Only authorized recipients can unlock it.</i>"
    )

    result_card = InlineQueryResultArticle(
        id=whisper.id,
        title=f"🤫 Whisper for {targets_display}",
        input_message_content=InputTextMessageContent(
            message_text=card_text,
            parse_mode=ParseMode.HTML,
        ),
        reply_markup=kb,
    )

    try:
        sent_guest = await bot.answer_guest_query(
            guest_query_id=guest_query_id,
            result=result_card,
        )
        if sent_guest and getattr(sent_guest, "inline_message_id", None):
            await whisper_service.bind_inline_message(whisper.id, sent_guest.inline_message_id)
            logger.info(
                "guest_whisper_bound",
                whisper_id=whisper.id,
                inline_message_id=sent_guest.inline_message_id,
            )
    except Exception as exc:
        logger.error(
            "guest_query_answer_failed",
            guest_query_id=guest_query_id,
            whisper_id=whisper.id,
            error=str(exc),
            exc_info=True,
        )
        raise
