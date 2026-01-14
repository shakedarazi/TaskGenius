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
from app.auth.dependencies import CurrentUser
from app.auth.repository import MongoUserRepository
from app.telegram.repository import (
    MongoTelegramVerificationRepository,
    MongoTelegramUpdateRepository,
)
from app.telegram.schemas import (
    TelegramUpdate,
    TelegramLinkStartResponse,
    TelegramStatusResponse,
    TelegramNotificationsToggleRequest,
    TelegramUnlinkResponse,
)
from app.telegram.service import TelegramService


router = APIRouter(prefix="/telegram", tags=["Telegram"])


async def get_telegram_service(
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)]
) -> TelegramService:
    """Dependency to get Telegram service instance with MongoDB repositories."""
    user_repo = MongoUserRepository(db)
    verification_repo = MongoTelegramVerificationRepository(db)
    update_repo = MongoTelegramUpdateRepository(db)
    return TelegramService(
        db=db,
        user_repository=user_repo,
        verification_repository=verification_repo,
        update_repository=update_repo,
    )


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


def _get_user_repo(db: AsyncIOMotorDatabase) -> MongoUserRepository:
    """Helper to get user repository instance."""
    return MongoUserRepository(db)


def _get_verification_repo(db: AsyncIOMotorDatabase) -> MongoTelegramVerificationRepository:
    """Helper to get verification repository instance."""
    return MongoTelegramVerificationRepository(db)


@router.post("/link/start", response_model=TelegramLinkStartResponse)
async def start_telegram_link(
    current_user: CurrentUser,
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)],
) -> TelegramLinkStartResponse:
    """
    Start Telegram linking flow for the authenticated user.
    
    Generates a short-lived verification code that the user must send
    to the Telegram bot in order to link accounts.
    """
    import secrets
    import string
    from datetime import datetime, timedelta, timezone
    
    verification_repo = _get_verification_repo(db)
    
    # Generate 6-character alphanumeric code
    alphabet = string.ascii_letters + string.digits
    code = "".join(secrets.choice(alphabet) for _ in range(6))
    
    # Code expires in 10 minutes
    ttl_minutes = 10
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=ttl_minutes)
    
    await verification_repo.create_code(
        user_id=current_user.id,
        code=code,
        expires_at=expires_at,
    )
    
    return TelegramLinkStartResponse(
        code=code,
        expires_in_seconds=ttl_minutes * 60,
    )


@router.get("/status", response_model=TelegramStatusResponse)
async def get_telegram_status(
    current_user: CurrentUser,
) -> TelegramStatusResponse:
    """Return current Telegram linking status for the authenticated user."""
    if not current_user.telegram:
        return TelegramStatusResponse(
            linked=False,
            telegram_username=None,
            notifications_enabled=False,
        )
    
    return TelegramStatusResponse(
        linked=True,
        telegram_username=current_user.telegram.telegram_username,
        notifications_enabled=current_user.telegram.notifications_enabled,
    )


@router.post("/unlink", response_model=TelegramUnlinkResponse)
async def unlink_telegram(
    current_user: CurrentUser,
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)],
) -> TelegramUnlinkResponse:
    """Unlink Telegram account from the authenticated user."""
    user_repo = _get_user_repo(db)
    await user_repo.remove_telegram_link(current_user.id)
    return TelegramUnlinkResponse(unlinked=True)


@router.patch("/notifications", response_model=TelegramStatusResponse)
async def toggle_telegram_notifications(
    body: TelegramNotificationsToggleRequest,
    current_user: CurrentUser,
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)],
) -> TelegramStatusResponse:
    """
    Enable or disable Telegram notifications for the authenticated user.
    
    Requires that the user has already linked their Telegram account.
    """
    user_repo = _get_user_repo(db)
    
    # Check if user has Telegram link before trying to update
    if not current_user.telegram:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Telegram account not linked.",
        )
    
    # Update notifications (only if telegram link exists)
    user = await user_repo.set_notifications_enabled(current_user.id, body.enabled)
    if not user or not user.telegram:
        # This shouldn't happen if we checked above, but handle edge case
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Telegram account not linked.",
        )
    
    return TelegramStatusResponse(
        linked=True,
        telegram_username=user.telegram.telegram_username,
        notifications_enabled=user.telegram.notifications_enabled,
    )
