"""
TASKGENIUS Core API - Insights Models

Insights operates on Task objects from app.tasks.models.
This module exists for structural consistency with the Standard Module Pattern.
"""

# Re-export Task for convenience when insights logic needs the type
from app.tasks.models import Task  # noqa: F401
