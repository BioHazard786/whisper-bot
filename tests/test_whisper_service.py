"""Unit tests for WhisperService business logic."""

import pytest

from whisper_bot.services.whisper_service import WhisperService


@pytest.mark.asyncio
async def test_create_and_access_whisper_by_username(
    whisper_service: WhisperService,
) -> None:
    whisper = await whisper_service.create_whisper(
        sender_id=1,
        sender_first_name="Alice",
        sender_username="alice",
        text="Top secret coordinates",
        target_usernames={"bob"},
    )
    assert whisper.id is not None

    # Authorized recipient opens whisper
    obj, auth, content = await whisper_service.access_whisper(
        whisper_id=whisper.id,
        user_id=2,
        username="bob",
    )
    assert auth is True
    assert content == "Top secret coordinates"
    assert obj is not None
    assert 2 in obj.read_by


@pytest.mark.asyncio
async def test_create_and_access_whisper_by_user_id(
    whisper_service: WhisperService,
) -> None:
    whisper = await whisper_service.create_whisper(
        sender_id=1,
        sender_first_name="Alice",
        sender_username="alice",
        text="Secret for ID",
        target_usernames=set(),
        target_user_ids={999},
    )

    # Access by matching user_id
    _, auth, content = await whisper_service.access_whisper(
        whisper_id=whisper.id,
        user_id=999,
        username=None,
    )
    assert auth is True
    assert content == "Secret for ID"


@pytest.mark.asyncio
async def test_sender_access(whisper_service: WhisperService) -> None:
    # Sender view allowed
    w1 = await whisper_service.create_whisper(
        sender_id=1,
        sender_first_name="Alice",
        sender_username="alice",
        text="My note",
        target_usernames={"bob"},
        allow_sender_view=True,
    )
    _, auth1, _ = await whisper_service.access_whisper(
        whisper_id=w1.id,
        user_id=1,
        username="alice",
    )
    assert auth1 is True

    # Sender view disallowed
    w2 = await whisper_service.create_whisper(
        sender_id=1,
        sender_first_name="Alice",
        sender_username="alice",
        text="My note hidden",
        target_usernames={"bob"},
        allow_sender_view=False,
    )
    _, auth2, status2 = await whisper_service.access_whisper(
        whisper_id=w2.id,
        user_id=1,
        username="alice",
    )
    assert auth2 is False
    assert status2 == "unauthorized"


@pytest.mark.asyncio
async def test_unauthorized_user_denied(whisper_service: WhisperService) -> None:
    whisper = await whisper_service.create_whisper(
        sender_id=1,
        sender_first_name="Alice",
        sender_username="alice",
        text="Private talk",
        target_usernames={"bob"},
    )
    _, auth, status = await whisper_service.access_whisper(
        whisper_id=whisper.id,
        user_id=3,
        username="eve",
    )
    assert auth is False
    assert status == "unauthorized"


@pytest.mark.asyncio
async def test_one_time_self_destruct(whisper_service: WhisperService) -> None:
    whisper = await whisper_service.create_whisper(
        sender_id=1,
        sender_first_name="Alice",
        sender_username="alice",
        text="Self destructing payload",
        target_usernames={"bob"},
        is_one_time=True,
    )

    # First access by recipient succeeds
    w_first, auth1, content1 = await whisper_service.access_whisper(
        whisper_id=whisper.id,
        user_id=2,
        username="bob",
    )
    assert auth1 is True
    assert content1 == "Self destructing payload"
    assert w_first is not None
    assert w_first.is_destroyed is True

    # Second access by recipient is blocked as destroyed
    _, auth2, status2 = await whisper_service.access_whisper(
        whisper_id=whisper.id,
        user_id=2,
        username="bob",
    )
    assert auth2 is False
    assert status2 == "destroyed"


@pytest.mark.asyncio
async def test_delete_whisper(whisper_service: WhisperService) -> None:
    whisper = await whisper_service.create_whisper(
        sender_id=1,
        sender_first_name="Alice",
        sender_username="alice",
        text="Regretted message",
        target_usernames={"bob"},
    )

    # Non-sender cannot delete
    fail = await whisper_service.delete_whisper(whisper.id, user_id=2)
    assert fail is False

    # Sender can delete
    success = await whisper_service.delete_whisper(whisper.id, user_id=1)
    assert success is True

    # After deletion, accessing reports destroyed
    _, auth, status = await whisper_service.access_whisper(
        whisper_id=whisper.id,
        user_id=2,
        username="bob",
    )
    assert auth is False
    assert status == "destroyed"


@pytest.mark.asyncio
async def test_multi_recipient_one_time(whisper_service: WhisperService) -> None:
    whisper = await whisper_service.create_whisper(
        sender_id=1,
        sender_first_name="Alice",
        sender_username="alice",
        text="Group secret",
        target_usernames={"bob", "charlie"},
        is_one_time=True,
    )

    # Bob views his one-time copy
    _, auth_b1, content_b1 = await whisper_service.access_whisper(
        whisper_id=whisper.id,
        user_id=2,
        username="bob",
    )
    assert auth_b1 is True
    assert content_b1 == "Group secret"
    assert whisper.is_destroyed is False

    # Bob tries to view again -> already_read
    _, auth_b2, status_b2 = await whisper_service.access_whisper(
        whisper_id=whisper.id,
        user_id=2,
        username="bob",
    )
    assert auth_b2 is False
    assert status_b2 == "already_read"

    # Charlie views his copy -> now all recipients have read it
    _, auth_c, content_c = await whisper_service.access_whisper(
        whisper_id=whisper.id,
        user_id=3,
        username="charlie",
    )
    assert auth_c is True
    assert content_c == "Group secret"
    assert whisper.is_destroyed is True

    # After all have read, subsequent attempts report destroyed
    _, auth_b3, status_b3 = await whisper_service.access_whisper(
        whisper_id=whisper.id,
        user_id=2,
        username="bob",
    )
    assert auth_b3 is False
    assert status_b3 == "destroyed"


@pytest.mark.asyncio
async def test_mix_match_usernames_and_user_ids(
    whisper_service: WhisperService,
) -> None:
    whisper = await whisper_service.create_whisper(
        sender_id=1,
        sender_first_name="Alice",
        sender_username="alice",
        text="Mix match secret payload",
        target_usernames={"bob"},
        target_user_ids={88888888},
        is_one_time=True,
    )

    # Bob (username target) views
    _, auth_bob, content_bob = await whisper_service.access_whisper(
        whisper_id=whisper.id,
        user_id=2,
        username="bob",
    )
    assert auth_bob is True
    assert content_bob == "Mix match secret payload"
    assert whisper.is_destroyed is False

    # Unauthorized third-party denied
    _, auth_intruder, status_intruder = await whisper_service.access_whisper(
        whisper_id=whisper.id,
        user_id=999,
        username="intruder",
    )
    assert auth_intruder is False
    assert status_intruder == "unauthorized"

    # User 88888888 (ID target) views -> now both have viewed, so destroyed
    _, auth_id, content_id = await whisper_service.access_whisper(
        whisper_id=whisper.id,
        user_id=88888888,
        username=None,
    )
    assert auth_id is True
    assert content_id == "Mix match secret payload"
    assert whisper.is_destroyed is True
