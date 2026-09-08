"""Inline query handlers for creating whispers anywhere in Telegram."""

import secrets

from aiogram import Router
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

    # If query is completely empty: show usage instructions
    if not raw:
        article = InlineQueryResultArticle(
            id="hint_empty",
            title="🤫 How to send a Whisper",
            description="Type: @recipient secret message",
            input_message_content=InputTextMessageContent(
                message_text=(
                    "🤫 **How to send a Whisper with Psst!**\n\n"
                    "Type in any chat:\n"
                    "`@psst_whisper_bot @username your secret message`\n\n"
                    "Only `@username` will be able to read what you wrote!"
                ),
                parse_mode="Markdown",
            ),
        )
        await inline_query.answer([article], cache_time=1, is_personal=True)
        return

    parsed = parse_whisper_query(raw)

    # If no recipient or no message text: show guidance prompt
    if not parsed.is_valid:
        desc = (
            "Missing secret message text"
            if parsed.has_targets
            else "Specify a recipient username (e.g. @username)"
        )
        article = InlineQueryResultArticle(
            id="hint_invalid",
            title="⚠️ Incomplete Whisper Query",
            description=desc,
            input_message_content=InputTextMessageContent(
                message_text=(
                    "💡 **Format Reminder:**\n"
                    "`@psst_whisper_bot @username secret message`\n\n"
                    "For one-time self-destructing whispers:\n"
                    "`@psst_whisper_bot !1 @username secret message`"
                ),
                parse_mode="Markdown",
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

    std_card = InlineQueryResultArticle(
        id=std_id,
        title=f"🤫 Whisper for {targets_display}",
        description=f"Secret message for {targets_display}. Click to send.",
        input_message_content=InputTextMessageContent(
            message_text=(
                f"🤫 **A whisper has been sent for {targets_display}!**\n\n"
                "_Only the authorized recipient(s) and the sender can open this message._"
            ),
            parse_mode="Markdown",
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
                f"👁️ **A One-Time Whisper has been sent for {targets_display}!**\n\n"
                "_💥 This whisper will self-destruct once opened._"
            ),
            parse_mode="Markdown",
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
