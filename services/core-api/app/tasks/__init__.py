"""
TASKGENIUS Core API - Tasks Module

Phase 2: Task CRUD with MongoDB.
"""

from app.tasks.router import router as tasks_router

__all__ = ["tasks_router"]
