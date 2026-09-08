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
