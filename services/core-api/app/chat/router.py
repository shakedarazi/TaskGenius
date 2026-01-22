from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.auth.dependencies import CurrentUser
from app.tasks.repository import TaskRepositoryInterface
from app.tasks.router import get_task_repository
from app.chat.schemas import ChatRequest, ChatResponse
from app.chat.service import process_message

router = APIRouter(prefix="/chat", tags=["Chat"])


@router.post("", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    current_user: CurrentUser,
    task_repository: Annotated[TaskRepositoryInterface, Depends(get_task_repository)],
) -> ChatResponse:
    """Process chat message or selection."""
    if not request.message and request.selection is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Either message or selection is required")
    
    return await process_message(
        user_id=current_user.id,
        message=request.message,
        selection=request.selection,
        deadline=request.deadline,
        task_repository=task_repository,
    )
