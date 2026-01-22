import logging
from datetime import datetime, timedelta, timezone, date

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.auth.repository import MongoUserRepository
from app.telegram.weekly_repository import MongoTelegramWeeklySummaryRepository
from app.telegram.adapter import TelegramAdapter
from app.tasks.repository import TaskRepository
from app.insights.service import InsightsService
from app.insights.schemas import WeeklySummary

logger = logging.getLogger(__name__)


class TelegramWeeklySummaryService:
    def __init__(
        self,
        db: AsyncIOMotorDatabase,
        user_repo: MongoUserRepository,
        summary_repo: MongoTelegramWeeklySummaryRepository,
        task_repo: TaskRepository,
        insights_service: InsightsService,
        telegram_adapter: TelegramAdapter,
    ):
        self.db = db
        self.user_repo = user_repo
        self.summary_repo = summary_repo
        self.task_repo = task_repo
        self.insights_service = insights_service
        self.telegram_adapter = telegram_adapter

    def _get_week_start(self, dt: datetime) -> date:
        """Get Monday of the week for a given datetime (UTC)."""
        # Monday = 0, Sunday = 6
        days_since_monday = dt.weekday()
        monday = dt - timedelta(days=days_since_monday)
        return monday.date()

    def _format_summary_for_telegram(self, summary: WeeklySummary) -> str:
        """Format WeeklySummary as Telegram-friendly text."""
        lines = ["📊 *Your Weekly Task Summary*\n"]

        # Completed tasks
        if summary.completed.count > 0:
            lines.append(f"✅ *Completed*: {summary.completed.count} task(s)")
            for task in summary.completed.tasks[:5]:  # Limit to 5
                lines.append(f"  • {task.title}")
            if summary.completed.count > 5:
                lines.append(f"  ... and {summary.completed.count - 5} more")
            lines.append("")

        # High priority tasks
        if summary.high_priority.count > 0:
            lines.append(f"🔴 *High Priority*: {summary.high_priority.count} task(s)")
            for task in summary.high_priority.tasks[:5]:
                lines.append(f"  • {task.title}")
            if summary.high_priority.count > 5:
                lines.append(f"  ... and {summary.high_priority.count - 5} more")
            lines.append("")

        # Upcoming tasks
        if summary.upcoming.count > 0:
            lines.append(f"📅 *Upcoming* (next 7 days): {summary.upcoming.count} task(s)")
            for task in summary.upcoming.tasks[:5]:
                deadline_str = task.deadline.strftime("%Y-%m-%d") if task.deadline else "No deadline"
                lines.append(f"  • {task.title} ({deadline_str})")
            if summary.upcoming.count > 5:
                lines.append(f"  ... and {summary.upcoming.count - 5} more")
            lines.append("")

        # Overdue tasks
        if summary.overdue.count > 0:
            lines.append(f"⚠️ *Overdue*: {summary.overdue.count} task(s)")
            for task in summary.overdue.tasks[:5]:
                lines.append(f"  • {task.title}")
            if summary.overdue.count > 5:
                lines.append(f"  ... and {summary.overdue.count - 5} more")
            lines.append("")

        if len(lines) == 1:  # Only header
            lines.append("You have no tasks to report this week. Great job! 🎉")

        return "\n".join(lines)

    async def send_weekly_summaries_for_all_users(self) -> None:
        now = datetime.now(timezone.utc)
        week_start = self._get_week_start(now)

        try:
            # Get all users with notifications enabled
            users = await self.user_repo.list_users_with_notifications_enabled()
            logger.info(f"Weekly summary job: Found {len(users)} users with notifications enabled")

            for user in users:
                if not user.telegram:
                    continue  # Skip users without telegram linkage
                    
                try:
                    # Check idempotency
                    if await self.summary_repo.has_summary_sent(user.id, week_start):
                        logger.debug(f"Summary already sent for user {user.id}, week {week_start}")
                        continue

                    # Fetch user's tasks
                    tasks = await self.task_repo.list_by_owner(user.id)
                    logger.debug(f"Found {len(tasks)} tasks for user {user.id}")

                    # Generate summary
                    summary = self.insights_service.generate_weekly_summary(tasks, now)

                    # Format as Telegram message
                    message_text = self._format_summary_for_telegram(summary)

                    # Send via Telegram
                    response = await self.telegram_adapter.send_message(
                        chat_id=user.telegram.telegram_chat_id,
                        text=message_text,
                        parse_mode="Markdown",
                    )

                    if response.ok:
                        # Mark as sent only if send succeeded
                        await self.summary_repo.mark_summary_sent(user.id, week_start)
                        logger.info(f"Sent weekly summary to user {user.id} (chat {user.telegram.telegram_chat_id})")
                    else:
                        logger.warning(f"Failed to send weekly summary to user {user.id}: {response}")

                except Exception as e:
                    logger.error(f"Error sending weekly summary to user {user.id}: {e}", exc_info=True)
                    # Continue with next user

        except Exception as e:
            logger.error(f"Error in weekly summary job: {e}", exc_info=True)

    async def send_summary_for_user(self, user_id: str) -> tuple[bool, str]:
        try:
            # Get user
            user = await self.user_repo.get_by_id(user_id)
            if not user:
                return False, "User not found"
            
            if not user.telegram:
                return False, "Telegram account not linked"
            
            # Log warning if notifications are disabled (manual send still allowed)
            if not user.telegram.notifications_enabled:
                logger.info(f"Manual summary send for user {user_id} (notifications disabled - automatic summaries won't be sent)")
            
            # Fetch user's tasks
            tasks = await self.task_repo.list_by_owner(user_id)
            logger.debug(f"Found {len(tasks)} tasks for user {user_id}")
            
            # Generate summary
            now = datetime.now(timezone.utc)
            summary = self.insights_service.generate_weekly_summary(tasks, now)
            
            # Format as Telegram message
            message_text = self._format_summary_for_telegram(summary)
            
            # Send via Telegram
            response = await self.telegram_adapter.send_message(
                chat_id=user.telegram.telegram_chat_id,
                text=message_text,
                parse_mode="Markdown",
            )
            
            if response.ok:
                logger.info(f"Sent weekly summary to user {user_id} (chat {user.telegram.telegram_chat_id})")
                return True, "Summary sent successfully"
            else:
                logger.warning(f"Failed to send weekly summary to user {user_id}: {response}")
                return False, f"Failed to send: {response}"
                
        except Exception as e:
            logger.error(f"Error sending weekly summary to user {user_id}: {e}", exc_info=True)
            return False, f"Error: {str(e)}"
