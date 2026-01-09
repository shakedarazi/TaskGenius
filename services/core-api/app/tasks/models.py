"""
TASKGENIUS Core API - Task Models

Internal task model for database operations.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
import uuid

from app.tasks.enums import (
    TaskStatus,
    TaskPriority,
    TaskCategory,
    EstimateBucket,
)


def _utcnow() -> datetime:
    """Get current UTC time as timezone-aware datetime."""
    return datetime.now(timezone.utc)


@dataclass
class Task:
    """Task entity for database storage."""

    id: str
    owner_id: str
    title: str
    status: TaskStatus
    priority: TaskPriority
    description: Optional[str] = None
    category: Optional[TaskCategory] = None
    deadline: Optional[datetime] = None
    estimate_bucket: Optional[EstimateBucket] = None
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: datetime = field(default_factory=_utcnow)

    @classmethod
    def create(
        cls,
        owner_id: str,
        title: str,
        status: TaskStatus,
        priority: TaskPriority,
        description: Optional[str] = None,
        category: Optional[TaskCategory] = None,
        deadline: Optional[datetime] = None,
        estimate_bucket: Optional[EstimateBucket] = None,
    ) -> "Task":
        """Create a new task with generated ID."""
        now = _utcnow()
        return cls(
            id=str(uuid.uuid4()),
            owner_id=owner_id,
            title=title,
            status=status,
            priority=priority,
            description=description,
            category=category,
            deadline=deadline,
            estimate_bucket=estimate_bucket,
            created_at=now,
            updated_at=now,
        )

    def to_dict(self) -> dict:
        """Convert task to dictionary for MongoDB storage."""
        return {
            "_id": self.id,
            "owner_id": self.owner_id,
            "title": self.title,
            "status": self.status.value,
            "priority": self.priority.value,
            "description": self.description,
            "category": self.category.value if self.category else None,
            "deadline": self.deadline,
            "estimate_bucket": self.estimate_bucket.value if self.estimate_bucket else None,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Task":
        """Create task from MongoDB document."""
        return cls(
            id=data["_id"],
            owner_id=data["owner_id"],
            title=data["title"],
            status=TaskStatus(data["status"]),
            priority=TaskPriority(data["priority"]),
            description=data.get("description"),
            category=TaskCategory(data["category"]) if data.get("category") else None,
            deadline=data.get("deadline"),
            estimate_bucket=EstimateBucket(data["estimate_bucket"]) if data.get("estimate_bucket") else None,
            created_at=data["created_at"],
            updated_at=data["updated_at"],
        )
