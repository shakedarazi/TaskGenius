"""
TASKGENIUS Core API - Test Configuration

Shared fixtures for CI-safe testing without MongoDB.
"""

import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Callable, Optional, Dict
from fastapi.testclient import TestClient
from fastapi.security import HTTPAuthorizationCredentials
from fastapi import Request

from unittest.mock import MagicMock

from app.main import app
from app.auth.repository import UserRepositoryInterface, User
from app.auth.service import AuthService
from app.auth.router import get_auth_service as get_auth_service_router
from app.auth.dependencies import get_auth_service as get_auth_service_deps, get_current_user, CurrentUser, bearer_scheme
from app.tasks.repository import InMemoryTaskRepository
from app.tasks.router import get_task_repository
from app.database import get_database


# Global in-memory repositories for tests
_test_repository = InMemoryTaskRepository()
_test_user_repository: Optional['InMemoryUserRepository'] = None
_test_auth_service: Optional[AuthService] = None


class InMemoryUserRepository(UserRepositoryInterface):
    """In-memory user repository for testing."""
    
    def __init__(self):
        self._users: Dict[str, User] = {}
        self._users_by_username: Dict[str, User] = {}
    
    async def create(self, user: User) -> User:
        """Create a new user."""
        self._users[user.id] = user
        self._users_by_username[user.username.lower()] = user
        return user
    
    async def get_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID."""
        return self._users.get(user_id)
    
    async def get_by_username(self, username: str) -> Optional[User]:
        """Get user by username (case-insensitive)."""
        return self._users_by_username.get(username.lower())
    
    async def exists_by_username(self, username: str) -> bool:
        """Check if username exists."""
        return username.lower() in self._users_by_username
    
    def clear(self) -> None:
        """Clear all users (synchronous helper for tests)."""
        self._users.clear()
        self._users_by_username.clear()
    
    def get_by_username_sync(self, username: str) -> Optional[User]:
        """Synchronous helper for tests that need direct access."""
        return asyncio.run(self.get_by_username(username))


# Initialize test user repository
_test_user_repository = InMemoryUserRepository()
_test_auth_service = AuthService(_test_user_repository)


async def override_get_auth_service(db=None):
    """Override dependency to use in-memory user repository.
    
    Signature must match get_auth_service from app.auth.router.
    Note: db parameter is ignored - we use in-memory repo for tests.
    """
    # Return test auth_service with in-memory repository
    # This bypasses MongoDB completely
    return _test_auth_service


async def override_get_current_user(
    request: Request,
):
    """Override get_current_user to use in-memory auth service.
    
    This override bypasses dependency resolution entirely by extracting the token
    directly from request headers, avoiding any MongoDB operations.
    
    Note: FastAPI will inject the Request object automatically via Depends.
    """
    from fastapi import HTTPException, status
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    if request is None:
        raise credentials_exception
    
    # Extract token directly from Authorization header
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise credentials_exception
    
    token = auth_header[7:]  # Remove "Bearer " prefix
    
    # Use test auth_service directly (no dependency resolution needed)
    user_id = _test_auth_service.decode_token(token)
    
    if user_id is None:
        raise credentials_exception
    
    # Get user from in-memory repository (async)
    user = await _test_auth_service.get_user_by_id(user_id)
    if user is None:
        raise credentials_exception
    
    return user


async def override_get_task_repository():
    """Override dependency to use in-memory repository."""
    return _test_repository


async def override_get_database():
    """Override database dependency (not used in tests, but required by some dependencies)."""
    # Return a mock database that satisfies AsyncIOMotorDatabase interface
    # ChatService doesn't actually use it - it only uses it to create InsightsService
    mock_db = MagicMock()
    # Make it async-compatible
    return mock_db


# Export test-only singletons for backward compatibility with tests
# These wrap the async repository with sync helpers
class UserRepositoryWrapper:
    """Test-only wrapper that provides sync access to async repository."""
    
    def clear(self) -> None:
        """Clear all users."""
        _test_user_repository.clear()
    
    def get_by_username(self, username: str) -> Optional[User]:
        """Get user by username (synchronous for test convenience)."""
        return _test_user_repository.get_by_username_sync(username)


user_repository = UserRepositoryWrapper()
auth_service = _test_auth_service


@pytest.fixture
def task_repository():
    """Provide a fresh in-memory task repository for each test."""
    _test_repository.clear()
    return _test_repository


@pytest.fixture
def client(task_repository):
    """Create test client with in-memory repository."""
    user_repository.clear()
    # Override the repository dependency
    app.dependency_overrides[get_task_repository] = override_get_task_repository
    # Override auth service dependency (both locations)
    app.dependency_overrides[get_auth_service_router] = override_get_auth_service
    app.dependency_overrides[get_auth_service_deps] = override_get_auth_service
    # Override get_current_user to use test auth_service
    # IMPORTANT: Must override the exact function object used by the route
    # This override bypasses dependency resolution by extracting token directly from request
    app.dependency_overrides[get_current_user] = override_get_current_user
    # Override database dependency (required by chat service)
    app.dependency_overrides[get_database] = override_get_database
    
    yield TestClient(app)
    # Clean up override after test
    app.dependency_overrides.clear()


@pytest.fixture
def registered_user(client):
    """Register a test user and return credentials."""
    credentials = {"username": "testuser", "password": "testpassword123"}
    client.post("/auth/register", json=credentials)
    return credentials


@pytest.fixture
def auth_token(client, registered_user):
    """Get an auth token for the registered user."""
    response = client.post("/auth/login", json=registered_user)
    return response.json()["access_token"]


@pytest.fixture
def auth_headers(auth_token):
    """Create Authorization headers for authenticated requests."""
    return {"Authorization": f"Bearer {auth_token}"}


@pytest.fixture
def second_user_credentials():
    """Credentials for a second test user."""
    return {"username": "seconduser", "password": "secondpassword123"}


@pytest.fixture
def second_user_token(client, second_user_credentials):
    """Register a second user and get their auth token."""
    client.post("/auth/register", json=second_user_credentials)
    response = client.post("/auth/login", json=second_user_credentials)
    return response.json()["access_token"]


@pytest.fixture
def second_auth_headers(second_user_token):
    """Authorization headers for the second user."""
    return {"Authorization": f"Bearer {second_user_token}"}


# Time control fixtures for deterministic urgency testing
class FrozenClock:
    """A clock that returns a fixed time for deterministic testing."""
    
    def __init__(self, frozen_time: datetime):
        self._frozen_time = frozen_time
    
    def __call__(self) -> datetime:
        return self._frozen_time
    
    def set(self, new_time: datetime) -> None:
        self._frozen_time = new_time
    
    def advance(self, delta: timedelta) -> None:
        self._frozen_time += delta


@pytest.fixture
def frozen_now() -> datetime:
    """A fixed 'now' time for testing."""
    return datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def frozen_clock(frozen_now) -> FrozenClock:
    """A controllable clock for urgency testing."""
    return FrozenClock(frozen_now)
