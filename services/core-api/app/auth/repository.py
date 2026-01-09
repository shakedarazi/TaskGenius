"""
TASKGENIUS Core API - User Repository

Phase 1: In-memory user repository.
Phase 2 will replace with MongoDB implementation.
"""

from abc import ABC, abstractmethod
from typing import Optional

from app.auth.models import User


class UserRepositoryInterface(ABC):
    """Abstract interface for user repository.
    
    This interface allows swapping implementations (in-memory -> MongoDB).
    """

    @abstractmethod
    def create(self, user: User) -> User:
        """Create a new user."""
        pass

    @abstractmethod
    def get_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID."""
        pass

    @abstractmethod
    def get_by_username(self, username: str) -> Optional[User]:
        """Get user by username."""
        pass

    @abstractmethod
    def exists_by_username(self, username: str) -> bool:
        """Check if username exists."""
        pass


class InMemoryUserRepository(UserRepositoryInterface):
    """In-memory user repository for Phase 1.
    
    Thread-safe for single-process use.
    Will be replaced by MongoDB repository in Phase 2.
    """

    def __init__(self):
        self._users_by_id: dict[str, User] = {}
        self._users_by_username: dict[str, User] = {}

    def create(self, user: User) -> User:
        """Create a new user."""
        self._users_by_id[user.id] = user
        self._users_by_username[user.username.lower()] = user
        return user

    def get_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID."""
        return self._users_by_id.get(user_id)

    def get_by_username(self, username: str) -> Optional[User]:
        """Get user by username (case-insensitive)."""
        return self._users_by_username.get(username.lower())

    def exists_by_username(self, username: str) -> bool:
        """Check if username exists (case-insensitive)."""
        return username.lower() in self._users_by_username

    def clear(self) -> None:
        """Clear all users (for testing only)."""
        self._users_by_id.clear()
        self._users_by_username.clear()


# Singleton instance for the application
# This will be replaced with dependency injection in Phase 2
user_repository = InMemoryUserRepository()
