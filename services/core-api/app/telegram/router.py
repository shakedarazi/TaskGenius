"""
TASKGENIUS Core API - Telegram Router

API endpoints for Telegram webhook integration.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.database import get_database
from app.tasks.repository import TaskRepositoryInterface
from app.tasks.router import get_task_repository
from app.telegram.schemas import TelegramUpdate
from app.telegram.service import TelegramService


router = APIRouter(prefix="/telegram", tags=["Telegram"])


async def get_telegram_service(
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)]
) -> TelegramService:
    """Dependency to get Telegram service instance."""
    return TelegramService(db)


@router.post("/webhook")
async def telegram_webhook(
    update: TelegramUpdate,
    telegram_service: Annotated[TelegramService, Depends(get_telegram_service)],
    task_repository: Annotated[TaskRepositoryInterface, Depends(get_task_repository)],
) -> dict:
    """
    Telegram webhook endpoint.
    
    This endpoint:
    - Receives Telegram webhook updates
    - Processes messages through chat flow
    - Sends responses back to Telegram
    
    No authentication required (Telegram webhook validation should be done via secret token in production).
    """
    try:
        await telegram_service.process_webhook_update(update, task_repository)
        return {"ok": True}
    except Exception as e:
        # Log error but return success to Telegram (to avoid retries)
        # In production, proper error handling and logging should be implemented
        return {"ok": False, "error": str(e)}


@router.get("/webhook")
async def telegram_webhook_info() -> dict:
    """
    Webhook info endpoint (for verification).
    
    Telegram may send GET requests to verify webhook endpoint.
    """
    return {
        "status": "webhook_endpoint",
        "service": "TASKGENIUS Core API",
    }
