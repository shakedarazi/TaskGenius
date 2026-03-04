"""
TASKGENIUS Chatbot Service - Shared Enums

Aligned with shared/contracts/enums.json and core-api app/core/enums.py.
These enums ensure chatbot responses match core-api expectations.
"""

from enum import Enum


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
