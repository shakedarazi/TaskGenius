"""
TASKGENIUS Core API - User Model

Internal user model for authentication.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
import uuid


def _utcnow() -> datetime:
    """Get current UTC time as timezone-aware datetime."""
    return datetime.now(timezone.utc)


@dataclass
class User:
    """User entity for authentication."""

    id: str
    username: str
    password_hash: str
    created_at: datetime = field(default_factory=_utcnow)

    @classmethod
    def create(cls, username: str, password_hash: str) -> "User":
        """Create a new user with generated ID."""
        return cls(
            id=str(uuid.uuid4()),
            username=username,
            password_hash=password_hash,
            created_at=_utcnow(),
        )
