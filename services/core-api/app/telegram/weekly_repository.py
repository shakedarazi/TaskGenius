"""
TASKGENIUS Core API - Telegram Weekly Summary Repository

Repository for tracking sent weekly Telegram summaries.
Prevents duplicate sends within the same week.
"""

from abc import ABC, abstractmethod
from datetime import date, datetime, timezone
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorDatabase


class TelegramWeeklySummaryRepositoryInterface(ABC):
    """Abstract interface for weekly summary idempotency."""

    @abstractmethod
    async def has_summary_sent(self, user_id: str, week_start: date) -> bool:
        """Check if summary was already sent for this user/week."""
        pass

    @abstractmethod
    async def mark_summary_sent(self, user_id: str, week_start: date) -> None:
        """Mark summary as sent for this user/week."""
        pass


class MongoTelegramWeeklySummaryRepository(TelegramWeeklySummaryRepositoryInterface):
    """MongoDB implementation for weekly summary idempotency."""

    COLLECTION_NAME = "telegram_weekly_summaries"

    def __init__(self, db: AsyncIOMotorDatabase):
        self.collection = db[self.COLLECTION_NAME]

    async def has_summary_sent(self, user_id: str, week_start: date) -> bool:
        """Check if summary was already sent for this user/week."""
        doc = await self.collection.find_one({
            "user_id": user_id,
            "week_start": week_start.isoformat(),
        })
        return doc is not None

    async def mark_summary_sent(self, user_id: str, week_start: date) -> None:
        """Mark summary as sent for this user/week."""
        await self.collection.update_one(
            {
                "user_id": user_id,
                "week_start": week_start.isoformat(),
            },
            {
                "$set": {
                    "user_id": user_id,
                    "week_start": week_start.isoformat(),
                    "sent_at": datetime.now(timezone.utc),
                }
            },
            upsert=True,
        )
