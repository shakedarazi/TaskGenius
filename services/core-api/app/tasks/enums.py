"""
TASKGENIUS Core API - Task Enums

Enums for task-related fields, derived from shared/contracts/enums.json.
These enums are immutable contracts and must not be modified.
"""

from enum import Enum


class TaskStatus(str, Enum):
    """Task status values."""
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    CANCELED = "canceled"


class TaskPriority(str, Enum):
    """Task priority levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class TaskCategory(str, Enum):
    """Task category classifications."""
    WORK = "work"
    STUDY = "study"
    PERSONAL = "personal"
    HEALTH = "health"
    FINANCE = "finance"
    ERRANDS = "errands"
    OTHER = "other"


class EstimateBucket(str, Enum):
    """Time estimate buckets for tasks."""
    LT_15 = "lt_15"        # Less than 15 minutes
    _15_30 = "15_30"       # 15-30 minutes
    _30_60 = "30_60"       # 30-60 minutes
    _60_120 = "60_120"     # 60-120 minutes
    GT_120 = "gt_120"      # More than 120 minutes


class UrgencyLevel(str, Enum):
    """
    Derived urgency level computed from deadline and current time.
    
    Per docs/requirements.en.md:
    - NO_DEADLINE: deadline is missing
    - OVERDUE: deadline passed AND status is not DONE/CANCELED
    - DUE_TODAY: deadline is today
    - DUE_SOON: within next 7 days
    - NOT_SOON: more than 7 days away
    """
    NO_DEADLINE = "no_deadline"
    OVERDUE = "overdue"
    DUE_TODAY = "due_today"
    DUE_SOON = "due_soon"
    NOT_SOON = "not_soon"
