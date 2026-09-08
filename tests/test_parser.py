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


def test_parse_multiple_user_ids_space_separated() -> None:
    parsed = parse_whisper_query("12345678 87654321 secret meeting at dusk")
    assert parsed.is_valid
    assert parsed.target_user_ids == {12345678, 87654321}
    assert parsed.target_usernames == set()
    assert parsed.text == "secret meeting at dusk"


def test_parse_multiple_user_ids_comma_separated() -> None:
    parsed = parse_whisper_query("12345678,87654321,99999999 secret code")
    assert parsed.is_valid
    assert parsed.target_user_ids == {12345678, 87654321, 99999999}
    assert parsed.text == "secret code"

    parsed_spaced = parse_whisper_query("12345678, 87654321 secret code")
    assert parsed_spaced.is_valid
    assert parsed_spaced.target_user_ids == {12345678, 87654321}
    assert parsed_spaced.text == "secret code"


def test_parse_multiple_user_ids_prefixed() -> None:
    # id: prefix with comma-separated list
    parsed = parse_whisper_query("id:11111111,22222222 confidential notes")
    assert parsed.is_valid
    assert parsed.target_user_ids == {11111111, 22222222}
    assert parsed.text == "confidential notes"

    # Multiple id: tokens
    parsed_multi = parse_whisper_query("id:11111111 id:22222222 confidential notes")
    assert parsed_multi.is_valid
    assert parsed_multi.target_user_ids == {11111111, 22222222}
    assert parsed_multi.text == "confidential notes"

    # uid: and user: prefixes
    parsed_uid = parse_whisper_query("uid:33333333 user:44444444 token transfer")
    assert parsed_uid.is_valid
    assert parsed_uid.target_user_ids == {33333333, 44444444}
    assert parsed_uid.text == "token transfer"


def test_parse_mixed_usernames_and_user_ids() -> None:
    parsed = parse_whisper_query("!1 @alice 12345678 id:87654321 deploy key")
    assert parsed.is_valid
    assert parsed.is_one_time is True
    assert parsed.target_usernames == {"alice"}
    assert parsed.target_user_ids == {12345678, 87654321}
    assert parsed.text == "deploy key"


def test_parse_usernames_with_commas() -> None:
    parsed = parse_whisper_query("@alice, @bob, @charlie launch the rocket")
    assert parsed.is_valid
    assert parsed.target_usernames == {"alice", "bob", "charlie"}
    assert parsed.text == "launch the rocket"


def test_parse_numbers_in_message_not_treated_as_targets() -> None:
    parsed = parse_whisper_query("@alice 100 dollars on table")
    assert parsed.is_valid
    assert parsed.target_usernames == {"alice"}
    assert parsed.target_user_ids == set()
    assert parsed.text == "100 dollars on table"


def test_parse_tg_user_links_and_markdown_mentions() -> None:
    # Direct tg:// link
    parsed_tg = parse_whisper_query("tg://user?id=12345678 secret via tg link")
    assert parsed_tg.is_valid
    assert parsed_tg.target_user_ids == {12345678}
    assert parsed_tg.text == "secret via tg link"

    # Markdown mention link [Name](tg://user?id=...)
    parsed_md = parse_whisper_query("[John Doe](tg://user?id=87654321) meet at 5pm")
    assert parsed_md.is_valid
    assert parsed_md.target_user_ids == {87654321}
    assert parsed_md.text == "meet at 5pm"

    # Markdown t.me link [Alice](https://t.me/alice)
    parsed_tme = parse_whisper_query("[Alice](https://t.me/alice) check this out")
    assert parsed_tme.is_valid
    assert parsed_tme.target_usernames == {"alice"}
    assert parsed_tme.text == "check this out"


