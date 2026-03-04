"""
TASKGENIUS Core API - Insights Dependencies

FastAPI dependency injection for insights-related services.
"""

from app.insights.service import InsightsService


async def get_insights_service() -> InsightsService:
    """Dependency to get InsightsService instance."""
    return InsightsService()
