from abc import ABC, abstractmethod
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorDatabase
from app.auth.models import User

class UserRepositoryInterface(ABC):
    """Abstract interface for user repository.
    
    This interface allows swapping implementations (in-memory -> MongoDB).
    """

    @abstractmethod
    async def create(self, user: User) -> User:
        """Create a new user."""
        pass

    @abstractmethod
    async def get_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID."""
        pass

    @abstractmethod
    async def get_by_username(self, username: str) -> Optional[User]:
        """Get user by username."""
        pass

    @abstractmethod
    async def exists_by_username(self, username: str) -> bool:
        """Check if username exists."""
        pass


class MongoUserRepository(UserRepositoryInterface):
    """MongoDB implementation of the user repository."""

    COLLECTION_NAME = "users"

    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.collection = db[self.COLLECTION_NAME]

    async def create(self, user: User) -> User:
        """Create a new user."""
        import logging
        logger = logging.getLogger(__name__)
        try:
            user_dict = user.to_dict()
            logger.info(f"[MongoUserRepository] Creating user in MongoDB: username={user.username}, id={user.id}")
            result = await self.collection.insert_one(user_dict)
            logger.info(f"[MongoUserRepository] User created successfully with _id: {result.inserted_id}")
            # Verify it was actually inserted
            verify = await self.collection.find_one({"_id": user.id})
            if verify:
                logger.info(f"[MongoUserRepository] Verification: User found in DB after insert")
            else:
                logger.error(f"[MongoUserRepository] Verification FAILED: User NOT found in DB after insert!")
            return user
        except Exception as e:
            logger.error(f"[MongoUserRepository] Error creating user in MongoDB: {e}", exc_info=True)
            raise

    async def get_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID."""
        doc = await self.collection.find_one({"_id": user_id})
        if doc is None:
            return None
        return User.from_dict(doc)

    async def get_by_username(self, username: str) -> Optional[User]:
        """Get user by username (case-insensitive)."""
        doc = await self.collection.find_one({"username": {"$regex": f"^{username}$", "$options": "i"}})
        if doc is None:
            return None
        return User.from_dict(doc)

    async def exists_by_username(self, username: str) -> bool:
        """Check if username exists (case-insensitive)."""
        doc = await self.collection.find_one({"username": {"$regex": f"^{username}$", "$options": "i"}})
        return doc is not None

    async def update(self, user: User) -> User:
        """Update user document in MongoDB."""
        await self.collection.replace_one({"_id": user.id}, user.to_dict())
        return user

    async def update_telegram_link(
        self,
        user_id: str,
        telegram_user_id: int,
        telegram_chat_id: int,
        telegram_username: Optional[str],
        notifications_enabled: bool = False,
    ) -> Optional[User]:
        """Update or set Telegram linkage for a user."""
        from datetime import datetime, timezone
        from app.auth.models import TelegramLink

        telegram = TelegramLink(
            telegram_user_id=telegram_user_id,
            telegram_chat_id=telegram_chat_id,
            telegram_username=telegram_username,
            notifications_enabled=notifications_enabled,
            linked_at=datetime.now(timezone.utc),
        )

        await self.collection.update_one(
            {"_id": user_id},
            {"$set": {"telegram": {
                "telegram_user_id": telegram.telegram_user_id,
                "telegram_chat_id": telegram.telegram_chat_id,
                "telegram_username": telegram.telegram_username,
                "notifications_enabled": telegram.notifications_enabled,
                "linked_at": telegram.linked_at,
            }}},
        )

        return await self.get_by_id(user_id)

    async def remove_telegram_link(self, user_id: str) -> None:
        """Remove Telegram linkage from a user."""
        await self.collection.update_one(
            {"_id": user_id},
            {"$unset": {"telegram": ""}},
        )

    async def set_notifications_enabled(self, user_id: str, enabled: bool) -> Optional[User]:
        """Toggle Telegram notifications for a user. Only updates if telegram link exists."""
        # Only update if telegram field exists
        result = await self.collection.find_one_and_update(
            {"_id": user_id, "telegram": {"$exists": True}},
            {"$set": {"telegram.notifications_enabled": enabled}},
            return_document=True,
        )
        return User.from_dict(result) if result else None

    async def get_by_telegram_user_id(self, telegram_user_id: int) -> Optional[User]:
        """Get user by Telegram user ID."""
        doc = await self.collection.find_one({"telegram.telegram_user_id": telegram_user_id})
        if doc is None:
            return None
        return User.from_dict(doc)

    async def list_users_with_notifications_enabled(self) -> list[User]:
        """List all users who have Telegram notifications enabled."""
        cursor = self.collection.find({
            "telegram.notifications_enabled": True,
            "telegram.telegram_chat_id": {"$exists": True, "$ne": None},
        })
        users = []
        async for doc in cursor:
            users.append(User.from_dict(doc))
        return users
