import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.suggestions.schemas import SuggestRequest, SuggestResponse
from app.suggestions.dependencies import get_suggestions_service
from app.suggestions.service import SuggestionsService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/interpret", tags=["Interpret"])


@router.post("", response_model=SuggestResponse)
async def interpret_message(
    request: SuggestRequest,
    service: Annotated[SuggestionsService, Depends(get_suggestions_service)],
) -> SuggestResponse:
    """Generate task suggestions from user message."""
    if not request.message.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Message cannot be empty")
    
    if not request.user_id.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User ID cannot be empty")
    
    try:
        return await service.generate_suggestions(
            message=request.message.strip(),
            user_id=request.user_id.strip(),
            tasks=request.tasks,
        )
    except Exception as e:
        logger.error(f"Error generating suggestions: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to generate suggestions")
