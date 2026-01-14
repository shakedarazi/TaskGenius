"""
TASKGENIUS Core API - Telegram Service

Service for handling Telegram webhook events and user mapping.
"""

from typing import Optional
import asyncio
import re
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.telegram.adapter import TelegramAdapter
from app.telegram.repository import (
    UserTelegramLinkRepositoryInterface,
    TelegramVerificationRepositoryInterface,
    TelegramUpdateRepositoryInterface,
)
from app.telegram.schemas import TelegramUpdate, TelegramMessage
from app.chat.service import ChatService
from app.tasks.repository import TaskRepositoryInterface
from app.chat.schemas import ChatResponse


class TelegramService:
    """
    Service for Telegram integration.
    
    Responsibilities:
    - Process Telegram webhook updates
    - Map Telegram user IDs to application user IDs
    - Route messages through chat flow
    - Send responses back to Telegram
    """

    def __init__(
        self,
        db: AsyncIOMotorDatabase,
        link_repository: Optional[UserTelegramLinkRepositoryInterface] = None,
        verification_repository: Optional[TelegramVerificationRepositoryInterface] = None,
        update_repository: Optional[TelegramUpdateRepositoryInterface] = None,
    ):
        self.db = db
        self.telegram_adapter = TelegramAdapter()
        self.chat_service = ChatService(db)
        self.link_repository = link_repository
        self.verification_repository = verification_repository
        self.update_repository = update_repository
        # Keep in-memory fallback for backward compatibility
        self._user_mappings: dict[int, str] = {}

    async def process_webhook_update(
        self,
        update: TelegramUpdate,
        task_repository: TaskRepositoryInterface,
    ) -> None:
        """
        Process a Telegram webhook update.
        
        This method:
        0. Checks idempotency (skip if already processed)
        1. Extracts message from update
        2. Handles verification codes OR maps Telegram user to application user
        3. Routes message through chat flow
        4. Sends response back to Telegram
        
        Args:
            update: Telegram webhook update
            task_repository: Task repository for chat flow
        """
        # Idempotency check: skip if this update_id was already processed
        if self.update_repository:
            try:
                if await self.update_repository.is_processed(update.update_id):
                    return  # Already processed, skip silently
            except Exception:
                # If DB check fails, continue (don't break webhook)
                pass

        if not update.message or not update.message.text:
            # Ignore non-text messages
            return

        telegram_user_id = update.message.from_user.id
        message_text = update.message.text
        chat_id = update.message.chat.get("id")
        telegram_username = update.message.from_user.username

        # Check if message is a verification code
        if self._looks_like_verification_code(message_text):
            await self._handle_verification_code(
                code=message_text.strip(),
                telegram_user_id=telegram_user_id,
                telegram_chat_id=chat_id,
                telegram_username=telegram_username,
            )
            return  # Don't process as chat message

        # Map Telegram user to application user
        app_user_id = await self._get_or_create_user_mapping(telegram_user_id)

        if not app_user_id:
            # If we can't map the user, send a helpful message
            await self.telegram_adapter.send_message(
                chat_id=chat_id,
                text="Please register in the web application first to use Telegram integration. To link your account, generate a verification code in the web app and send it here.",
            )
            return

        # Mark update as processed (idempotency)
        if self.update_repository:
            try:
                await self.update_repository.mark_processed(update.update_id, telegram_user_id)
            except Exception:
                # If marking fails, continue (don't break webhook)
                pass

        # Route through existing chat flow
        chat_response = await self.chat_service.process_message(
            user_id=app_user_id,
            message=message_text,
            task_repository=task_repository,
        )

        # Send response back to Telegram
        await self.telegram_adapter.send_message(
            chat_id=chat_id,
            text=chat_response.reply,
        )

    def _looks_like_verification_code(self, text: str) -> bool:
        """Check if message text looks like a verification code (6-8 alphanumeric chars)."""
        if not text:
            return False
        stripped = text.strip()
        # Match 6-8 alphanumeric characters
        return bool(re.match(r'^[A-Za-z0-9]{6,8}$', stripped))

    async def _handle_verification_code(
        self,
        code: str,
        telegram_user_id: int,
        telegram_chat_id: int,
        telegram_username: Optional[str],
    ) -> None:
        """Handle verification code sent by user to link Telegram account."""
        if not self.verification_repository:
            await self.telegram_adapter.send_message(
                chat_id=telegram_chat_id,
                text="Verification is not available. Please contact support.",
            )
            return

        try:
            # Find valid verification code
            verification = await self.verification_repository.get_valid_code(code)
            if not verification:
                await self.telegram_adapter.send_message(
                    chat_id=telegram_chat_id,
                    text="Invalid or expired verification code. Please generate a new code in the web application.",
                )
                return

            # Create or update user-telegram link
            if not self.link_repository:
                await self.telegram_adapter.send_message(
                    chat_id=telegram_chat_id,
                    text="Account linking is not available. Please contact support.",
                )
                return

            link = await self.link_repository.upsert_link(
                user_id=verification.user_id,
                telegram_user_id=telegram_user_id,
                telegram_chat_id=telegram_chat_id,
                telegram_username=telegram_username,
            )

            # Mark code as used
            await self.verification_repository.mark_used(verification.id)

            await self.telegram_adapter.send_message(
                chat_id=telegram_chat_id,
                text="✅ Account linked successfully! You can now use Telegram to manage your tasks. Send /help to see available commands.",
            )
        except Exception as e:
            # Log error but send user-friendly message
            await self.telegram_adapter.send_message(
                chat_id=telegram_chat_id,
                text="An error occurred while linking your account. Please try again or contact support.",
            )

    async def _get_or_create_user_mapping(self, telegram_user_id: int) -> Optional[str]:
        """
        Get mapping between Telegram user ID and application user ID.
        
        First tries MongoDB repository, falls back to in-memory mapping for backward compatibility.
        
        Args:
            telegram_user_id: Telegram user ID
        
        Returns:
            Application user ID if mapping exists, None otherwise
        """
        # Try MongoDB repository first
        if self.link_repository:
            try:
                link = await self.link_repository.get_by_telegram_user_id(telegram_user_id)
                if link:
                    return link.user_id
            except Exception:
                # If DB query fails, fall back to in-memory
                pass
        
        # Fallback to in-memory mapping (backward compatibility)
        return self._user_mappings.get(telegram_user_id)
    
    def set_user_mapping(self, telegram_user_id: int, app_user_id: str) -> None:
        """
        Set mapping between Telegram user ID and application user ID.
        
        This is a helper method for testing. In production, use verification flow.
        Also updates in-memory fallback for backward compatibility.
        
        Args:
            telegram_user_id: Telegram user ID
            app_user_id: Application user ID
        """
        self._user_mappings[telegram_user_id] = app_user_id
        # Also try to persist to MongoDB if repository is available
        if self.link_repository:
            try:
                # Note: This doesn't have chat_id/username, but preserves backward compatibility
                # In production, users should use verification flow instead
                asyncio.create_task(
                    self.link_repository.upsert_link(
                        user_id=app_user_id,
                        telegram_user_id=telegram_user_id,
                        telegram_chat_id=0,  # Unknown, will be updated on next webhook
                        telegram_username=None,
                    )
                )
            except Exception:
                pass  # Silent failure for backward compatibility