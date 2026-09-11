"""Unit tests for bot handlers."""

from unittest.mock import AsyncMock

import pytest
from aiogram import Bot
from aiogram.types import CallbackQuery, User

from whisper_bot.handlers.callbacks import handle_whisper_callback
from whisper_bot.services.whisper_service import WhisperService


@pytest.mark.asyncio
async def test_callback_open_authorized(whisper_service: WhisperService) -> None:
    whisper = await whisper_service.create_whisper(
        sender_id=1,
        sender_first_name="Alice",
        sender_username="alice",
        text="Super secret note",
        target_usernames={"bob"},
    )

    mock_user = User(
        id=2,
        is_bot=False,
        first_name="Bob",
        username="bob",
    )
    mock_callback = AsyncMock(spec=CallbackQuery)
    mock_callback.answer = AsyncMock()
    mock_callback.data = f"w:{whisper.id}:open"
    mock_callback.from_user = mock_user
    mock_callback.message = None
    mock_callback.inline_message_id = "inline_msg_123"

    mock_bot = AsyncMock(spec=Bot)

    await handle_whisper_callback(
        callback=mock_callback,
        bot=mock_bot,
        whisper_service=whisper_service,
    )

    mock_callback.answer.assert_awaited_once()
    called_text = mock_callback.answer.call_args.args[0]
    assert "Super secret note" in called_text


@pytest.mark.asyncio
async def test_callback_open_unauthorized(whisper_service: WhisperService) -> None:
    whisper = await whisper_service.create_whisper(
        sender_id=1,
        sender_first_name="Alice",
        sender_username="alice",
        text="Super secret note",
        target_usernames={"bob"},
    )

    mock_user = User(
        id=3,
        is_bot=False,
        first_name="Eve",
        username="eve",
    )
    mock_callback = AsyncMock(spec=CallbackQuery)
    mock_callback.answer = AsyncMock()
    mock_callback.data = f"w:{whisper.id}:open"
    mock_callback.from_user = mock_user
    mock_callback.message = None
    mock_callback.inline_message_id = "inline_msg_123"

    mock_bot = AsyncMock(spec=Bot)

    await handle_whisper_callback(
        callback=mock_callback,
        bot=mock_bot,
        whisper_service=whisper_service,
    )

    mock_callback.answer.assert_awaited_once()
    called_text = mock_callback.answer.call_args.args[0]
    assert "not for you" in called_text


@pytest.mark.asyncio
async def test_callback_delete_by_sender(whisper_service: WhisperService) -> None:
    whisper = await whisper_service.create_whisper(
        sender_id=1,
        sender_first_name="Alice",
        sender_username="alice",
        text="To be deleted",
        target_usernames={"bob"},
    )

    mock_user = User(
        id=1,
        is_bot=False,
        first_name="Alice",
        username="alice",
    )
    mock_callback = AsyncMock(spec=CallbackQuery)
    mock_callback.answer = AsyncMock()
    mock_callback.data = f"w:{whisper.id}:delete"
    mock_callback.from_user = mock_user
    mock_callback.message = None
    mock_callback.inline_message_id = "inline_msg_123"

    mock_bot = AsyncMock(spec=Bot)

    await handle_whisper_callback(
        callback=mock_callback,
        bot=mock_bot,
        whisper_service=whisper_service,
    )

    mock_callback.answer.assert_awaited_once()
    called_text = mock_callback.answer.call_args.args[0]
    assert "has been deleted" in called_text


@pytest.mark.asyncio
async def test_group_whisper_text_mention(whisper_service: WhisperService) -> None:
    from aiogram.types import Chat, Message, MessageEntity

    from whisper_bot.handlers.group import handle_group_whisper_command

    mock_bot = AsyncMock(spec=Bot)
    mock_bot.send_message = AsyncMock()
    mock_bot.send_message.return_value = AsyncMock(message_id=42)

    # User without username
    tagged_user = User(id=77777777, is_bot=False, first_name="NoUsernameUser")
    sender_user = User(id=1, is_bot=False, first_name="Alice", username="alice")
    chat = Chat(id=-1001234567890, type="supergroup")

    entity = MessageEntity(type="text_mention", offset=9, length=14, user=tagged_user)
    mock_message = AsyncMock(spec=Message)
    mock_message.text = "/whisper NoUsernameUser confidential info"
    mock_message.entities = [entity]
    mock_message.from_user = sender_user
    mock_message.chat = chat
    mock_message.delete = AsyncMock()

    await handle_group_whisper_command(
        message=mock_message,
        bot=mock_bot,
        whisper_service=whisper_service,
    )

    mock_bot.send_message.assert_awaited_once()
    sent_text = mock_bot.send_message.call_args.kwargs["text"]
    assert "ID:77777777" in sent_text


@pytest.mark.asyncio
async def test_group_whisper_psst_alias(whisper_service: WhisperService) -> None:
    """Test that /psst command works identically to /whisper."""
    from aiogram.types import Chat, Message

    from whisper_bot.handlers.group import handle_group_whisper_command

    mock_bot = AsyncMock(spec=Bot)
    mock_bot.send_message = AsyncMock()
    mock_bot.send_message.return_value = AsyncMock(message_id=99)

    sender = User(id=1, is_bot=False, first_name="Alice", username="alice")
    chat = Chat(id=-1001234567890, type="supergroup")

    mock_msg = AsyncMock(spec=Message)
    mock_msg.text = "/psst @bob Top secret info for you"
    mock_msg.caption = None
    mock_msg.entities = []
    mock_msg.from_user = sender
    mock_msg.chat = chat
    mock_msg.delete = AsyncMock()

    await handle_group_whisper_command(
        message=mock_msg,
        bot=mock_bot,
        whisper_service=whisper_service,
    )

    mock_msg.delete.assert_awaited_once()
    mock_bot.send_message.assert_awaited_once()
    sent_text = mock_bot.send_message.call_args.kwargs["text"]
    assert "@bob" in sent_text


@pytest.mark.asyncio
async def test_handle_start_command() -> None:
    """Test /start command message content."""
    from aiogram.types import Chat, Message

    from whisper_bot.handlers.common import handle_start

    mock_msg = AsyncMock(spec=Message)
    mock_msg.from_user = User(id=1, is_bot=False, first_name="Alice", username="alice")
    mock_msg.chat = Chat(id=1, type="private")
    mock_msg.answer = AsyncMock()

    await handle_start(mock_msg)

    mock_msg.answer.assert_awaited_once()
    called_text = mock_msg.answer.call_args.args[0]
    assert "/whisper" in called_text
    assert "/psst" in called_text
    assert "4,096" in called_text


@pytest.mark.asyncio
async def test_handle_help_command() -> None:
    """Test /help command message content."""
    from aiogram.types import Chat, Message

    from whisper_bot.handlers.common import handle_help

    mock_msg = AsyncMock(spec=Message)
    mock_msg.from_user = User(id=1, is_bot=False, first_name="Alice", username="alice")
    mock_msg.chat = Chat(id=1, type="private")
    mock_msg.answer = AsyncMock()

    await handle_help(mock_msg)

    mock_msg.answer.assert_awaited_once()
    called_text = mock_msg.answer.call_args.args[0]
    assert "/whisper" in called_text
    assert "/psst" in called_text
    assert "4,096" in called_text
