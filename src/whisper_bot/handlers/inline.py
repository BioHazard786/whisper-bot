"""Inline query handlers for creating whispers anywhere in Telegram."""

import html
import secrets

from aiogram import Router
from aiogram.enums import ParseMode
from aiogram.types import (
    ChosenInlineResult,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InlineQuery,
    InlineQueryResultArticle,
    InputTextMessageContent,
)

from whisper_bot.logger import get_logger
from whisper_bot.services.whisper_service import WhisperService
from whisper_bot.utils.query_parser import parse_whisper_query

logger = get_logger(__name__)
inline_router = Router(name="inline_router")


@inline_router.inline_query()
async def handle_inline_query(
    inline_query: InlineQuery,
    whisper_service: WhisperService,
) -> None:
    """Process inline queries to generate whisper message cards."""
    raw = inline_query.query.strip()
    user = inline_query.from_user
    logger.info(
        "inline_query_received",
        user_id=user.id,
        chat_type=inline_query.chat_type,
        raw_query=raw,
    )

    # If query is completely empty: show usage instructions
    if not raw:
        article = InlineQueryResultArticle(
            id="hint_empty",
            title="🤫 How to send a Whisper",
            description="Type: @recipient secret message",
            input_message_content=InputTextMessageContent(
                message_text=(
                    "🤫 <b>How to send a Whisper with Psst!</b>\n\n"
                    "Type in any chat:\n"
                    "<code>@psst_whisper_bot @username your secret message</code>\n\n"
                    "Only <code>@username</code> will be able to read what you wrote!"
                ),
                parse_mode=ParseMode.HTML,
            ),
        )
        await inline_query.answer([article], cache_time=1, is_personal=True)
        return

    parsed = parse_whisper_query(raw)

    # If no recipient or no message text: show guidance prompt
    if not parsed.is_valid:
        if not parsed.has_targets:
            article = InlineQueryResultArticle(
                id="hint_inline_format",
                title="⚠️ Specify a recipient",
                description="Type: @psst_whisper_bot @recipient secret message",
                input_message_content=InputTextMessageContent(
                    message_text=(
                        "💡 <b>Inline Mode Format Reminder:</b>\n"
                        "<code>@psst_whisper_bot @username secret message</code>\n"
                        "<code>@psst_whisper_bot 12345678 87654321 secret message</code>\n\n"
                        "For one-time self-destructing whispers:\n"
                        "<code>@psst_whisper_bot !1 @username secret message</code>"
                    ),
                    parse_mode=ParseMode.HTML,
                ),
            )
            await inline_query.answer([article], cache_time=1, is_personal=True)
            return

        # Has targets but missing message text
        article = InlineQueryResultArticle(
            id="hint_missing_text",
            title="⚠️ Incomplete Whisper Query",
            description="Missing secret message text. Type your secret after the recipient.",
            input_message_content=InputTextMessageContent(
                message_text="💡 Please type your secret message after the recipient username or ID.",
                parse_mode=ParseMode.HTML,
            ),
        )
        await inline_query.answer([article], cache_time=1, is_personal=True)
        return

    targets_display = ", ".join(
        [f"@{u}" for u in sorted(parsed.target_usernames)]
        + [f"ID:{i}" for i in sorted(parsed.target_user_ids)]
    )

    # 1. Standard Whisper
    std_id = f"s_{secrets.token_urlsafe(6)}"
    await whisper_service.create_whisper(
        sender_id=user.id,
        sender_first_name=user.first_name,
        sender_username=user.username,
        text=parsed.text,
        target_usernames=parsed.target_usernames,
        target_user_ids=parsed.target_user_ids,
        is_one_time=parsed.is_one_time,
        allow_sender_view=parsed.allow_sender_view,
        custom_id=std_id,
    )

    escaped_targets = html.escape(targets_display, quote=False)
    std_card = InlineQueryResultArticle(
        id=std_id,
        title=f"🤫 Whisper for {targets_display}",
        description=f"Secret message for {targets_display}. Click to send.",
        input_message_content=InputTextMessageContent(
            message_text=(
                f"🤫 <b>A whisper has been sent for {escaped_targets}!</b>\n\n"
                "<i>Only the authorized recipient(s) and the sender can open this message.</i>"
            ),
            parse_mode=ParseMode.HTML,
        ),
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="🔒 Open Whisper",
                        callback_data=f"w:{std_id}:open",
                    )
                ]
            ]
        ),
    )

    # 2. One-Time Self-Destruct Whisper
    ot_id = f"o_{secrets.token_urlsafe(6)}"
    await whisper_service.create_whisper(
        sender_id=user.id,
        sender_first_name=user.first_name,
        sender_username=user.username,
        text=parsed.text,
        target_usernames=parsed.target_usernames,
        target_user_ids=parsed.target_user_ids,
        is_one_time=True,
        allow_sender_view=parsed.allow_sender_view,
        custom_id=ot_id,
    )

    ot_card = InlineQueryResultArticle(
        id=ot_id,
        title=f"👁️ One-Time Whisper for {targets_display}",
        description="💥 Self-destructs permanently after recipient opens it!",
        input_message_content=InputTextMessageContent(
            message_text=(
                f"👁️ <b>A One-Time Whisper has been sent for {escaped_targets}!</b>\n\n"
                "<i>💥 This whisper will self-destruct once opened.</i>"
            ),
            parse_mode=ParseMode.HTML,
        ),
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="💣 Open One-Time Whisper",
                        callback_data=f"w:{ot_id}:open",
                    )
                ]
            ]
        ),
    )

    # Answer query with both choices
    await inline_query.answer(
        [std_card, ot_card],
        cache_time=1,
        is_personal=True,
    )


@inline_router.chosen_inline_result()
async def handle_chosen_inline_result(
    chosen: ChosenInlineResult,
    whisper_service: WhisperService,
) -> None:
    """Track chosen inline whisper and bind its inline message ID."""
    whisper_id = chosen.result_id
    if chosen.inline_message_id:
        await whisper_service.bind_inline_message(whisper_id, chosen.inline_message_id)
        logger.info(
            "inline_whisper_bound",
            whisper_id=whisper_id,
            inline_message_id=chosen.inline_message_id,
        )
