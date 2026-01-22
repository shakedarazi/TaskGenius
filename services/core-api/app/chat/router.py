from typing import Annotated

from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.database import get_database
from app.auth.dependencies import CurrentUser
from app.tasks.repository import TaskRepositoryInterface
from app.tasks.router import get_task_repository
from app.chat.service import ChatService
from app.chat.schemas import ChatRequest, ChatResponse


router = APIRouter(prefix="/chat", tags=["Chat"])


async def get_chat_service(
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)]
) -> ChatService:
    """Dependency to get chat service instance."""
    return ChatService(db)


@router.post("", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    current_user: CurrentUser,
    chat_service: Annotated[ChatService, Depends(get_chat_service)],
    task_repository: Annotated[TaskRepositoryInterface, Depends(get_task_repository)],
) -> ChatResponse:
    return await chat_service.process_message(
        user_id=current_user.id,
        message=request.message,
        task_repository=task_repository,
        conversation_history=request.conversation_history,
    )
