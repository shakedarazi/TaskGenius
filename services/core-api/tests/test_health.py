"""
TASKGENIUS Core API - Health Endpoint Tests
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.config import settings


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


class TestHealthEndpoint:
    """Tests for the health check endpoint."""

    def test_health_returns_200(self, client):
        """Health endpoint should return 200 OK."""
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_returns_healthy_status(self, client):
        """Health endpoint should indicate healthy status."""
        response = client.get("/health")
        data = response.json()
        assert data["status"] == "healthy"

    def test_health_includes_service_info(self, client):
        """Health endpoint should include service name and version."""
        response = client.get("/health")
        data = response.json()
        assert data["service"] == settings.APP_NAME
        assert data["version"] == settings.APP_VERSION


class TestRootEndpoint:
    """Tests for the root endpoint."""

    def test_root_returns_200(self, client):
        """Root endpoint should return 200 OK."""
        response = client.get("/")
        assert response.status_code == 200

    def test_root_includes_service_info(self, client):
        """Root endpoint should include service information."""
        response = client.get("/")
        data = response.json()
        assert "service" in data
        assert "version" in data
