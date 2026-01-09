"""
TASKGENIUS Core API - Insights Schemas

Pydantic models for weekly insights responses.
Schema follows docs/insights_weekly_summary_spec.md.
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from app.tasks.enums import TaskStatus, TaskPriority, TaskCategory, UrgencyLevel


class TaskSummary(BaseModel):
    """Minimal task representation for insights summaries."""

    id: str
    title: str
    status: TaskStatus
    priority: TaskPriority
    category: Optional[TaskCategory] = None
    deadline: Optional[datetime] = None
    urgency: UrgencyLevel


class CompletedTasksSummary(BaseModel):
    """Summary of completed tasks in the time window."""

    count: int = Field(description="Number of tasks completed in the last 7 days")
    tasks: List[TaskSummary] = Field(description="List of completed tasks")


class HighPriorityTasksSummary(BaseModel):
    """Summary of open high-priority tasks."""

    count: int = Field(description="Number of open high-priority tasks")
    tasks: List[TaskSummary] = Field(description="List of high-priority tasks (HIGH or URGENT)")


class UpcomingTasksSummary(BaseModel):
    """Summary of tasks due within the next 7 days."""

    count: int = Field(description="Number of tasks due within 7 days")
    tasks: List[TaskSummary] = Field(description="List of upcoming tasks")


class OverdueTasksSummary(BaseModel):
    """Summary of overdue tasks."""

    count: int = Field(description="Number of overdue tasks")
    tasks: List[TaskSummary] = Field(description="List of overdue tasks")


class WeeklySummary(BaseModel):
    """
    Complete weekly insights summary.
    
    Per docs/insights_weekly_summary_spec.md:
    - Completed tasks (last 7 days)
    - Open high-priority tasks
    - Tasks due within next 7 days
    - Overdue tasks
    """

    generated_at: datetime = Field(description="Timestamp when report was generated")
    period_start: datetime = Field(description="Start of the lookback period (7 days ago)")
    period_end: datetime = Field(description="End of the lookahead period (7 days from now)")

    completed: CompletedTasksSummary = Field(description="Tasks completed in the last 7 days")
    high_priority: HighPriorityTasksSummary = Field(description="Open tasks with HIGH or URGENT priority")
    upcoming: UpcomingTasksSummary = Field(description="Tasks due within the next 7 days")
    overdue: OverdueTasksSummary = Field(description="Tasks past their deadline")
