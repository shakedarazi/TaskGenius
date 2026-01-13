"""
TASKGENIUS Core API - Task Repository

Repository pattern for task data access.
Includes MongoDB implementation for runtime and interface for testing.
"""

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Optional, List

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.tasks.models import Task
from app.tasks.enums import TaskStatus


class TaskRepositoryInterface(ABC):
    """
    Abstract interface for task repository.

    Enables swapping implementations (MongoDB for runtime, in-memory for tests).
    All operations are scoped by owner_id to enforce ownership isolation.
    """

    @abstractmethod
    async def create(self, task: Task) -> Task:
        pass

    @abstractmethod
    async def get_by_id(self, task_id: str, owner_id: str) -> Optional[Task]:
        pass

    @abstractmethod
    async def list_by_owner(
        self,
        owner_id: str,
        status: Optional[TaskStatus] = None,
        deadline_before: Optional[datetime] = None,
        deadline_after: Optional[datetime] = None,
        exclude_statuses: Optional[List[TaskStatus]] = None,
        completed_since: Optional[datetime] = None,
    ) -> List[Task]:
        """List tasks for owner with optional filters."""
        pass

    @abstractmethod
    async def update(self, task_id: str, owner_id: str, updates: dict) -> Optional[Task]:
        pass

    @abstractmethod
    async def delete(self, task_id: str, owner_id: str) -> bool:
        pass

    @abstractmethod
    async def count_by_owner(self, owner_id: str) -> int:
        pass


class TaskRepository(TaskRepositoryInterface):
    """
    MongoDB implementation of the task repository.

    All queries are scoped by owner_id to enforce ownership isolation.
    Only core-api may access MongoDB per architecture constraints.
    """

    COLLECTION_NAME = "tasks"

    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.collection = db[self.COLLECTION_NAME]

    async def create(self, task: Task) -> Task:
        await self.collection.insert_one(task.to_dict())
        return task

    async def get_by_id(self, task_id: str, owner_id: str) -> Optional[Task]:
        doc = await self.collection.find_one({"_id": task_id, "owner_id": owner_id})
        if doc is None:
            return None
        return Task.from_dict(doc)

    async def list_by_owner(
        self,
        owner_id: str,
        status: Optional[TaskStatus] = None,
        deadline_before: Optional[datetime] = None,
        deadline_after: Optional[datetime] = None,
        exclude_statuses: Optional[List[TaskStatus]] = None,
        completed_since: Optional[datetime] = None,
    ) -> List[Task]:
        query: dict = {"owner_id": owner_id}

        # Explicit status filter wins
        if status is not None:
            query["status"] = status.value
        elif exclude_statuses:
            query["status"] = {"$nin": [s.value for s in exclude_statuses]}

        if deadline_before is not None or deadline_after is not None:
            query["deadline"] = {}
            if deadline_before is not None:
                query["deadline"]["$lte"] = deadline_before
            if deadline_after is not None:
                query["deadline"]["$gte"] = deadline_after
            if not query["deadline"]:
                del query["deadline"]

        # Completed filter: use updated_at >= completed_since
        # This is intended for the "Completed" screen / query.
        if completed_since is not None:
            # If caller asks "completed since", we should only return DONE tasks
            query["status"] = TaskStatus.DONE.value
            query["$or"] = [
                {"completed_at": {"$gte": completed_since}},
                {"completed_at": None, "updated_at": {"$gte": completed_since}},
                {"completed_at": {"$exists": False}, "updated_at": {"$gte": completed_since}},
            ]


        cursor = self.collection.find(query).sort("created_at", -1)
        tasks: List[Task] = []
        async for doc in cursor:
            tasks.append(Task.from_dict(doc))
        return tasks

    async def update(self, task_id: str, owner_id: str, updates: dict) -> Optional[Task]:
        updates["updated_at"] = datetime.now(timezone.utc)

        result = await self.collection.find_one_and_update(
            {"_id": task_id, "owner_id": owner_id},
            {"$set": updates},
            return_document=True,
        )
        if result is None:
            return None
        return Task.from_dict(result)

    async def delete(self, task_id: str, owner_id: str) -> bool:
        result = await self.collection.delete_one({"_id": task_id, "owner_id": owner_id})
        return result.deleted_count > 0

    async def count_by_owner(self, owner_id: str) -> int:
        return await self.collection.count_documents({"owner_id": owner_id})


class InMemoryTaskRepository(TaskRepositoryInterface):
    """
    In-memory implementation for CI-safe testing.
    """

    def __init__(self):
        self._tasks: dict[str, Task] = {}

    def clear(self) -> None:
        self._tasks.clear()

    async def create(self, task: Task) -> Task:
        self._tasks[task.id] = task
        return task

    async def get_by_id(self, task_id: str, owner_id: str) -> Optional[Task]:
        task = self._tasks.get(task_id)
        if task is None or task.owner_id != owner_id:
            return None
        return task

    async def list_by_owner(
        self,
        owner_id: str,
        status: Optional[TaskStatus] = None,
        deadline_before: Optional[datetime] = None,
        deadline_after: Optional[datetime] = None,
        exclude_statuses: Optional[List[TaskStatus]] = None,
        completed_since: Optional[datetime] = None,
    ) -> List[Task]:
        results: List[Task] = []

        for task in self._tasks.values():
            if task.owner_id != owner_id:
                continue

            # Completed_since implies DONE only + updated_at window
            if completed_since is not None:
                if task.status != TaskStatus.DONE:
                    continue
                task_updated = task.updated_at
                if task_updated.tzinfo is None:
                    task_updated = task_updated.replace(tzinfo=timezone.utc)
                if task_updated < completed_since:
                    continue

            if status is not None and task.status != status:
                continue

            if status is None and exclude_statuses and task.status in exclude_statuses:
                continue

            if deadline_before is not None and task.deadline is not None:
                if task.deadline > deadline_before:
                    continue

            if deadline_after is not None and task.deadline is not None:
                if task.deadline < deadline_after:
                    continue

            results.append(task)

        results.sort(key=lambda t: t.created_at, reverse=True)
        return results

    async def update(self, task_id: str, owner_id: str, updates: dict) -> Optional[Task]:
        task = self._tasks.get(task_id)
        if task is None or task.owner_id != owner_id:
            return None

        for key, value in updates.items():
            if hasattr(task, key):
                setattr(task, key, value)

        task.updated_at = datetime.now(timezone.utc)
        return task

    async def delete(self, task_id: str, owner_id: str) -> bool:
        task = self._tasks.get(task_id)
        if task is None or task.owner_id != owner_id:
            return False
        del self._tasks[task_id]
        return True

    async def count_by_owner(self, owner_id: str) -> int:
        return sum(1 for t in self._tasks.values() if t.owner_id == owner_id)
