"""
Telegram Poller - Long-polling mode for development.

This module provides a background task that polls Telegram for updates
instead of receiving them via webhook. This is useful for local development
where a public HTTPS URL is not available.
"""

import asyncio
import logging
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.config import settings
from app.telegram.adapter import TelegramAdapter
from app.telegram.schemas import TelegramUpdate
# REUSE EXISTING FACTORIES - guarantees identical behavior with webhook
from app.telegram.router import get_telegram_service
from app.tasks.router import get_task_repository

logger = logging.getLogger(__name__)


class TelegramPoller:
    """Background poller for Telegram updates (development mode)."""

    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self._task: asyncio.Task | None = None
        self._running = False
        self._offset = 0

    async def start(self) -> None:
        """Start the polling background task."""
        if self._running:
            logger.info("Telegram poller already running")
            return

        if not settings.TELEGRAM_BOT_TOKEN:
            logger.info("Telegram poller skipped (no TELEGRAM_BOT_TOKEN)")
            return

        # Clear any existing webhook and pending updates
        adapter = TelegramAdapter()
        await adapter.delete_webhook(drop_pending_updates=True)

        self._running = True
        self._task = asyncio.create_task(self._poll_loop())
        logger.info("Telegram poller started")

    async def stop(self) -> None:
        """Stop the polling background task."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Telegram poller stopped")

    async def _poll_loop(self) -> None:
        """Main polling loop."""
        adapter = TelegramAdapter()

        while self._running:
            try:
                updates = await adapter.get_updates(offset=self._offset, timeout=30)
                for raw in updates:
                    try:
                        update = TelegramUpdate(**raw)
                        await self._process_update(update)
                        self._offset = update.update_id + 1
                    except Exception as e:
                        logger.error("Error processing update %s: %s", raw.get("update_id"), e)
                        # Still advance offset to avoid getting stuck
                        if "update_id" in raw:
                            self._offset = raw["update_id"] + 1
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.error("Polling error: %s", e)
                await asyncio.sleep(5)

    async def _process_update(self, update: TelegramUpdate) -> None:
        """Process a single update using the same factories as webhook route."""
        # USE SAME FACTORIES AS WEBHOOK ROUTE - guarantees identical behavior
        service = await get_telegram_service(self.db)
        task_repo = await get_task_repository(self.db)
        await service.process_webhook_update(update, task_repo)
