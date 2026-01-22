
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
import uuid


def _utcnow() -> datetime:
    """Get current UTC time as timezone-aware datetime."""
    return datetime.now(timezone.utc)


@dataclass
class TelegramLink:
    """Telegram linkage information embedded in User document."""

    telegram_user_id: int
    telegram_chat_id: int
    telegram_username: Optional[str] = None
    notifications_enabled: bool = False
    linked_at: datetime = field(default_factory=_utcnow)


@dataclass
class User:
    """User entity for authentication."""

    id: str
    username: str
    password_hash: str
    created_at: datetime = field(default_factory=_utcnow)
    telegram: Optional[TelegramLink] = None

    @classmethod
    def create(cls, username: str, password_hash: str) -> "User":
        """Create a new user with generated ID."""
        return cls(
            id=str(uuid.uuid4()),
            username=username,
            password_hash=password_hash,
            created_at=_utcnow(),
            telegram=None,
        )

    def to_dict(self) -> dict:
        """Convert user to dictionary for MongoDB storage."""
        doc = {
            "_id": self.id,
            "username": self.username,
            "password_hash": self.password_hash,
            "created_at": self.created_at,
        }
        if self.telegram:
            doc["telegram"] = {
                "telegram_user_id": self.telegram.telegram_user_id,
                "telegram_chat_id": self.telegram.telegram_chat_id,
                "telegram_username": self.telegram.telegram_username,
                "notifications_enabled": self.telegram.notifications_enabled,
                "linked_at": self.telegram.linked_at,
            }
        return doc

    @classmethod
    def from_dict(cls, data: dict) -> "User":
        """Create user from MongoDB document."""
        telegram = None
        if "telegram" in data and data["telegram"]:
            tel_data = data["telegram"]
            telegram = TelegramLink(
                telegram_user_id=tel_data["telegram_user_id"],
                telegram_chat_id=tel_data["telegram_chat_id"],
                telegram_username=tel_data.get("telegram_username"),
                notifications_enabled=tel_data.get("notifications_enabled", False),
                linked_at=tel_data.get("linked_at", _utcnow()),
            )
        return cls(
            id=data["_id"],
            username=data["username"],
            password_hash=data["password_hash"],
            created_at=data["created_at"],
            telegram=telegram,
        )
