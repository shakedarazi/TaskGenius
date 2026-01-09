"""
TASKGENIUS Core API - Telegram Service

Service for handling Telegram webhook events and user mapping.
"""

from typing import Optional
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.telegram.adapter import TelegramAdapter
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

    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.telegram_adapter = TelegramAdapter()
        self.chat_service = ChatService(db)

    async def process_webhook_update(
        self,
        update: TelegramUpdate,
        task_repository: TaskRepositoryInterface,
    ) -> None:
        """
        Process a Telegram webhook update.
        
        This method:
        1. Extracts message from update
        2. Maps Telegram user to application user
        3. Routes message through chat flow
        4. Sends response back to Telegram
        
        Args:
            update: Telegram webhook update
            task_repository: Task repository for chat flow
        """
        if not update.message or not update.message.text:
            # Ignore non-text messages
            return

        telegram_user_id = update.message.from_user.id
        message_text = update.message.text
        chat_id = update.message.chat.get("id")

        # Map Telegram user to application user
        # For Phase 5, we use a simple mapping: store Telegram user ID -> app user ID
        # In production, this would be stored in MongoDB with proper user linking
        app_user_id = await self._get_or_create_user_mapping(telegram_user_id)

        if not app_user_id:
            # If we can't map the user, send a helpful message
            await self.telegram_adapter.send_message(
                chat_id=chat_id,
                text="Please register in the web application first to use Telegram integration.",
            )
            return

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

    async def _get_or_create_user_mapping(self, telegram_user_id: int) -> Optional[str]:
        """
        Get or create mapping between Telegram user ID and application user ID.
        
        For Phase 5, this uses an in-memory mapping that can be extended to MongoDB.
        In production, this would:
        - Check MongoDB for existing mapping
        - Create mapping if user provides their app username/ID
        - Handle user linking flow
        
        Args:
            telegram_user_id: Telegram user ID
        
        Returns:
            Application user ID if mapping exists, None otherwise
        """
        # Phase 5: In-memory mapping (can be extended to MongoDB in future phases)
        # For now, we check if a mapping exists in a simple in-memory store
        # In a real implementation, this would query MongoDB for user_telegram_mappings collection
        
        # Check in-memory mapping (for Phase 5)
        # This would be replaced with MongoDB query in production
        mapping = getattr(self, '_user_mappings', {}).get(telegram_user_id)
        return mapping
    
    def set_user_mapping(self, telegram_user_id: int, app_user_id: str) -> None:
        """
        Set mapping between Telegram user ID and application user ID.
        
        This is a helper method for testing and future user linking flow.
        
        Args:
            telegram_user_id: Telegram user ID
            app_user_id: Application user ID
        """
        if not hasattr(self, '_user_mappings'):
            self._user_mappings = {}
        self._user_mappings[telegram_user_id] = app_user_id
