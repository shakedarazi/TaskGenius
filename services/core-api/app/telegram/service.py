"""
Telegram Service - Minimal command-based interface.

Supported commands:
- /help - Show available commands
- /add <title> - Add a new task
- /urgent - List high-priority tasks
- /soon - List tasks due within 3 days

This service is stateless and deterministic. It does NOT use AI/LLM.
"""

from typing import Optional, List
import re
import logging
from datetime import datetime, timedelta, timezone
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.telegram.adapter import TelegramAdapter
from app.telegram.repository import (
    TelegramVerificationRepositoryInterface,
    TelegramUpdateRepositoryInterface,
)
from app.auth.repository import MongoUserRepository
from app.telegram.schemas import TelegramUpdate
from app.tasks.repository import TaskRepositoryInterface
from app.tasks.models import Task
from app.tasks.enums import TaskStatus, TaskPriority

logger = logging.getLogger(__name__)

# Static help message
HELP_MESSAGE = """🤖 TaskGenius Bot

Priorities:
🔴 (urgent) 🟣 (high) 🟠 (medium)


Commands:
/add <title> — Add a new task
/urgent — List high-priority tasks
/soon — List tasks due within 3 days
/help — Show this message

Example: /add Buy groceries"""

LINK_REQUIRED_MESSAGE = """Please link your Telegram account first.

1. Log in to the TaskGenius web app
2. Go to Settings → Telegram
3. Generate a verification code
4. Send the code here"""


