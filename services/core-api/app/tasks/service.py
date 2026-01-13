"""
TASKGENIUS Core API - Task Service

Business logic for task operations including urgency computation.
"""

from datetime import datetime, timezone, timedelta
from typing import Optional, List, Callable

from app.tasks.models import Task
from app.tasks.repository import TaskRepositoryInterface
from app.tasks.enums import TaskStatus, UrgencyLevel
from app.tasks.schemas import TaskCreateRequest, TaskUpdateRequest, TaskResponse


class TaskService:
    """Service layer for task business logic."""

    def __init__(
        self,
        repository: TaskRepositoryInterface,
        clock: Optional[Callable[[], datetime]] = None,
    ):
        """
        Initialize the task service.
        
        Args:
            repository: Task repository implementation
            clock: Optional clock function for testing (returns current datetime)
        """
        self.repository = repository
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    def _now(self) -> datetime:
        """Get current time using the configured clock."""
        return self._clock()

    @staticmethod
    def compute_urgency(
        task: Task,
        now: Optional[datetime] = None,
    ) -> UrgencyLevel:
        """
        Compute derived urgency level from task deadline and current time.
        
        Urgency classification per docs/requirements.en.md:
        - NO_DEADLINE: deadline is missing
        - OVERDUE: deadline passed AND status is not DONE/CANCELED
        - DUE_TODAY: deadline is today
        - DUE_SOON: deadline within next 7 days
        - NOT_SOON: deadline more than 7 days away
        """
        if task.deadline is None:
            return UrgencyLevel.NO_DEADLINE

        if now is None:
            now = datetime.now(timezone.utc)

        # Ensure both datetimes are timezone-aware for comparison
        deadline = task.deadline
        if deadline.tzinfo is None:
            deadline = deadline.replace(tzinfo=timezone.utc)

        # Get dates for comparison (ignore time component for day-level checks)
        today = now.date()
        deadline_date = deadline.date()

        # Check if task is closed (DONE or CANCELED)
        is_closed = task.status in (TaskStatus.DONE, TaskStatus.CANCELED)

        # OVERDUE: deadline passed and task is still open
        if deadline_date < today and not is_closed:
            return UrgencyLevel.OVERDUE

        # DUE_TODAY: deadline is today
        if deadline_date == today:
            return UrgencyLevel.DUE_TODAY

        # DUE_SOON: within next 7 days
        days_until = (deadline_date - today).days
        if 1 <= days_until <= 7:
            return UrgencyLevel.DUE_SOON

        # NOT_SOON: more than 7 days away
        return UrgencyLevel.NOT_SOON

    def _task_to_response(self, task: Task) -> TaskResponse:
        """Convert a Task model to TaskResponse with computed urgency."""
        return TaskResponse(
            id=task.id,
            owner_id=task.owner_id,
            title=task.title,
            status=task.status,
            priority=task.priority,
            description=task.description,
            category=task.category,
            deadline=task.deadline,
            estimate_bucket=task.estimate_bucket,
            urgency=self.compute_urgency(task, self._now()),
            created_at=task.created_at,
            updated_at=task.updated_at,
        )

    async def create_task(
        self,
        owner_id: str,
        request: TaskCreateRequest,
    ) -> TaskResponse:
        """Create a new task for the owner."""
        task = Task.create(
            owner_id=owner_id,
            title=request.title,
            status=request.status,
            priority=request.priority,
            description=request.description,
            category=request.category,
            deadline=request.deadline,
            estimate_bucket=request.estimate_bucket,
        )
        await self.repository.create(task)
        return self._task_to_response(task)

    async def get_task(self, task_id: str, owner_id: str) -> Optional[TaskResponse]:
        """Get a task by ID, scoped to owner."""
        task = await self.repository.get_by_id(task_id, owner_id)
        if task is None:
            return None
        return self._task_to_response(task)

    async def list_tasks(
        self,
        owner_id: str,
        status: Optional[TaskStatus] = None,
        deadline_before: Optional[datetime] = None,
        deadline_after: Optional[datetime] = None,
        exclude_statuses: Optional[List[TaskStatus]] = None,
        completed_since: Optional[datetime] = None,
    ) -> List[TaskResponse]:
        """List tasks for owner with optional filters."""
        tasks = await self.repository.list_by_owner(
            owner_id=owner_id,
            status=status,
            deadline_before=deadline_before,
            deadline_after=deadline_after,
            exclude_statuses=exclude_statuses,
            completed_since=completed_since,
        )
        return [self._task_to_response(task) for task in tasks]

    async def update_task(
        self,
        task_id: str,
        owner_id: str,
        request: TaskUpdateRequest,
    ) -> Optional[TaskResponse]:
        """Update a task, scoped to owner."""
        # Build updates dict from non-None fields
        updates = {}
        if request.title is not None:
            updates["title"] = request.title
        if request.status is not None:
            updates["status"] = request.status.value
        if request.priority is not None:
            updates["priority"] = request.priority.value
        if request.description is not None:
            updates["description"] = request.description
        if request.category is not None:
            updates["category"] = request.category.value
        if request.deadline is not None:
            updates["deadline"] = request.deadline
        if request.estimate_bucket is not None:
            updates["estimate_bucket"] = request.estimate_bucket.value

        # Handle explicit null for optional fields (allow clearing)
        request_data = request.model_dump(exclude_unset=True)
        if "description" in request_data and request_data["description"] is None:
            updates["description"] = None
        if "category" in request_data and request_data["category"] is None:
            updates["category"] = None
        if "deadline" in request_data and request_data["deadline"] is None:
            updates["deadline"] = None
        if "estimate_bucket" in request_data and request_data["estimate_bucket"] is None:
            updates["estimate_bucket"] = None

        if not updates:
            # No updates provided, just return current task
            return await self.get_task(task_id, owner_id)
            
        if request.status is not None:
            current = await self.repository.get_by_id(task_id, owner_id)
            if current is None:
                return None
            
            prev_status = current.status
            next_status = request.status

            if prev_status != TaskStatus.DONE and next_status == TaskStatus.DONE:
                updates["completed_at"] = self._now()

            if prev_status == TaskStatus.DONE and next_status != TaskStatus.DONE:
                updates["completed_at"] = None

        task = await self.repository.update(task_id, owner_id, updates)
        if task is None:
            return None
        return self._task_to_response(task)

    async def delete_task(self, task_id: str, owner_id: str) -> bool:
        """Delete a task, scoped to owner."""
        return await self.repository.delete(task_id, owner_id)

    async def count_tasks(self, owner_id: str) -> int:
        """Count total tasks for owner."""
        return await self.repository.count_by_owner(owner_id)
