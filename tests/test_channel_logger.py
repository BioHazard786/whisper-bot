"""Unit tests for ChannelLogger service and configuration."""

from unittest.mock import AsyncMock

import pytest
from aiogram import Bot
from aiogram.enums import ParseMode
from aiogram.types import Chat, ChosenInlineResult, Message, User

from whisper_bot.config import Settings
from whisper_bot.handlers.group import handle_group_whisper_command
from whisper_bot.handlers.inline import handle_chosen_inline_result
from whisper_bot.models.whisper import Whisper
from whisper_bot.services.channel_logger import ChannelLogger
from whisper_bot.services.whisper_service import WhisperService


@pytest.mark.asyncio
async def test_channel_logger_disabled_when_none() -> None:
    """Verify ChannelLogger drops messages when log_channel is None."""
    mock_bot = AsyncMock(spec=Bot)
    mock_bot.send_message = AsyncMock()

    logger = ChannelLogger(bot=mock_bot, log_channel=None)
    assert not logger.is_enabled

    whisper = Whisper(
        id="test1",
        sender_id=111,
        sender_first_name="Alice",
        sender_username="alice",
        text="Super secret message",
        target_usernames={"bob"},
    )
    await logger.log_whisper(whisper, mode="group")

    mock_bot.send_message.assert_not_awaited()


@pytest.mark.asyncio
async def test_channel_logger_sends_formatted_message() -> None:
    """Verify ChannelLogger sends detailed HTML log to the designated channel."""
    mock_bot = AsyncMock(spec=Bot)
    mock_bot.send_message = AsyncMock()

    logger = ChannelLogger(bot=mock_bot, log_channel=-1001234567890)
    assert logger.is_enabled

    whisper = Whisper(
        id="test2",
        sender_id=111,
        sender_first_name="Alice",
        sender_username="alice",
        text="Confidential bank details: 1234-5678",
        target_usernames={"bob"},
        target_user_ids={999},
        is_one_time=True,
    )
    await logger.log_whisper(
        whisper,
        mode="group",
        chat_title="Secret Project Group",
        chat_id=-1009876543210,
    )

    mock_bot.send_message.assert_awaited_once()
    call_kwargs = mock_bot.send_message.call_args.kwargs
    assert call_kwargs["chat_id"] == -1001234567890
    assert call_kwargs["parse_mode"] == ParseMode.HTML

    text = call_kwargs["text"]
    assert "Confidential bank details: 1234-5678" in text
    assert "Alice" in text
    assert "@alice" in text
    assert "111" in text
    assert "@bob" in text
    assert "ID:999" in text
    assert "One-Time Self-Destruct" in text
    assert "Group Command" in text
    assert "Secret Project Group" in text
    assert "-1009876543210" in text


@pytest.mark.asyncio
async def test_channel_logger_handles_send_error_gracefully() -> None:
    """Verify ChannelLogger catches Telegram API errors without raising."""
    mock_bot = AsyncMock(spec=Bot)
    mock_bot.send_message = AsyncMock(side_effect=RuntimeError("Channel not found"))

    logger = ChannelLogger(bot=mock_bot, log_channel=-1009999999999)
    whisper = Whisper(
        id="test3",
        sender_id=111,
        sender_first_name="Alice",
        sender_username="alice",
        text="Secret",
        target_usernames={"bob"},
    )
    # Must not raise
    await logger.log_whisper(whisper, mode="inline")
    mock_bot.send_message.assert_awaited_once()


@pytest.mark.asyncio
async def test_group_whisper_triggers_channel_logger(whisper_service: WhisperService) -> None:
    """Verify handle_group_whisper_command invokes channel_logger with whisper details."""
    mock_bot = AsyncMock(spec=Bot)
    mock_bot.send_message = AsyncMock()
    mock_bot.send_message.return_value = AsyncMock(message_id=50)

    mock_channel_logger = AsyncMock(spec=ChannelLogger)
    mock_channel_logger.log_whisper = AsyncMock()

    sender = User(id=123, is_bot=False, first_name="Eve", username="eve")
    chat = Chat(id=-100111222333, type="supergroup", title="Test Supergroup")

    mock_msg = AsyncMock(spec=Message)
    mock_msg.text = "/whisper @bob Meeting at noon"
    mock_msg.caption = None
    mock_msg.entities = []
    mock_msg.from_user = sender
    mock_msg.chat = chat
    mock_msg.delete = AsyncMock()

    await handle_group_whisper_command(
        message=mock_msg,
        bot=mock_bot,
        whisper_service=whisper_service,
        channel_logger=mock_channel_logger,
    )

    mock_channel_logger.log_whisper.assert_awaited_once()
    logged_whisper = mock_channel_logger.log_whisper.call_args.kwargs["whisper"]
    assert logged_whisper.text == "Meeting at noon"
    assert "bob" in logged_whisper.target_usernames
    assert mock_channel_logger.log_whisper.call_args.kwargs["mode"] == "group"
    assert mock_channel_logger.log_whisper.call_args.kwargs["chat_title"] == "Test Supergroup"


@pytest.mark.asyncio
async def test_inline_chosen_triggers_channel_logger(whisper_service: WhisperService) -> None:
    """Verify handle_chosen_inline_result invokes channel_logger."""
    whisper = await whisper_service.create_whisper(
        sender_id=456,
        sender_first_name="Frank",
        sender_username="frank",
        text="Inline secret",
        target_usernames={"grace"},
        custom_id="inline_w1",
    )

    mock_channel_logger = AsyncMock(spec=ChannelLogger)
    mock_channel_logger.log_whisper = AsyncMock()

    chosen = ChosenInlineResult(
        result_id="inline_w1",
        from_user=User(id=456, is_bot=False, first_name="Frank", username="frank"),
        query="@grace Inline secret",
        inline_message_id="msg_inline_999",
    )

    await handle_chosen_inline_result(
        chosen=chosen,
        whisper_service=whisper_service,
        channel_logger=mock_channel_logger,
    )

    mock_channel_logger.log_whisper.assert_awaited_once()
    logged = mock_channel_logger.log_whisper.call_args.kwargs["whisper"]
    assert logged.id == whisper.id
    assert logged.text == "Inline secret"
    assert mock_channel_logger.log_whisper.call_args.kwargs["mode"] == "inline"


def test_settings_log_channel_parsing() -> None:
    """Verify Settings parses various LOG_CHANNEL formats."""
    # Negative channel ID
    s1 = Settings(LOG_CHANNEL="-1001234567890")
    assert s1.log_channel == -1001234567890

    # Username string
    s2 = Settings(LOG_CHANNEL="@my_whisper_logs")
    assert s2.log_channel == "@my_whisper_logs"

    # Empty / none string values normalize to None
    s3 = Settings(LOG_CHANNEL="")
    assert s3.log_channel is None

    s4 = Settings(LOG_CHANNEL="none")
    assert s4.log_channel is None

    s5 = Settings(LOG_CHANNEL="0")
    assert s5.log_channel is None
