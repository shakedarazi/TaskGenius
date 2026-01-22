
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.telegram.models import (
    UserTelegramLink,
    TelegramVerificationCode,
    ProcessedTelegramUpdate,
)


class UserTelegramLinkRepositoryInterface(ABC):
    @abstractmethod
    async def get_by_telegram_user_id(self, telegram_user_id: int) -> Optional[UserTelegramLink]:
        pass

    @abstractmethod
    async def get_by_user_id(self, user_id: str) -> Optional[UserTelegramLink]:
        pass

    @abstractmethod
    async def upsert_link(
        self,
        user_id: str,
        telegram_user_id: int,
        telegram_chat_id: int,
        telegram_username: Optional[str],
    ) -> UserTelegramLink:
        pass

    @abstractmethod
    async def delete_for_user(self, user_id: str) -> None:
        pass

    @abstractmethod
    async def set_notifications_enabled(self, user_id: str, enabled: bool) -> None:
        pass


class MongoUserTelegramLinkRepository(UserTelegramLinkRepositoryInterface):
    COLLECTION_NAME = "user_telegram_links"

    def __init__(self, db: AsyncIOMotorDatabase):
        self.collection = db[self.COLLECTION_NAME]

    @staticmethod
    def _from_doc(doc: dict) -> UserTelegramLink:
        return UserTelegramLink(
            id=str(doc["_id"]),
            user_id=doc["user_id"],
            telegram_user_id=doc["telegram_user_id"],
            telegram_chat_id=doc["telegram_chat_id"],
            telegram_username=doc.get("telegram_username"),
            notifications_enabled=doc.get("notifications_enabled", False),
            connected_at=doc["connected_at"],
        )

    async def get_by_telegram_user_id(self, telegram_user_id: int) -> Optional[UserTelegramLink]:
        doc = await self.collection.find_one({"telegram_user_id": telegram_user_id})
        return self._from_doc(doc) if doc else None

    async def get_by_user_id(self, user_id: str) -> Optional[UserTelegramLink]:
        doc = await self.collection.find_one({"user_id": user_id})
        return self._from_doc(doc) if doc else None

    async def upsert_link(
        self,
        user_id: str,
        telegram_user_id: int,
        telegram_chat_id: int,
        telegram_username: Optional[str],
    ) -> UserTelegramLink:
        now = datetime.now(timezone.utc)
        update = {
            "user_id": user_id,
            "telegram_user_id": telegram_user_id,
            "telegram_chat_id": telegram_chat_id,
            "telegram_username": telegram_username,
            "connected_at": now,
        }

        result = await self.collection.find_one_and_update(
            {"user_id": user_id},
            {"$set": update, "$setOnInsert": {"notifications_enabled": False}},
            upsert=True,
            return_document=True,
        )
        if result is None:
            result = await self.collection.find_one({"user_id": user_id})
        return self._from_doc(result)

    async def delete_for_user(self, user_id: str) -> None:
        await self.collection.delete_many({"user_id": user_id})

    async def set_notifications_enabled(self, user_id: str, enabled: bool) -> None:
        await self.collection.update_many(
            {"user_id": user_id},
            {"$set": {"notifications_enabled": enabled}},
        )


class TelegramVerificationRepositoryInterface(ABC):
    @abstractmethod
    async def create_code(
        self,
        user_id: str,
        code: str,
        expires_at: datetime,
    ) -> TelegramVerificationCode:
        pass

    @abstractmethod
    async def get_valid_code(self, code: str) -> Optional[TelegramVerificationCode]:
        pass

    @abstractmethod
    async def mark_used(self, code_id: str) -> None:
        pass


class MongoTelegramVerificationRepository(TelegramVerificationRepositoryInterface):
    COLLECTION_NAME = "telegram_verification_codes"

    def __init__(self, db: AsyncIOMotorDatabase):
        self.collection = db[self.COLLECTION_NAME]

    @staticmethod
    def _from_doc(doc: dict) -> TelegramVerificationCode:
        return TelegramVerificationCode(
            id=str(doc["_id"]),
            user_id=doc["user_id"],
            code=doc["code"],
            created_at=doc["created_at"],
            expires_at=doc["expires_at"],
            used_at=doc.get("used_at"),
        )

    async def create_code(
        self,
        user_id: str,
        code: str,
        expires_at: datetime,
    ) -> TelegramVerificationCode:
        doc = {
            "user_id": user_id,
            "code": code,
            "created_at": datetime.now(timezone.utc),
            "expires_at": expires_at,
            "used_at": None,
        }
        result = await self.collection.insert_one(doc)
        doc["_id"] = result.inserted_id
        return self._from_doc(doc)

    async def get_valid_code(self, code: str) -> Optional[TelegramVerificationCode]:
        now = datetime.now(timezone.utc)
        doc = await self.collection.find_one(
            {
                "code": code,
                "used_at": None,
                "expires_at": {"$gt": now},
            }
        )
        return self._from_doc(doc) if doc else None

    async def mark_used(self, code_id: str) -> None:
        await self.collection.update_one(
            {"_id": code_id},
            {"$set": {"used_at": datetime.now(timezone.utc)}},
        )


class TelegramUpdateRepositoryInterface(ABC):
    @abstractmethod
    async def is_processed(self, update_id: int) -> bool:
        pass

    @abstractmethod
    async def mark_processed(self, update_id: int, telegram_user_id: int) -> None:
        pass


class MongoTelegramUpdateRepository(TelegramUpdateRepositoryInterface):
    COLLECTION_NAME = "telegram_processed_updates"

    def __init__(self, db: AsyncIOMotorDatabase):
        self.collection = db[self.COLLECTION_NAME]

    async def is_processed(self, update_id: int) -> bool:
        doc = await self.collection.find_one({"update_id": update_id})
        return doc is not None

    async def mark_processed(self, update_id: int, telegram_user_id: int) -> None:
        record = ProcessedTelegramUpdate.create(update_id=update_id, telegram_user_id=telegram_user_id)
        await self.collection.insert_one(
            {
                "_id": record.id,
                "update_id": record.update_id,
                "telegram_user_id": record.telegram_user_id,
                "first_seen_at": record.first_seen_at,
            }
        )

