"""
TASKGENIUS Core API - Task Schemas

Pydantic models for task API requests and responses.
"""

from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field

from app.tasks.enums import (
    TaskStatus,
    TaskPriority,
    TaskCategory,
    EstimateBucket,
    UrgencyLevel,
)


class TaskCreateRequest(BaseModel):
    """Request model for creating a task."""

    title: str = Field(min_length=1, max_length=500, description="Task title")
    status: TaskStatus = Field(default=TaskStatus.OPEN, description="Task status")
    priority: TaskPriority = Field(default=TaskPriority.MEDIUM, description="Task priority")
    description: Optional[str] = Field(default=None, max_length=5000, description="Task description")
    category: Optional[TaskCategory] = Field(default=None, description="Task category")
    deadline: Optional[datetime] = Field(default=None, description="Task deadline")
    estimate_bucket: Optional[EstimateBucket] = Field(default=None, description="Time estimate bucket")


class TaskUpdateRequest(BaseModel):
    """Request model for updating a task."""

    title: Optional[str] = Field(default=None, min_length=1, max_length=500, description="Task title")
    status: Optional[TaskStatus] = Field(default=None, description="Task status")
    priority: Optional[TaskPriority] = Field(default=None, description="Task priority")
    description: Optional[str] = Field(default=None, max_length=5000, description="Task description")
    category: Optional[TaskCategory] = Field(default=None, description="Task category")
    deadline: Optional[datetime] = Field(default=None, description="Task deadline")
    estimate_bucket: Optional[EstimateBucket] = Field(default=None, description="Time estimate bucket")


class TaskResponse(BaseModel):
    """Response model for a single task."""

    id: str = Field(description="Task ID")
    owner_id: str = Field(description="Owner user ID")
    title: str = Field(description="Task title")
    status: TaskStatus = Field(description="Task status")
    priority: TaskPriority = Field(description="Task priority")
    description: Optional[str] = Field(default=None, description="Task description")
    category: Optional[TaskCategory] = Field(default=None, description="Task category")
    deadline: Optional[datetime] = Field(default=None, description="Task deadline")
    estimate_bucket: Optional[EstimateBucket] = Field(default=None, description="Time estimate bucket")
    urgency: UrgencyLevel = Field(description="Derived urgency level based on deadline")
    created_at: datetime = Field(description="Creation timestamp")
    updated_at: datetime = Field(description="Last update timestamp")


class TaskListResponse(BaseModel):
    """Response model for a list of tasks."""

    tasks: List[TaskResponse] = Field(description="List of tasks")
    total: int = Field(description="Total number of tasks in the list")


class TaskDeleteResponse(BaseModel):
    """Response model for task deletion."""

    message: str = Field(description="Success message")
    id: str = Field(description="Deleted task ID")
