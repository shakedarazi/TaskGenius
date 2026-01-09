"""
TASKGENIUS Chatbot Service - Test Configuration

Shared fixtures for CI-safe testing.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.service import ChatbotService


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def chatbot_service():
    """Create chatbot service instance."""
    return ChatbotService()
