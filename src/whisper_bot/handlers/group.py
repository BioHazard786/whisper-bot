"""Group chat command handlers with ephemeral support."""

from aiogram import Bot, Router
from aiogram.filters import Command
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


@group_router.message(Command("whisper", "psst"))
async def handle_group_whisper_command(
    message: Message,
    bot: Bot,
    whisper_service: WhisperService,
) -> None:
    """Handle /whisper or /psst commands in groups."""
    raw_text = message.text or ""
    # Strip the command prefix e.g. /whisper or /whisper@psst_whisper_bot
    tokens = raw_text.split(maxsplit=1)
    args = tokens[1] if len(tokens) > 1 else ""

    user = message.from_user
    if not user:
        return

    # Attempt to delete the command message to guarantee privacy on legacy clients
    try:
        await message.delete()
    except Exception as del_err:
        logger.debug("could_not_delete_command_message", error=str(del_err))

    parsed = parse_whisper_query(args)

    if not parsed.is_valid:
        guide_text = (
            f"💡 **@{user.username or user.first_name}**, to send a whisper, use:\n"
            "`/whisper @username your secret message`\n\n"
            "Or use inline mode in any chat:\n"
            "`@psst_whisper_bot @username your secret message`"
        )
        await message.answer(guide_text, parse_mode="Markdown")
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

    destruct_notice = " _(💥 Self-destructs after reading)_" if parsed.is_one_time else ""
    announcement = (
        f"🤫 **{user.first_name}** sent a private whisper for **{targets_display}**!{destruct_notice}\n\n"
        "_Click below to view. Only authorized recipients can unlock it._"
    )

    sent_msg = await bot.send_message(
        chat_id=message.chat.id,
        text=announcement,
        reply_markup=kb,
        parse_mode="Markdown",
    )
    whisper.group_message_id = sent_msg.message_id
    await whisper_service._storage.update(whisper)
