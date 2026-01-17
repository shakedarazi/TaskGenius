"""
TASKGENIUS Chatbot Service - Router

Internal API endpoints for chatbot-service.
Accessible only from core-api via internal HTTP.
"""

import logging
from fastapi import APIRouter, HTTPException, status
from app.schemas import ChatRequest, ChatResponse
from app.service import ChatbotService

logger = logging.getLogger(__name__)


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
    
    Raises:
        HTTPException: If request validation fails or service error occurs
    """
    try:
        logger.info(f"Processing message for user {request.user_id}: {request.message[:50]}...")
        
        # Validate request
        if not request.message or not request.message.strip():
            logger.warning("Empty message received")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Message cannot be empty",
            )
        
        if not request.user_id or not request.user_id.strip():
            logger.warning("Empty user_id received")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User ID cannot be empty",
            )
        
        service = get_chatbot_service()
        response = await service.generate_response(request)
        
        logger.info(f"Generated response with intent: {response.intent}")
        return response
        
    except HTTPException:
        # Re-raise HTTP exceptions (validation errors)
        raise
    except Exception as e:
        # Log unexpected errors
        logger.error(f"Unexpected error processing message: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while processing your message. Please try again later.",
        )
