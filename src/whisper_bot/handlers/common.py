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
        "• <b>Guest Mode (No Joining!):</b> Reply to anyone or mention <code>@psst_whisper_bot</code> in any chat\n"
        "• <b>Inline Whispers:</b> Type <code>@psst_whisper_bot @user secret</code> in any chat\n"
        "• <b>Group Commands:</b> Invisible <code>/whisper @user secret</code> commands\n"
        "• <b>User IDs &amp; No-Username:</b> Whisper using numeric IDs (<code>12345678</code>) or by replying\n"
        "• <b>One-Time Whispers:</b> Add <code>!1</code> to permanently self-destruct after reading\n\n"
        "Tap below to send your first whisper!"
    )
    await message.answer(text, reply_markup=get_start_keyboard(), parse_mode=ParseMode.HTML)


@common_router.message(Command("help"))
async def handle_help(message: Message) -> None:
    """Handle /help command."""
    text = (
        "📖 **How to Use Psst! Whisper Bot**\n\n"
        "**1. Guest Mode (Works Anywhere Without Adding Bot):**\n"
        "• **Reply to Any Message:** Swipe to reply to someone's message and type:\n"
        "`@psst_whisper_bot secret message`\n"
        "*(Works even if the user has no username!)*\n"
        "• **Mention Recipient:** In any chat, type:\n"
        "`@psst_whisper_bot @recipient secret message`\n\n"
        "**2. Inline Whispers (Any Chat):**\n"
        "Type `@psst_whisper_bot @recipient secret message` and tap the locked card to send.\n\n"
        "**3. One-Time Self-Destructing Whispers:**\n"
        "Add `!1` to destroy the whisper as soon as it's read:\n"
        "`@psst_whisper_bot !1 @recipient secret message`\n\n"
        "**4. User IDs & Multiple Targets (Advanced):**\n"
        "Pass numeric IDs, Telegram links, or multiple targets:\n"
        "`@psst_whisper_bot 12345678 secret message`\n"
        "`@psst_whisper_bot @alice 12345678 id:99999999 secret message`\n\n"
        "**5. Ephemeral Group Commands:**\n"
        "In groups where Psst! is added, type `/whisper @recipient secret message`.\n"
        "Telegram hides your command from other members!"
    )
    await message.answer(text, reply_markup=get_help_keyboard(), parse_mode="Markdown")


@common_router.callback_query(F.data == "menu:help")
async def handle_help_callback(callback: CallbackQuery) -> None:
    """Handle 'How It Works' inline button."""
    text = (
        "📖 **How to Use Psst! Whisper Bot**\n\n"
        "**1. Guest Mode (No Joining Needed!):**\n"
        "• Reply to any message: `@psst_whisper_bot secret text`\n"
        "• Or mention: `@psst_whisper_bot @recipient secret text`\n\n"
        "**2. Inline Whispers:**\n"
        "Type `@psst_whisper_bot @recipient secret text` in any chat.\n\n"
        "**3. One-Time Whispers:**\n"
        "Add `!1` prefix to self-destruct once opened.\n\n"
        "**4. Group Commands:**\n"
        "Type `/whisper @recipient secret text` in a group chat."
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
