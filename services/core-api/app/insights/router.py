from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.database import get_database
from app.auth.dependencies import CurrentUser
from app.tasks.repository import TaskRepositoryInterface, TaskRepository
from app.tasks.router import get_task_repository
from app.insights.service import InsightsService
from app.insights.schemas import WeeklySummary


router = APIRouter(prefix="/insights", tags=["Insights"])


async def get_insights_service() -> InsightsService:
    """Dependency to get insights service instance."""
    return InsightsService()


@router.get("/weekly", response_model=WeeklySummary)
async def get_weekly_summary(
    current_user: CurrentUser,
    task_repository: Annotated[TaskRepositoryInterface, Depends(get_task_repository)],
    insights_service: Annotated[InsightsService, Depends(get_insights_service)],
) -> WeeklySummary:
    # Fetch all tasks for the user (ownership enforced by repository)
    from app.tasks.repository import TaskRepositoryInterface
    tasks = await task_repository.list_by_owner(current_user.id)
    
    # Generate summary with injected "now" (deterministic)
    now = datetime.now(timezone.utc)
    return insights_service.generate_weekly_summary(tasks, now)
