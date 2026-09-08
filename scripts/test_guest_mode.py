"""Standalone test script using python-telegram-bot 22.8 to test Telegram Guest Mode.

Usage:
    uv run python scripts/test_guest_mode.py
"""

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InlineQueryResultArticle,
    InputTextMessageContent,
    Update,
)
from telegram.ext import (
    Application,
    ContextTypes,
    MessageHandler,
    TypeHandler,
    filters,
)

from whisper_bot.config import get_settings


async def raw_update_logger(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log every incoming update from Telegram with its exact payload type."""
    update_type = "unknown"
    if update.guest_message:
        update_type = "guest_message (GUEST MODE ✨)"
    elif update.message:
        update_type = "message (regular in-chat message)"
    elif update.inline_query:
        update_type = "inline_query"
    elif update.callback_query:
        update_type = "callback_query"

    print(f"\n📥 [UPDATE #{update.update_id}] Received event_type: {update_type}")


async def handle_guest_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle incoming guest_message updates sent via Telegram Guest Mode."""
    msg = update.guest_message
    if not msg:
        return

    query_id = msg.guest_query_id
    user = msg.from_user
    chat = msg.chat
    text = msg.text or msg.caption or ""

    print("\n" + "=" * 60)
    print("🎉 GUEST MESSAGE RECEIVED VIA TELEGRAM GUEST MODE!")
    print(f"  • Guest Query ID: {query_id}")
    print(f"  • Sender: {user.first_name if user else 'Unknown'} (ID: {user.id if user else '?'})")
    print(f"  • Chat: {chat.title or chat.type} (ID: {chat.id}, Type: {chat.type})")
    print(f"  • Raw Text: {text!r}")

    # Inspect reply context
    if msg.reply_to_message:
        replied_user = msg.reply_to_message.from_user
        print(
            f"  • Reply Target (reply_to_message): {replied_user.first_name if replied_user else '?'} (ID: {replied_user.id if replied_user else '?'})"
        )
    if getattr(msg, "external_reply", None):
        print(f"  • External Reply: {msg.external_reply}")
    print("=" * 60)

    if not query_id:
        print("❌ Missing guest_query_id, cannot answer.")
        return

    # Build response article
    card_text = (
        f"🤫 **Psst Guest Mode Active!**\n\n"
        f"Received guest whisper from **{user.first_name if user else 'Anonymous'}**!\n"
        f"Content: `{text}`\n\n"
        f"_This message was posted directly via Telegram Bot API Guest Mode._"
    )

    kb = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("🔒 Test Button", callback_data="test_guest_click"),
            ]
        ]
    )

    result_article = InlineQueryResultArticle(
        id=f"guest_{msg.message_id}",
        title="🤫 Psst! Guest Whisper",
        input_message_content=InputTextMessageContent(
            message_text=card_text,
            parse_mode="Markdown",
        ),
        reply_markup=kb,
    )

    try:
        sent = await context.bot.answer_guest_query(
            guest_query_id=query_id,
            result=result_article,
        )
        print(
            f"✅ Successfully answered guest query! Inline Message ID: {sent.inline_message_id}\n"
        )
    except Exception as exc:
        print(f"❌ Error in answer_guest_query: {exc}\n")


async def handle_regular_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle regular messages (when the bot is already a member of the chat)."""
    msg = update.message
    if not msg:
        return

    user = msg.from_user
    chat = msg.chat
    text = msg.text or msg.caption or ""

    print("\n" + "-" * 60)
    print("ℹ️ REGULAR MESSAGE RECEIVED (NOT Guest Mode):")
    print(f"  • Sender: {user.first_name if user else 'Unknown'} (ID: {user.id if user else '?'})")
    print(f"  • Chat: {chat.title or chat.type} (ID: {chat.id}, Type: {chat.type})")
    print(f"  • Text: {text!r}")
    print("  👉 Note: The bot is ALREADY A MEMBER of this chat.")
    print("     In chats where the bot is a member, Telegram routes messages as standard")
    print("     chat messages, NOT as guest_message updates.")
    print("-" * 60)


def main() -> None:
    settings = get_settings()
    token = settings.bot_token

    async def post_init(application: Application) -> None:
        me = await application.bot.get_me()
        print("\n🤖 Bot Identity:")
        print(f"  • Username: @{me.username}")
        print(f"  • Name: {me.first_name}")
        print(f"  • supports_guest_queries: {getattr(me, 'supports_guest_queries', None)}")
        print(f"  • supports_inline_queries: {getattr(me, 'supports_inline_queries', None)}")
        print(
            f"  • can_read_all_group_messages (Privacy Off): {getattr(me, 'can_read_all_group_messages', None)}"
        )
        print(
            "\n📡 Polling active for: ['guest_message', 'message', 'inline_query', 'callback_query']..."
        )
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print("👉 TEST 1 (Guest Mode):")
        print("   In a chat where @psst_whisper_bot is NOT A MEMBER:")
        print("   Type '@psst_whisper_bot hello' and press Send.")
        print("👉 TEST 2 (Member Mode):")
        print("   In a chat where @psst_whisper_bot IS A MEMBER:")
        print("   Type '@psst_whisper_bot hello' and press Send.")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print("Press Ctrl+C to stop.\n")

    app = Application.builder().token(token).post_init(post_init).build()

    # Log all updates
    app.add_handler(TypeHandler(Update, raw_update_logger), group=-1)

    # Handler for guest_message updates
    app.add_handler(MessageHandler(filters.UpdateType.GUEST_MESSAGE, handle_guest_message))

    # Handler for regular messages (to detect member interactions)
    app.add_handler(
        MessageHandler(filters.ALL & ~filters.UpdateType.GUEST_MESSAGE, handle_regular_message)
    )

    allowed_updates = [
        "guest_message",
        "message",
        "inline_query",
        "chosen_inline_result",
        "callback_query",
    ]

    app.run_polling(
        allowed_updates=allowed_updates,
        drop_pending_updates=True,
    )


if __name__ == "__main__":
    main()
