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
    return TaskRepository(db)


async def get_task_service(
    repository: Annotated[TaskRepositoryInterface, Depends(get_task_repository)]
) -> TaskService:
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
    include_closed: bool = Query(
        default=False,
        description="If true, include DONE/CANCELED tasks. Default is false (active only).",
    ),
    completed_since: Optional[datetime] = Query(
        default=None,
        description="For DONE tasks: return only tasks with updated_at >= completed_since",
    ),
) -> TaskListResponse:
    if completed_since is not None and status_filter not in (None, TaskStatus.DONE):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="completed_since is only supported with status=done",
        )

    # Default Active view: exclude closed statuses
    exclude_statuses = None
    if status_filter is None and not include_closed and completed_since is None:
        exclude_statuses = [TaskStatus.DONE, TaskStatus.CANCELED]

    # If completed_since provided, force DONE
    effective_status = status_filter
    if completed_since is not None:
        effective_status = TaskStatus.DONE

    tasks = await service.list_tasks(
        owner_id=current_user.id,
        status=effective_status,
        deadline_before=deadline_before,
        deadline_after=deadline_after,
        exclude_statuses=exclude_statuses,
        completed_since=completed_since,
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
    deleted = await service.delete_task(task_id, current_user.id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )
    return TaskDeleteResponse(message="Task deleted successfully", id=task_id)
