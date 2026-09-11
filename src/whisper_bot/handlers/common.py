"""Common handlers: /start, /help, /stats, /ping."""

import html
import time

from aiogram import F, Router
from aiogram.enums import ParseMode
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
    raw_name = message.from_user.first_name if message.from_user else "Friend"
    first_name = html.escape(raw_name, quote=False)
    text = (
        f"🤫 <b>Hey {first_name}, welcome to Psst!</b>\n\n"
        "I am your privacy-first <b>Whisper Bot</b>. Send secret, "
        "self-destructing, and ephemeral messages anywhere across Telegram.\n\n"
        "🔒 <b>Ways to Whisper:</b>\n"
        "• <b>Group Commands (Long Whispers):</b> Send <code>/whisper @user secret</code> or <code>/psst @user secret</code> in groups. "
        "Delivered directly onto the timeline with support for <b>long messages (up to 4,096 chars)</b> without dialog box limits!\n"
        "• <b>Inline Whispers:</b> Type <code>@psst_whisper_bot @user secret</code> in any chat (opens in an alert popup dialog, best for short messages)\n"
        "• <b>User IDs &amp; Deep Links:</b> Whisper using numeric IDs (<code>12345678</code>) or mention links\n"
        "• <b>One-Time Whispers:</b> Add <code>!1</code> to permanently self-destruct after reading\n\n"
        "Tap below to send your first whisper!"
    )
    await message.answer(text, reply_markup=get_start_keyboard(), parse_mode=ParseMode.HTML)


@common_router.message(Command("help"))
async def handle_help(message: Message) -> None:
    """Handle /help command."""
    text = (
        "📖 **How to Use Psst! Whisper Bot**\n\n"
        "**1. Ephemeral Group Commands (`/whisper` or `/psst`) — Supports Long Whispers:**\n"
        "In groups where Psst! is added, send a private whisper to someone:\n"
        "`/whisper @recipient your secret message`\n"
        "✨ **Advantage:** Group whispers render directly on the recipient's chat timeline ephemerally, "
        "supporting **long whispers (up to 4,096 characters)** and rich text! Unlike inline mode, "
        "your message will never get cut off by popup dialog limits.\n\n"
        "**2. Inline Whispers (Any Chat):**\n"
        "Type `@psst_whisper_bot @recipient secret message` anywhere (private chats, channels, groups) and tap the locked card.\n"
        "*(Note: Inline whispers open in Telegram's alert popup dialog, which has character length limits. Use group commands for longer messages!)*\n\n"
        "**3. One-Time Self-Destructing Whispers:**\n"
        "Add `!1` to permanently self-destruct as soon as read:\n"
        "`/whisper !1 @recipient secret message`\n"
        "`@psst_whisper_bot !1 @recipient secret message`\n\n"
        "**4. User IDs & Multiple Targets:**\n"
        "Target users by numeric ID or combine multiple targets:\n"
        "`/whisper 12345678 secret message`\n"
        "`@psst_whisper_bot @alice 12345678 id:99999999 secret message`"
    )
    await message.answer(text, reply_markup=get_help_keyboard(), parse_mode="Markdown")


@common_router.callback_query(F.data == "menu:help")
async def handle_help_callback(callback: CallbackQuery) -> None:
    """Handle 'How It Works' inline button."""
    text = (
        "📖 **How to Use Psst! Whisper Bot**\n\n"
        "**1. Group Commands (`/whisper` or `/psst`) — Long Whispers:**\n"
        "`/whisper @recipient secret text`\n"
        "Delivered directly to the chat timeline with support for long messages (up to 4,096 chars) without dialog box limits!\n\n"
        "**2. Inline Whispers (Any Chat):**\n"
        "Type `@psst_whisper_bot @recipient secret text` in any chat (displayed in alert popup dialog, best for short notes).\n\n"
        "**3. One-Time Whispers:**\n"
        "Add `!1` to self-destruct once opened."
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
