"""
TASKGENIUS Chatbot Service - Foundation Layer

Provides config and shared enums.
"""

from app.core.config import settings, Settings
from app.core.enums import TaskPriority, TaskCategory, EstimateBucket

__all__ = [
    "settings",
    "Settings",
    "TaskPriority",
    "TaskCategory",
    "EstimateBucket",
]
