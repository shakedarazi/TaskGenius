from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from app.tasks.enums import TaskStatus, TaskPriority, TaskCategory, UrgencyLevel


class TaskSummary(BaseModel):
    id: str
    title: str
    status: TaskStatus
    priority: TaskPriority
    category: Optional[TaskCategory] = None
    deadline: Optional[datetime] = None
    urgency: UrgencyLevel


class CompletedTasksSummary(BaseModel):
    count: int = Field(description="Number of tasks completed in the last 7 days")
    tasks: List[TaskSummary] = Field(description="List of completed tasks")


class HighPriorityTasksSummary(BaseModel):
    count: int = Field(description="Number of open high-priority tasks")
    tasks: List[TaskSummary] = Field(description="List of high-priority tasks (HIGH or URGENT)")


class UpcomingTasksSummary(BaseModel):
    count: int = Field(description="Number of tasks due within 7 days")
    tasks: List[TaskSummary] = Field(description="List of upcoming tasks")


class OverdueTasksSummary(BaseModel):
    count: int = Field(description="Number of overdue tasks")
    tasks: List[TaskSummary] = Field(description="List of overdue tasks")


class WeeklySummary(BaseModel):
    generated_at: datetime = Field(description="Timestamp when report was generated")
    period_start: datetime = Field(description="Start of the lookback period (7 days ago)")
    period_end: datetime = Field(description="End of the lookahead period (7 days from now)")

    completed: CompletedTasksSummary = Field(description="Tasks completed in the last 7 days")
    high_priority: HighPriorityTasksSummary = Field(description="Open tasks with HIGH or URGENT priority")
    upcoming: UpcomingTasksSummary = Field(description="Tasks due within the next 7 days")
    overdue: OverdueTasksSummary = Field(description="Tasks past their deadline")
