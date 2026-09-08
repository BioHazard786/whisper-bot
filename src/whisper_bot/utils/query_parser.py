"""Parser for inline whisper queries and group commands."""

import re
from dataclasses import dataclass, field

_FLAG_ONE_TIME = {"!1", "!once", "!destruct", "!onetime"}
_FLAG_NO_SENDER = {"!nosender", "!hide", "!anon"}
_ID_PREFIXES = ("id:", "uid:", "user:")


@dataclass(slots=True)
class ParsedWhisperQuery:
    """Structured representation of a parsed whisper request."""

    target_usernames: set[str] = field(default_factory=set)
    target_user_ids: set[int] = field(default_factory=set)
    text: str = ""
    is_one_time: bool = False
    allow_sender_view: bool = True
    raw_query: str = ""

    @property
    def has_targets(self) -> bool:
        """Check if any recipient targets were identified."""
        return bool(self.target_usernames or self.target_user_ids)

    @property
    def has_text(self) -> bool:
        """Check if secret message text is present."""
        return bool(self.text.strip())

    @property
    def is_valid(self) -> bool:
        """Query is valid if it has at least one target and a non-empty text."""
        return self.has_targets and self.has_text


def normalize_links(raw: str) -> str:
    """Normalize Telegram user/channel links and markdown mentions into standard target formats."""
    # Transform [Name](tg://user?id=12345678) -> id:12345678
    text = re.sub(r"\[([^\]]+)\]\(tg://user\?id=(\d+)\)", r"id:\2", raw)
    # Transform [Name](https://t.me/username) -> @username
    text = re.sub(r"\[([^\]]+)\]\(https?://t\.me/([a-zA-Z0-9_]{3,32})\)", r"@\2", text)
    # Transform direct tg://user?id=12345678 -> id:12345678
    text = re.sub(r"tg://user\?id=(\d+)", r"id:\1", text)
    # Transform direct https://t.me/username or t.me/username -> @username
    text = re.sub(r"(?<!\S)(?:https?://)?t\.me/([a-zA-Z0-9_]{3,32})(?!\S)", r"@\1", text)
    return text


def parse_whisper_query(raw: str) -> ParsedWhisperQuery:
    """Parse raw query string into targets, flags, and secret message content.

    Formats supported:
    - `@username secret message`
    - `@user1 @user2 secret message`
    - `id:12345678 secret message`
    - `id:12345678,87654321 secret message`
    - `12345678 87654321 secret message` (raw Telegram user IDs)
    - `12345678,87654321 secret message`
    - `tg://user?id=12345678 secret message`
    - `[Name](tg://user?id=12345678) secret message`
    - `!1 @username secret message` (one-time flag)
    - `!nosender @username secret message` (hide from sender)
    """
    cleaned = normalize_links(raw).strip()
    if not cleaned:
        return ParsedWhisperQuery(raw_query=raw)

    tokens = cleaned.split()
    target_usernames: set[str] = set()
    target_user_ids: set[int] = set()
    is_one_time = False
    allow_sender_view = True
    message_start_idx = 0

    for idx, token in enumerate(tokens):
        lower_token = token.lower()

        # Check for flags
        if lower_token in _FLAG_ONE_TIME:
            is_one_time = True
            message_start_idx = idx + 1
            continue

        if lower_token in _FLAG_NO_SENDER:
            allow_sender_view = False
            message_start_idx = idx + 1
            continue

        # Check for ID prefix: id:12345678, uid:12345678, user:12345678 (supports comma-separated list)
        matched_id_prefix = False
        for pfx in _ID_PREFIXES:
            if lower_token.startswith(pfx):
                ids_part = lower_token[len(pfx) :]
                sub_ids = [s.strip() for s in ids_part.split(",") if s.strip()]
                if sub_ids and all(s.isdigit() for s in sub_ids):
                    for s in sub_ids:
                        target_user_ids.add(int(s))
                    message_start_idx = idx + 1
                    matched_id_prefix = True
                    break
        if matched_id_prefix:
            continue

        # Check for comma-separated pure numeric IDs: e.g. 12345678,87654321
        if "," in token:
            sub_items = [s.strip() for s in token.split(",") if s.strip()]
            if sub_items and all(s.isdigit() and len(s) >= 5 for s in sub_items):
                for s in sub_items:
                    target_user_ids.add(int(s))
                message_start_idx = idx + 1
                continue

        # Check for single pure numeric user ID (Telegram user IDs are typically 5-16 digits)
        clean_numeric = token.rstrip(",")
        if clean_numeric.isdigit() and 5 <= len(clean_numeric) <= 16:
            target_user_ids.add(int(clean_numeric))
            message_start_idx = idx + 1
            continue

        # Check for username: @alice, @alice,@bob, or @alice,
        sub_names = [s.strip() for s in token.split(",") if s.strip()]
        if sub_names and all(s.startswith("@") and len(s) > 1 for s in sub_names):
            valid_names: list[str] = []
            for s in sub_names:
                clean_name = s.lstrip("@").lower()
                if re.match(r"^[a-zA-Z0-9_]{3,32}$", clean_name):
                    valid_names.append(clean_name)
            if len(valid_names) == len(sub_names):
                for name in valid_names:
                    target_usernames.add(name)
                message_start_idx = idx + 1
                continue

        # Once a non-target, non-flag token is encountered, the rest is the message
        break

    remaining_text = " ".join(tokens[message_start_idx:]).strip()

    return ParsedWhisperQuery(
        target_usernames=target_usernames,
        target_user_ids=target_user_ids,
        text=remaining_text,
        is_one_time=is_one_time,
        allow_sender_view=allow_sender_view,
        raw_query=raw,
    )

