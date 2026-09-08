"""Whisper domain models and status definitions."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum


class WhisperStatus(StrEnum):
    """Lifecycle status of a whisper."""

    ACTIVE = "active"
    READ = "read"
    DESTROYED = "destroyed"
    EXPIRED = "expired"


@dataclass(slots=True)
class Whisper:
    """Represents a secret whisper message."""

    id: str
    sender_id: int
    sender_first_name: str
    sender_username: str | None
    target_usernames: set[str] = field(default_factory=set)
    target_user_ids: set[int] = field(default_factory=set)
    text: str = ""
    is_one_time: bool = False
    allow_sender_view: bool = True
    read_by: set[int] = field(default_factory=set)
    read_usernames: set[str] = field(default_factory=set)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    expires_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    is_destroyed: bool = False
    inline_message_id: str | None = None
    chat_id: int | None = None
    group_message_id: int | None = None

    @property
    def is_expired(self) -> bool:
        """Check if whisper has passed its expiration time."""
        return datetime.now(UTC) >= self.expires_at

    @property
    def current_status(self) -> WhisperStatus:
        """Determine current status of the whisper."""
        if self.is_destroyed:
            return WhisperStatus.DESTROYED
        if self.is_expired:
            return WhisperStatus.EXPIRED
        if self.read_by:
            return WhisperStatus.READ
        return WhisperStatus.ACTIVE

    def can_view(self, user_id: int, username: str | None) -> bool:
        """Verify if a given user is authorized to view this whisper."""
        # 1. Sender authorization
        if user_id == self.sender_id and self.allow_sender_view:
            return True

        # 2. Explicit User ID authorization
        if user_id in self.target_user_ids:
            return True

        # 3. Username matching (case-insensitive)
        if username:
            clean_username = username.lstrip("@").strip().lower()
            if clean_username in self.target_usernames:
                return True

        return False

    def format_targets_display(self) -> str:
        """Return formatted string representing intended recipients."""
        parts: list[str] = []
        for username in sorted(self.target_usernames):
            parts.append(f"@{username}")
        for uid in sorted(self.target_user_ids):
            parts.append(f"ID:{uid}")
        return ", ".join(parts) if parts else "everyone"
