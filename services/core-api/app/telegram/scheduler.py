import asyncio
import logging
from datetime import datetime, timezone

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.config import settings
from app.telegram.weekly_service import TelegramWeeklySummaryService
from app.auth.repository import MongoUserRepository
from app.telegram.weekly_repository import MongoTelegramWeeklySummaryRepository
from app.tasks.repository import TaskRepository
from app.insights.service import InsightsService
from app.telegram.adapter import TelegramAdapter

logger = logging.getLogger(__name__)


class WeeklySummaryScheduler:
    """Background scheduler for weekly Telegram summaries."""

    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self._task: asyncio.Task | None = None
        self._running = False

    async def start(self) -> None:
        """Start the scheduler background task."""
        if self._running:
            return

        if not settings.TELEGRAM_WEEKLY_SUMMARY_ENABLED:
            logger.info("Weekly summary scheduler is disabled via config")
            return

        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info("Weekly summary scheduler started")

    async def stop(self) -> None:
        """Stop the scheduler background task."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Weekly summary scheduler stopped")

    async def _run_loop(self) -> None:
        """Main scheduler loop."""
        interval = settings.TELEGRAM_WEEKLY_SUMMARY_INTERVAL_SECONDS

        while self._running:
            try:
                await self._run_job()
            except Exception as e:
                logger.error(f"Error in weekly summary job: {e}", exc_info=True)

            # Sleep until next run
            await asyncio.sleep(interval)

    async def _run_job(self) -> None:
        """Execute the weekly summary job once."""
        # Initialize services
        user_repo = MongoUserRepository(self.db)
        summary_repo = MongoTelegramWeeklySummaryRepository(self.db)
        task_repo = TaskRepository(self.db)
        insights_service = InsightsService()
        telegram_adapter = TelegramAdapter()

        service = TelegramWeeklySummaryService(
            db=self.db,
            user_repo=user_repo,
            summary_repo=summary_repo,
            task_repo=task_repo,
            insights_service=insights_service,
            telegram_adapter=telegram_adapter,
        )

        await service.send_weekly_summaries_for_all_users()
