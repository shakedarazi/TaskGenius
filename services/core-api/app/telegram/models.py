from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
import uuid


def _utcnow() -> datetime:
    """Get current UTC time as timezone-aware datetime."""
    return datetime.now(timezone.utc)


@dataclass
class UserTelegramLink:
    id: str
    user_id: str
    telegram_user_id: int
    telegram_chat_id: int
    telegram_username: Optional[str] = None
    notifications_enabled: bool = False
    connected_at: datetime = field(default_factory=_utcnow)

    @classmethod
    def create(
        cls,
        user_id: str,
        telegram_user_id: int,
        telegram_chat_id: int,
        telegram_username: Optional[str] = None,
    ) -> "UserTelegramLink":
        return cls(
            id=str(uuid.uuid4()),
            user_id=user_id,
            telegram_user_id=telegram_user_id,
            telegram_chat_id=telegram_chat_id,
            telegram_username=telegram_username,
            notifications_enabled=False,
            connected_at=_utcnow(),
        )


@dataclass
class TelegramVerificationCode:
    id: str
    user_id: str
    code: str
    created_at: datetime = field(default_factory=_utcnow)
    expires_at: datetime = field(default_factory=_utcnow)
    used_at: Optional[datetime] = None

    @property
    def is_used(self) -> bool:
        return self.used_at is not None

    @property
    def is_expired(self) -> bool:
        return self.expires_at <= _utcnow()


@dataclass
class ProcessedTelegramUpdate:
    id: str
    update_id: int
    telegram_user_id: int
    first_seen_at: datetime = field(default_factory=_utcnow)

    @classmethod
    def create(cls, update_id: int, telegram_user_id: int) -> "ProcessedTelegramUpdate":
        return cls(
            id=str(uuid.uuid4()),
            update_id=update_id,
            telegram_user_id=telegram_user_id,
            first_seen_at=_utcnow(),
        )

