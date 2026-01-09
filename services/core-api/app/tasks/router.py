"""
TASKGENIUS Core API - Task Router

CRUD endpoints for task management.
All endpoints are JWT-protected and user-scoped.
"""

from datetime import datetime
from typing import Optional, Annotated

from fastapi import APIRouter, HTTPException, status, Depends, Query
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.database import get_database
from app.auth.dependencies import CurrentUser
from app.tasks.service import TaskService
from app.tasks.repository import TaskRepository, TaskRepositoryInterface
from app.tasks.schemas import (
    TaskCreateRequest,
    TaskUpdateRequest,
    TaskResponse,
    TaskListResponse,
    TaskDeleteResponse,
)
from app.tasks.enums import TaskStatus


router = APIRouter(prefix="/tasks", tags=["Tasks"])


async def get_task_repository(
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)]
) -> TaskRepositoryInterface:
    """Dependency to get task repository instance."""
    return TaskRepository(db)


async def get_task_service(
    repository: Annotated[TaskRepositoryInterface, Depends(get_task_repository)]
) -> TaskService:
    """Dependency to get task service instance."""
    return TaskService(repository)


@router.post(
    "",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new task",
)
async def create_task(
    request: TaskCreateRequest,
    current_user: CurrentUser,
    service: Annotated[TaskService, Depends(get_task_service)],
) -> TaskResponse:
    """
    Create a new task for the authenticated user.
    
    The task is automatically associated with the current user.
    """
    return await service.create_task(
        owner_id=current_user.id,
        request=request,
    )


@router.get(
    "",
    response_model=TaskListResponse,
    summary="List tasks",
)
async def list_tasks(
    current_user: CurrentUser,
    service: Annotated[TaskService, Depends(get_task_service)],
    status_filter: Optional[TaskStatus] = Query(
        default=None,
        alias="status",
        description="Filter by task status",
    ),
    deadline_before: Optional[datetime] = Query(
        default=None,
        description="Filter tasks with deadline before this date",
    ),
    deadline_after: Optional[datetime] = Query(
        default=None,
        description="Filter tasks with deadline after this date",
    ),
) -> TaskListResponse:
    """
    List all tasks for the authenticated user.
    
    Supports filtering by status and deadline range.
    """
    tasks = await service.list_tasks(
        owner_id=current_user.id,
        status=status_filter,
        deadline_before=deadline_before,
        deadline_after=deadline_after,
    )
    return TaskListResponse(tasks=tasks, total=len(tasks))


@router.get(
    "/{task_id}",
    response_model=TaskResponse,
    summary="Get a task by ID",
)
async def get_task(
    task_id: str,
    current_user: CurrentUser,
    service: Annotated[TaskService, Depends(get_task_service)],
) -> TaskResponse:
    """
    Get a specific task by ID.
    
    Returns 404 if the task doesn't exist or belongs to another user.
    """
    task = await service.get_task(task_id, current_user.id)
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )
    return task


@router.patch(
    "/{task_id}",
    response_model=TaskResponse,
    summary="Update a task",
)
async def update_task(
    task_id: str,
    request: TaskUpdateRequest,
    current_user: CurrentUser,
    service: Annotated[TaskService, Depends(get_task_service)],
) -> TaskResponse:
    """
    Update a task by ID.
    
    Only provided fields will be updated.
    Returns 404 if the task doesn't exist or belongs to another user.
    """
    task = await service.update_task(task_id, current_user.id, request)
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )
    return task


@router.delete(
    "/{task_id}",
    response_model=TaskDeleteResponse,
    summary="Delete a task",
)
async def delete_task(
    task_id: str,
    current_user: CurrentUser,
    service: Annotated[TaskService, Depends(get_task_service)],
) -> TaskDeleteResponse:
    """
    Delete a task by ID.
    
    Returns 404 if the task doesn't exist or belongs to another user.
    """
    deleted = await service.delete_task(task_id, current_user.id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )
    return TaskDeleteResponse(message="Task deleted successfully", id=task_id)
