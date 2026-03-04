"""
TASKGENIUS Core API - Foundation Layer

Provides config, database, security, and shared enums.
Import from app.core for consistent access.
"""

from app.core.config import settings, Settings
from app.core.database import database, get_database
from app.core.security import validate_security_config
from app.core.enums import (
    TaskStatus,
    TaskPriority,
    TaskCategory,
    EstimateBucket,
    UrgencyLevel,
)

__all__ = [
    "settings",
    "Settings",
    "database",
    "get_database",
    "validate_security_config",
    "TaskStatus",
    "TaskPriority",
    "TaskCategory",
    "EstimateBucket",
    "UrgencyLevel",
]
