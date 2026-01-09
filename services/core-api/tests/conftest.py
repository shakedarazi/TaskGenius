"""
TASKGENIUS Core API - Test Configuration

Shared fixtures for CI-safe testing without MongoDB.
"""

import pytest
from datetime import datetime, timezone, timedelta
from typing import Callable
from fastapi.testclient import TestClient

from unittest.mock import MagicMock

from app.main import app
from app.auth.repository import user_repository
from app.tasks.repository import InMemoryTaskRepository
from app.tasks.router import get_task_repository
from app.database import get_database


# Global in-memory repository for tests
_test_repository = InMemoryTaskRepository()


async def override_get_task_repository():
    """Override dependency to use in-memory repository."""
    return _test_repository


async def override_get_database():
    """Override database dependency (not used in tests, but required by some dependencies)."""
    # Return a mock database - ChatService doesn't actually use it
    # It only uses it to create InsightsService which doesn't need it
    return MagicMock()


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
