from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends

from app.auth.dependencies import CurrentUser
from app.tasks.repository import TaskRepositoryInterface
from app.tasks.dependencies import get_task_repository
from app.insights.service import InsightsService
from app.insights.schemas import WeeklySummary
from app.insights.dependencies import get_insights_service


router = APIRouter(prefix="/insights", tags=["Insights"])


@router.get("/weekly", response_model=WeeklySummary)
async def get_weekly_summary(
    current_user: CurrentUser,
    task_repository: Annotated[TaskRepositoryInterface, Depends(get_task_repository)],
    insights_service: Annotated[InsightsService, Depends(get_insights_service)],
) -> WeeklySummary:
    # Fetch all tasks for the user (ownership enforced by repository)
    tasks = await task_repository.list_by_owner(current_user.id)
    
    # Generate summary with injected "now" (deterministic)
    now = datetime.now(timezone.utc)
    return insights_service.generate_weekly_summary(tasks, now)
