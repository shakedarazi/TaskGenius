"""
TASKGENIUS Chatbot Service - Router

Internal API endpoints for chatbot-service.
Accessible only from core-api via internal HTTP.
"""

from fastapi import APIRouter
from app.schemas import ChatRequest, ChatResponse
from app.service import ChatbotService


router = APIRouter(prefix="/interpret", tags=["Interpret"])


# Service instance (can be overridden in tests)
_chatbot_service = ChatbotService()


def get_chatbot_service() -> ChatbotService:
    """Get chatbot service instance."""
    return _chatbot_service


def set_chatbot_service(service: ChatbotService) -> None:
    """Set chatbot service (for testing)."""
    global _chatbot_service
    _chatbot_service = service


@router.post("", response_model=ChatResponse)
async def interpret_message(request: ChatRequest) -> ChatResponse:
    """
    Interpret a user message and generate a conversational response.
    
    This endpoint is called by core-api only.
    It does NOT access databases or mutate state.
    
    Args:
        request: Chat request with message and context data
    
    Returns:
        ChatResponse with conversational reply and suggestions
    """
    service = get_chatbot_service()
    return await service.generate_response(request)
