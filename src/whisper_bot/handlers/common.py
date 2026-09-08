"""Common handlers: /start, /help, /stats, /ping."""

import time

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from whisper_bot.services.whisper_service import WhisperService

common_router = Router(name="common_router")
_START_TIME = time.time()


def get_start_keyboard() -> InlineKeyboardMarkup:
    """Build the start menu keyboard."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🤫 Try Whisper Now",
                    switch_inline_query=" @username psst... secret message",
                ),
            ],
            [
                InlineKeyboardButton(text="📖 How It Works", callback_data="menu:help"),
                InlineKeyboardButton(text="📊 Bot Stats", callback_data="menu:stats"),
            ],
        ]
    )


def get_help_keyboard() -> InlineKeyboardMarkup:
    """Build the help menu keyboard."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🚀 Send Inline Whisper",
                    switch_inline_query=" @username Secret text",
                ),
            ],
            [
                InlineKeyboardButton(text="🔙 Back to Home", callback_data="menu:start"),
            ],
        ]
    )


@common_router.message(CommandStart())
async def handle_start(message: Message) -> None:
    """Handle /start command in private chats."""
    first_name = message.from_user.first_name if message.from_user else "Friend"
    text = (
        f"🤫 **Hey {first_name}, welcome to Psst!**\n\n"
        "I am your privacy-first **Whisper Bot**. I let you send secret, "
        "self-destructing, and ephemeral messages in groups or direct chats.\n\n"
        "🔒 **Key Features:**\n"
        "• **Inline Whispers:** Send whispers in any chat via `@psst_whisper_bot`\n"
        "• **One-Time Whispers:** Self-destructs immediately after reading\n"
        "• **Multi-Target:** Whisper to multiple specific users at once\n"
        "• **Ephemeral Group Commands:** Invisible `/whisper` commands using the latest Bot API\n\n"
        "Tap below to send your first whisper!"
    )
    await message.answer(text, reply_markup=get_start_keyboard(), parse_mode="Markdown")


@common_router.message(Command("help"))
async def handle_help(message: Message) -> None:
    """Handle /help command."""
    text = (
        "📖 **How to Use Psst! Whisper Bot**\n\n"
        "**1. Inline Whisper (Any Chat):**\n"
        "In any chat or group, type:\n"
        "`@psst_whisper_bot @recipient secret message`\n"
        "Tap the result to send a locked whisper card.\n\n"
        "**2. One-Time Self-Destructing Whisper:**\n"
        "When typing inline, pick the **👁️ One-Time Whisper** option or type:\n"
        "`@psst_whisper_bot !1 @recipient secret message`\n"
        "The whisper is permanently destroyed once the recipient opens it!\n\n"
        "**3. Multiple Recipients:**\n"
        "`@psst_whisper_bot @alice @bob secret message`\n\n"
        "**4. Ephemeral Group Messages:**\n"
        "In groups where Psst! is added, type:\n"
        "`/whisper @recipient secret message`\n"
        "Thanks to Bot API Ephemeral Commands, group members cannot see your command!"
    )
    await message.answer(text, reply_markup=get_help_keyboard(), parse_mode="Markdown")


@common_router.callback_query(F.data == "menu:help")
async def handle_help_callback(callback: CallbackQuery) -> None:
    """Handle 'How It Works' inline button."""
    text = (
        "📖 **How to Use Psst! Whisper Bot**\n\n"
        "**1. Inline Whisper (Any Chat):**\n"
        "In any chat, type:\n"
        "`@psst_whisper_bot @recipient secret message`\n\n"
        "**2. One-Time Self-Destructing Whisper:**\n"
        "Pick the **👁️ One-Time Whisper** option or prefix with `!1`:\n"
        "`@psst_whisper_bot !1 @recipient secret message`\n\n"
        "**3. Group Ephemeral Commands:**\n"
        "Type `/whisper @recipient secret message` in a group chat."
    )
    if callback.message and isinstance(callback.message, Message):
        await callback.message.edit_text(
            text, reply_markup=get_help_keyboard(), parse_mode="Markdown"
        )
    await callback.answer()


@common_router.callback_query(F.data == "menu:start")
async def handle_start_callback(callback: CallbackQuery) -> None:
    """Handle 'Back to Home' inline button."""
    first_name = callback.from_user.first_name or "Friend"
    text = (
        f"🤫 **Hey {first_name}, welcome to Psst!**\n\n"
        "I am your privacy-first **Whisper Bot**. Send secret, "
        "self-destructing, and ephemeral messages anywhere."
    )
    if callback.message and isinstance(callback.message, Message):
        await callback.message.edit_text(
            text, reply_markup=get_start_keyboard(), parse_mode="Markdown"
        )
    await callback.answer()


@common_router.callback_query(F.data == "menu:stats")
@common_router.message(Command("stats"))
async def handle_stats(
    event: Message | CallbackQuery,
    whisper_service: WhisperService,
) -> None:
    """Show service statistics."""
    stats = await whisper_service._storage.get_stats()
    uptime_sec = int(time.time() - _START_TIME)
    hours, remainder = divmod(uptime_sec, 3600)
    minutes, seconds = divmod(remainder, 60)

    text = (
        "📊 **Psst! Whisper Bot Statistics**\n\n"
        f"• **Active Whispers in Memory:** {stats['active']}\n"
        f"• **Lifetime Whispers Created:** {stats['lifetime_created']}\n"
        f"• **Expired / Destroyed Whispers:** {stats['expired_or_destroyed']}\n"
        f"• **Bot Uptime:** {hours}h {minutes}m {seconds}s\n"
        f"• **Architecture:** Python 3.11+ | aiogram 3 | structlog"
    )
    back_kb = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🔙 Back", callback_data="menu:start")]]
    )
    if isinstance(event, CallbackQuery):
        if event.message and isinstance(event.message, Message):
            await event.message.edit_text(text, reply_markup=back_kb, parse_mode="Markdown")
        await event.answer()
    else:
        await event.answer(text, reply_markup=back_kb, parse_mode="Markdown")


@common_router.message(Command("ping"))
async def handle_ping(message: Message) -> None:
    """Health check ping command."""
    start = time.perf_counter()
    msg = await message.answer("🏓 Pong!")
    latency_ms = (time.perf_counter() - start) * 1000
    await msg.edit_text(f"🏓 Pong! Latency: `{latency_ms:.1f}ms`", parse_mode="Markdown")
