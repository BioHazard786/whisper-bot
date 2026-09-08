"""Parser for inline whisper queries and group commands."""

import re
from dataclasses import dataclass, field

_FLAG_ONE_TIME = {"!1", "!once", "!destruct", "!onetime"}
_FLAG_NO_SENDER = {"!nosender", "!hide", "!anon"}


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


def parse_whisper_query(raw: str) -> ParsedWhisperQuery:
    """Parse raw query string into targets, flags, and secret message content.

    Formats supported:
    - `@username secret message`
    - `@user1 @user2 secret message`
    - `id:12345678 secret message`
    - `!1 @username secret message` (one-time flag)
    - `!nosender @username secret message` (hide from sender)
    """
    cleaned = raw.strip()
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

        # Check for username: @alice
        if token.startswith("@") and len(token) > 1:
            clean_name = token.lstrip("@").strip().lower()
            # Telegram usernames: a-z, 0-9, underscores, 4-32 chars
            if re.match(r"^[a-zA-Z0-9_]{3,32}$", clean_name):
                target_usernames.add(clean_name)
                message_start_idx = idx + 1
                continue

        # Check for ID prefix: id:12345678 or pure digits if before message text
        if lower_token.startswith("id:"):
            id_part = lower_token.split(":", 1)[1]
            if id_part.isdigit():
                target_user_ids.add(int(id_part))
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
