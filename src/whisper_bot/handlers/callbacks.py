"""Callback query handlers for opening, deleting, and managing whispers."""

import html

from aiogram import Bot, F, Router
from aiogram.enums import ParseMode
from aiogram.types import (
    CallbackQuery,
    EphemeralMessageParameters,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    ReplyParameters,
)

from whisper_bot.logger import get_logger
from whisper_bot.services.whisper_service import WhisperService

logger = get_logger(__name__)
callbacks_router = Router(name="callbacks_router")


@callbacks_router.callback_query(F.data.startswith("w:"))
async def handle_whisper_callback(
    callback: CallbackQuery,
    bot: Bot,
    whisper_service: WhisperService,
) -> None:
    """Handle whisper open and action callback clicks."""
    data = callback.data or ""
    parts = data.split(":")
    if len(parts) < 3:
        await callback.answer("⚠️ Invalid request.", show_alert=True)
        return

    _, whisper_id, action = parts[0], parts[1], parts[2]
    user = callback.from_user

    # Handle clicks on already destroyed buttons
    if action == "destroyed":
        await callback.answer(
            "💥 This one-time whisper has already been opened and destroyed.",
            show_alert=True,
        )
        return

    # Handle delete action
    if action == "delete":
        deleted = await whisper_service.delete_whisper(whisper_id, user.id)
        if deleted:
            await callback.answer("🗑️ Your whisper has been deleted.", show_alert=True)
            # Update markup if possible
            if callback.inline_message_id:
                try:
                    await bot.edit_message_reply_markup(
                        inline_message_id=callback.inline_message_id,
                        reply_markup=InlineKeyboardMarkup(
                            inline_keyboard=[
                                [
                                    InlineKeyboardButton(
                                        text="🗑️ Deleted by Sender",
                                        callback_data=f"w:{whisper_id}:destroyed",
                                    )
                                ]
                            ]
                        ),
                    )
                except Exception as e:
                    logger.debug("inline_markup_edit_failed", error=str(e))
            elif callback.message and isinstance(callback.message, Message):
                try:
                    await callback.message.edit_reply_markup(
                        reply_markup=InlineKeyboardMarkup(
                            inline_keyboard=[
                                [
                                    InlineKeyboardButton(
                                        text="🗑️ Deleted by Sender",
                                        callback_data=f"w:{whisper_id}:destroyed",
                                    )
                                ]
                            ]
                        )
                    )
                except Exception as e:
                    logger.debug("group_markup_edit_failed", error=str(e))
        else:
            await callback.answer(
                "⛔ Only the original sender can delete this whisper.",
                show_alert=True,
            )
        return

    # Handle open action
    if action == "open":
        whisper, authorized, result = await whisper_service.access_whisper(
            whisper_id=whisper_id,
            user_id=user.id,
            username=user.username,
        )

        if not authorized:
            if result == "not_found":
                await callback.answer(
                    "⚠️ This whisper does not exist or has expired.",
                    show_alert=True,
                )
            elif result == "expired":
                await callback.answer(
                    "⏳ This whisper has expired.",
                    show_alert=True,
                )
            elif result == "destroyed":
                await callback.answer(
                    "💥 This one-time whisper has already been opened and destroyed.",
                    show_alert=True,
                )
            elif result == "already_read":
                await callback.answer(
                    "💥 You have already viewed your one-time copy of this whisper.",
                    show_alert=True,
                )
            elif result == "unauthorized":
                targets = whisper.format_targets_display() if whisper else "another user"
                await callback.answer(
                    f"⛔ This whisper is not for you!\nIntended recipient(s): {targets}",
                    show_alert=True,
                )
            return

        secret_text = result
        sender_name = whisper.sender_first_name if whisper else "Someone"

        # Ephemeral Group delivery vs Modal Alert
        delivered_ephemerally = False

        if (
            callback.message
            and isinstance(callback.message, Message)
            and callback.message.chat
            and callback.message.chat.id < 0
        ):
            # We are in a group chat context with a chat_id and an active callback_query_id.
            # Utilize native Telegram Bot API Ephemeral Messages!
            try:
                sender_display = html.escape(sender_name, quote=False)
                escaped_secret = html.escape(secret_text, quote=False)
                await bot.send_message(
                    chat_id=callback.message.chat.id,
                    text=f"🤫 <b>Whisper from {sender_display}:</b>\n\n{escaped_secret}",
                    parse_mode=ParseMode.HTML,
                    ephemeral_message_parameters=EphemeralMessageParameters(
                        receiver_user_id=user.id,
                        callback_query_id=callback.id,
                    ),
                    reply_parameters=ReplyParameters(message_id=callback.message.message_id),
                )
                delivered_ephemerally = True
                await callback.answer("🤫 Whisper displayed in your timeline!")
            except Exception as ephemeral_exc:
                logger.info(
                    "ephemeral_delivery_fallback_to_alert",
                    chat_id=callback.message.chat.id,
                    error=str(ephemeral_exc),
                )

        if not delivered_ephemerally:
            # Inline message or client fallback: use Telegram secure alert popup
            await callback.answer(
                f"🤫 Whisper from {sender_name}:\n\n{secret_text}",
                show_alert=True,
            )

        # If one-time whisper and destroyed, update button text
        if whisper and whisper.is_destroyed:
            destroyed_markup = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="💥 Opened & Destroyed",
                            callback_data=f"w:{whisper_id}:destroyed",
                        )
                    ]
                ]
            )
            if callback.inline_message_id:
                try:
                    await bot.edit_message_reply_markup(
                        inline_message_id=callback.inline_message_id,
                        reply_markup=destroyed_markup,
                    )
                except Exception as e:
                    logger.debug("inline_destroy_markup_failed", error=str(e))
            elif callback.message and isinstance(callback.message, Message):
                try:
                    await callback.message.edit_reply_markup(reply_markup=destroyed_markup)
                except Exception as e:
                    logger.debug("group_destroy_markup_failed", error=str(e))
