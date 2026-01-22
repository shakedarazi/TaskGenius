from datetime import datetime, timedelta, timezone
from typing import List, Optional

from app.tasks.models import Task
from app.tasks.enums import TaskStatus, TaskPriority, UrgencyLevel
from app.tasks.service import TaskService
from app.insights.schemas import (
    WeeklySummary,
    TaskSummary,
    CompletedTasksSummary,
    HighPriorityTasksSummary,
    UpcomingTasksSummary,
    OverdueTasksSummary,
)


class InsightsService:
    def __init__(self):
        pass  # Pure logic, no dependencies needed

    def _task_to_summary(self, task: Task, now: datetime) -> TaskSummary:
        """Convert a Task model to a TaskSummary for insights response."""
        return TaskSummary(
            id=task.id,
            title=task.title,
            status=task.status,
            priority=task.priority,
            category=task.category,
            deadline=task.deadline,
            urgency=TaskService.compute_urgency(task, now),
        )

    def _filter_completed_tasks(
        self,
        tasks: List[Task],
        since: datetime,
    ) -> List[Task]:
        completed = []
        for task in tasks:
            if task.status == TaskStatus.DONE:
                # Check if task was completed (updated to DONE) within the window
                task_updated = task.updated_at
                if task_updated.tzinfo is None:
                    task_updated = task_updated.replace(tzinfo=timezone.utc)
                if task_updated >= since:
                    completed.append(task)
        return completed

    def _filter_high_priority_open_tasks(self, tasks: List[Task]) -> List[Task]:
        high_priority = []
        open_statuses = (TaskStatus.OPEN, TaskStatus.IN_PROGRESS)
        high_priorities = (TaskPriority.HIGH, TaskPriority.URGENT)
        
        for task in tasks:
            if task.status in open_statuses and task.priority in high_priorities:
                high_priority.append(task)
        return high_priority

    def _filter_upcoming_tasks(
        self,
        tasks: List[Task],
        now: datetime,
        lookahead_days: int = 7,
    ) -> List[Task]:
        upcoming = []
        cutoff = now + timedelta(days=lookahead_days)
        excluded_statuses = (TaskStatus.DONE, TaskStatus.CANCELED)
        
        for task in tasks:
            if task.deadline is None:
                continue
            if task.status in excluded_statuses:
                continue
            
            deadline = task.deadline
            if deadline.tzinfo is None:
                deadline = deadline.replace(tzinfo=timezone.utc)
            
            # Include if deadline is today or in the future, within lookahead
            if now.date() <= deadline.date() <= cutoff.date():
                upcoming.append(task)
        
        return upcoming

    def _filter_overdue_tasks(self, tasks: List[Task], now: datetime) -> List[Task]:
        overdue = []
        excluded_statuses = (TaskStatus.DONE, TaskStatus.CANCELED)
        
        for task in tasks:
            if task.deadline is None:
                continue
            if task.status in excluded_statuses:
                continue
            
            deadline = task.deadline
            if deadline.tzinfo is None:
                deadline = deadline.replace(tzinfo=timezone.utc)
            
            if deadline.date() < now.date():
                overdue.append(task)
        
        return overdue

    def generate_weekly_summary(
        self,
        tasks: List[Task],
        now: datetime,
    ) -> WeeklySummary:
        # Time boundaries
        period_start = now - timedelta(days=7)
        period_end = now + timedelta(days=7)
        
        # Compute each section
        completed_tasks = self._filter_completed_tasks(tasks, period_start)
        high_priority_tasks = self._filter_high_priority_open_tasks(tasks)
        upcoming_tasks = self._filter_upcoming_tasks(tasks, now, lookahead_days=7)
        overdue_tasks = self._filter_overdue_tasks(tasks, now)
        
        # Sort tasks for consistent output
        completed_tasks.sort(key=lambda t: t.updated_at, reverse=True)
        high_priority_tasks.sort(key=lambda t: (t.priority != TaskPriority.URGENT, t.title))
        upcoming_tasks.sort(key=lambda t: t.deadline or now)
        overdue_tasks.sort(key=lambda t: t.deadline or now)
        
        # Build response
        return WeeklySummary(
            generated_at=now,
            period_start=period_start,
            period_end=period_end,
            completed=CompletedTasksSummary(
                count=len(completed_tasks),
                tasks=[self._task_to_summary(t, now) for t in completed_tasks],
            ),
            high_priority=HighPriorityTasksSummary(
                count=len(high_priority_tasks),
                tasks=[self._task_to_summary(t, now) for t in high_priority_tasks],
            ),
            upcoming=UpcomingTasksSummary(
                count=len(upcoming_tasks),
                tasks=[self._task_to_summary(t, now) for t in upcoming_tasks],
            ),
            overdue=OverdueTasksSummary(
                count=len(overdue_tasks),
                tasks=[self._task_to_summary(t, now) for t in overdue_tasks],
            ),
        )
