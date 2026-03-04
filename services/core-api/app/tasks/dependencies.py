"""
TASKGENIUS Core API - Tasks Dependencies

FastAPI dependency injection for task-related services and repositories.
"""

from typing import Annotated

from fastapi import Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.database import get_database
from app.tasks.service import TaskService
from app.tasks.repository import TaskRepository, TaskRepositoryInterface


async def get_task_repository(
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)]
) -> TaskRepositoryInterface:
    """Dependency to get TaskRepository instance."""
    return TaskRepository(db)


async def get_task_service(
    repository: Annotated[TaskRepositoryInterface, Depends(get_task_repository)]
) -> TaskService:
    """Dependency to get TaskService instance."""
    return TaskService(repository)