class TelegramService:
    """Minimal, stateless Telegram command handler."""

    def __init__(
        self,
        db: AsyncIOMotorDatabase,
        user_repository: Optional[MongoUserRepository] = None,
        verification_repository: Optional[TelegramVerificationRepositoryInterface] = None,
        update_repository: Optional[TelegramUpdateRepositoryInterface] = None,
    ):
        self.db = db
        self.telegram_adapter = TelegramAdapter()
        self.user_repository = user_repository
        self.verification_repository = verification_repository
        self.update_repository = update_repository

    async def process_webhook_update(
        self,
        update: TelegramUpdate,
        task_repository: TaskRepositoryInterface,
    ) -> None:
        """Process incoming Telegram update."""
        
        # Idempotency check: skip if already processed
        if self.update_repository:
            try:
                if await self.update_repository.is_processed(update.update_id):
                    return
            except Exception:
                pass  # Don't break webhook on DB errors

        if not update.message or not update.message.text:
            return  # Ignore non-text messages

        telegram_user_id = update.message.from_user.id
        message_text = update.message.text.strip()
        chat_id = update.message.chat.get("id")
        telegram_username = update.message.from_user.username

        # Check if message is a verification code (6-8 alphanumeric)
        if self._looks_like_verification_code(message_text):
            await self._handle_verification_code(
                code=message_text,
                telegram_user_id=telegram_user_id,
                telegram_chat_id=chat_id,
                telegram_username=telegram_username,
            )
            return

        # Get linked app user
        app_user_id = await self._get_user_id(telegram_user_id)
        
        if not app_user_id:
            await self.telegram_adapter.send_message(
                chat_id=chat_id,
                text=LINK_REQUIRED_MESSAGE,
            )
            return

        # Mark as processed (idempotency)
        if self.update_repository:
            try:
                await self.update_repository.mark_processed(update.update_id, telegram_user_id)
            except Exception:
                pass

        # Route command
        await self._handle_command(
            text=message_text,
            user_id=app_user_id,
            chat_id=chat_id,
            task_repository=task_repository,
        )

    async def _handle_command(
        self,
        text: str,
        user_id: str,
        chat_id: int,
        task_repository: TaskRepositoryInterface,
    ) -> None:
        """Route command to appropriate handler."""
        
        if text == "/help" or text == "/start":
            await self.telegram_adapter.send_message(chat_id=chat_id, text=HELP_MESSAGE)
        
        elif text.startswith("/add "):
            title = text[5:].strip()
            if title:
                reply = await self._cmd_add(title, user_id, task_repository)
            else:
                reply = "Usage: /add <task title>\n\nExample: /add Buy groceries"
            await self.telegram_adapter.send_message(chat_id=chat_id, text=reply)
        
        elif text == "/add":
            await self.telegram_adapter.send_message(
                chat_id=chat_id,
                text="Usage: /add <task title>\n\nExample: /add Buy groceries",
            )
        
        elif text == "/urgent":
            reply = await self._cmd_urgent(user_id, task_repository)
            await self.telegram_adapter.send_message(chat_id=chat_id, text=reply)
        
        elif text == "/soon":
            reply = await self._cmd_soon(user_id, task_repository)
            await self.telegram_adapter.send_message(chat_id=chat_id, text=reply)
        
        else:
            # Unknown command → show help
            await self.telegram_adapter.send_message(chat_id=chat_id, text=HELP_MESSAGE)

    async def _cmd_add(
        self,
        title: str,
        user_id: str,
        task_repository: TaskRepositoryInterface,
    ) -> str:
        """Create a new task with default priority."""
        try:
            task = Task.create(
                owner_id=user_id,
                title=title,
                status=TaskStatus.OPEN,
                priority=TaskPriority.MEDIUM,
            )
            await task_repository.create(task)
            return (f"✅ Added: {task.title}\n"
                    f"🌐 Manage task details → Web ")
        except Exception as e:
            logger.error(f"Failed to create task: {e}")
            return "❌ Failed to add task. Please try again."

    async def _cmd_urgent(
        self,
        user_id: str,
        task_repository: TaskRepositoryInterface,
    ) -> str:
        """List tasks with high or urgent priority."""
        try:
            tasks = await task_repository.list_by_owner(
                owner_id=user_id,
                exclude_statuses=[TaskStatus.DONE, TaskStatus.CANCELED],
            )
            urgent_tasks = [
                t for t in tasks
                if t.priority in (TaskPriority.HIGH, TaskPriority.URGENT)
            ]
            return self._format_task_list(urgent_tasks, "⚡ Urgent tasks")
        except Exception as e:
            logger.error(f"Failed to list urgent tasks: {e}")
            return "❌ Failed to fetch tasks. Please try again."

    async def _cmd_soon(
        self,
        user_id: str,
        task_repository: TaskRepositoryInterface,
    ) -> str:
        """List tasks with deadline within 3 days."""
        try:
            now = datetime.now(timezone.utc)
            deadline_cutoff = now + timedelta(days=3)
            
            tasks = await task_repository.list_by_owner(
                owner_id=user_id,
                deadline_before=deadline_cutoff,
                exclude_statuses=[TaskStatus.DONE, TaskStatus.CANCELED],
            )
            # Filter to only tasks that actually have a deadline
            tasks_with_deadline = [t for t in tasks if t.deadline is not None]
            return self._format_task_list(tasks_with_deadline, "📅 Due soon (within 3 days)")
        except Exception as e:
            logger.error(f"Failed to list soon tasks: {e}")
            return "❌ Failed to fetch tasks. Please try again."

    def _format_task_list(self, tasks: List[Task], title: str) -> str:
        """Format task list for Telegram display."""
        if not tasks:
            return f"{title}\n\nNo tasks found."
        
        lines = [title, ""]
        for i, task in enumerate(tasks[:10], 1):  # Limit to 10
            # Priority colors: Urgent=Red, High=purple, Medium=Orange
            priority_icon = {
                TaskPriority.URGENT: "🔴",
                TaskPriority.HIGH: "🟣",
                TaskPriority.MEDIUM: "🟠",
            }.get(task.priority, "")
            lines.append(f"{i}. {task.title}{priority_icon}")
        
        return "\n".join(lines)

    def _looks_like_verification_code(self, text: str) -> bool:
        """Check if text looks like a verification code (6-8 alphanumeric)."""
        if not text:
            return False
        return bool(re.match(r'^[A-Za-z0-9]{6,8}$', text))

    async def _handle_verification_code(
        self,
        code: str,
        telegram_user_id: int,
        telegram_chat_id: int,
        telegram_username: Optional[str],
    ) -> None:
        """Handle verification code for account linking."""
        if not self.verification_repository:
            await self.telegram_adapter.send_message(
                chat_id=telegram_chat_id,
                text="Verification is not available. Please contact support.",
            )
            return

        try:
            verification = await self.verification_repository.get_valid_code(code)
            if not verification:
                await self.telegram_adapter.send_message(
                    chat_id=telegram_chat_id,
                    text="Invalid or expired code. Please generate a new one in the web app.",
                )
                return

            if not self.user_repository:
                await self.telegram_adapter.send_message(
                    chat_id=telegram_chat_id,
                    text="Account linking is not available. Please contact support.",
                )
                return

            await self.user_repository.update_telegram_link(
                user_id=verification.user_id,
                telegram_user_id=telegram_user_id,
                telegram_chat_id=telegram_chat_id,
                telegram_username=telegram_username,
                notifications_enabled=False,
            )

            await self.verification_repository.mark_used(verification.id)

            await self.telegram_adapter.send_message(
                chat_id=telegram_chat_id,
                text="✅ Account linked successfully!\n\nSend /help to see available commands.",
            )
        except Exception as e:
            logger.error(f"Verification error: {e}")
            await self.telegram_adapter.send_message(
                chat_id=telegram_chat_id,
                text="An error occurred. Please try again.",
            )

    async def _get_user_id(self, telegram_user_id: int) -> Optional[str]:
        """Get app user ID from Telegram user ID (DB lookup only)."""
        if not self.user_repository:
            return None
        try:
            user = await self.user_repository.get_by_telegram_user_id(telegram_user_id)
            if user and user.telegram:
                return user.id
        except Exception as e:
            logger.error(f"User lookup error: {e}")
        return None
