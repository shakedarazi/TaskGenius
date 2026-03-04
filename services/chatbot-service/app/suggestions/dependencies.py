"""
TASKGENIUS Chatbot Service - Suggestions Dependencies

FastAPI dependency injection for suggestions service.
"""

from app.suggestions.repository import get_llm_repository
from app.suggestions.service import SuggestionsService


def get_suggestions_service() -> SuggestionsService:
    """Dependency to get SuggestionsService instance."""
    repository = get_llm_repository()
    return SuggestionsService(repository)
