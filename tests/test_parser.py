"""Unit tests for query parsing."""

from whisper_bot.utils.query_parser import parse_whisper_query


def test_parse_empty_query() -> None:
    parsed = parse_whisper_query("")
    assert not parsed.is_valid
    assert not parsed.has_targets
    assert not parsed.has_text


def test_parse_single_username() -> None:
    parsed = parse_whisper_query("@bob meet me at the rooftop")
    assert parsed.is_valid
    assert parsed.target_usernames == {"bob"}
    assert parsed.target_user_ids == set()
    assert parsed.text == "meet me at the rooftop"
    assert not parsed.is_one_time
    assert parsed.allow_sender_view is True


def test_parse_multiple_usernames() -> None:
    parsed = parse_whisper_query("@alice @Bob @CHARLIE the key is under the mat")
    assert parsed.is_valid
    assert parsed.target_usernames == {"alice", "bob", "charlie"}
    assert parsed.text == "the key is under the mat"


def test_parse_user_id() -> None:
    parsed = parse_whisper_query("id:12345678 secret message")
    assert parsed.is_valid
    assert parsed.target_user_ids == {12345678}
    assert parsed.text == "secret message"


def test_parse_one_time_flags() -> None:
    for flag in ["!1", "!once", "!destruct", "!onetime"]:
        parsed = parse_whisper_query(f"{flag} @target secret code")
        assert parsed.is_valid
        assert parsed.is_one_time is True
        assert parsed.target_usernames == {"target"}
        assert parsed.text == "secret code"


def test_parse_no_sender_flag() -> None:
    parsed = parse_whisper_query("!nosender @target anonymous tip")
    assert parsed.is_valid
    assert parsed.allow_sender_view is False
    assert parsed.target_usernames == {"target"}
    assert parsed.text == "anonymous tip"


def test_parse_missing_text() -> None:
    parsed = parse_whisper_query("@bob")
    assert parsed.has_targets
    assert not parsed.has_text
    assert not parsed.is_valid


def test_parse_no_targets() -> None:
    parsed = parse_whisper_query("hello world without a target")
    assert not parsed.has_targets
    assert parsed.has_text
    assert not parsed.is_valid
