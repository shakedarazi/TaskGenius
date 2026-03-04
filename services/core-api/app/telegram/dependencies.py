"""
TASKGENIUS Core API - Telegram Dependencies

FastAPI dependency injection for Telegram-related services and repositories.
"""

from typing import Annotated

from fastapi import Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.database import get_database
from app.auth.repository import MongoUserRepository
from app.tasks.repository import TaskRepository
from app.telegram.repository import (
    MongoTelegramVerificationRepository,
    MongoTelegramUpdateRepository,
)
from app.telegram.weekly_repository import MongoTelegramWeeklySummaryRepository
from app.telegram.service import TelegramService
from app.telegram.weekly_service import TelegramWeeklySummaryService
from app.telegram.adapter import TelegramAdapter
from app.insights.service import InsightsService


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


async def get_weekly_summary_service(
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)]
) -> TelegramWeeklySummaryService:
    """Dependency to get Telegram weekly summary service instance."""
    user_repo = MongoUserRepository(db)
    summary_repo = MongoTelegramWeeklySummaryRepository(db)
    task_repo = TaskRepository(db)
    insights_service = InsightsService()
    telegram_adapter = TelegramAdapter()
    return TelegramWeeklySummaryService(
        db=db,
        user_repo=user_repo,
        summary_repo=summary_repo,
        task_repo=task_repo,
        insights_service=insights_service,
        telegram_adapter=telegram_adapter,
    )


def get_user_repo(db: AsyncIOMotorDatabase) -> MongoUserRepository:
    """Helper to get MongoUserRepository for Telegram handlers."""
    return MongoUserRepository(db)


def get_verification_repo(db: AsyncIOMotorDatabase) -> MongoTelegramVerificationRepository:
    """Helper to get MongoTelegramVerificationRepository for Telegram handlers."""
    return MongoTelegramVerificationRepository(db)
