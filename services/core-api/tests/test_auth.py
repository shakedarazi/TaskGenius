"""
TASKGENIUS Core API - Authentication Tests

Phase 1: Tests for register, login, and protected routes.
"""

import time
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from app.main import app
# Import test-only singletons from conftest (these use DI overrides)
from tests.conftest import user_repository, auth_service


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


class TestRegister:
    """Tests for POST /auth/register."""

    def test_register_success(self, client):
        """Successful registration should return 201."""
        response = client.post(
            "/auth/register",
            json={"username": "newuser", "password": "securepassword123"},
        )
        assert response.status_code == 201
        assert response.json()["message"] == "User registered successfully"

    def test_register_duplicate_username(self, client, registered_user):
        """Registering with existing username should return 409."""
        response = client.post("/auth/register", json=registered_user)
        assert response.status_code == 409
        assert "already exists" in response.json()["detail"]

    def test_register_short_username(self, client):
        """Username too short should return 422."""
        response = client.post(
            "/auth/register",
            json={"username": "ab", "password": "securepassword123"},
        )
        assert response.status_code == 422

    def test_register_short_password(self, client):
        """Password too short should return 422."""
        response = client.post(
            "/auth/register",
            json={"username": "validuser", "password": "short"},
        )
        assert response.status_code == 422

    def test_register_invalid_username_chars(self, client):
        """Username with invalid characters should return 422."""
        response = client.post(
            "/auth/register",
            json={"username": "invalid@user!", "password": "securepassword123"},
        )
        assert response.status_code == 422


class TestLogin:
    """Tests for POST /auth/login."""

    def test_login_success(self, client, registered_user):
        """Successful login should return access token."""
        response = client.post("/auth/login", json=registered_user)
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_wrong_password(self, client, registered_user):
        """Login with wrong password should return 401."""
        response = client.post(
            "/auth/login",
            json={"username": registered_user["username"], "password": "wrongpassword"},
        )
        assert response.status_code == 401
        assert "Invalid username or password" in response.json()["detail"]

    def test_login_nonexistent_user(self, client):
        """Login with non-existent user should return 401."""
        response = client.post(
            "/auth/login",
            json={"username": "nonexistent", "password": "anypassword"},
        )
        assert response.status_code == 401


class TestGetMe:
    """Tests for GET /auth/me (protected endpoint)."""

    def test_get_me_success(self, client, registered_user, auth_token):
        """Authenticated request should return user info."""
        response = client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == registered_user["username"]
        assert "id" in data
        assert "created_at" in data

    def test_get_me_without_token(self, client):
        """Request without token should return 401."""
        response = client.get("/auth/me")
        assert response.status_code == 401

    def test_get_me_invalid_token(self, client):
        """Request with invalid token should return 401."""
        response = client.get(
            "/auth/me",
            headers={"Authorization": "Bearer invalid_token_here"},
        )
        assert response.status_code == 401
        assert "Could not validate credentials" in response.json()["detail"]

    def test_get_me_malformed_header(self, client):
        """Request with malformed auth header should fail."""
        response = client.get(
            "/auth/me",
            headers={"Authorization": "NotBearer token"},
        )
        assert response.status_code == 401

    def test_get_me_expired_token(self, client, registered_user):
        """Request with expired token should return 401."""
        # Register and get user
        client.post("/auth/register", json=registered_user)
        login_response = client.post("/auth/login", json=registered_user)
        
        # Create an expired token (expires in -1 seconds)
        user = user_repository.get_by_username(registered_user["username"])
        expired_token = auth_service.create_access_token(
            user_id=user.id,
            expires_delta=timedelta(seconds=-1),
        )

        response = client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {expired_token}"},
        )
        assert response.status_code == 401


class TestFullAuthFlow:
    """Integration tests for complete authentication flow."""

    def test_register_login_me_flow(self, client):
        """Complete flow: register -> login -> /auth/me should succeed."""
        credentials = {"username": "flowuser", "password": "flowpassword123"}

        # Step 1: Register
        register_response = client.post("/auth/register", json=credentials)
        assert register_response.status_code == 201

        # Step 2: Login
        login_response = client.post("/auth/login", json=credentials)
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]

        # Step 3: Access protected endpoint
        me_response = client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert me_response.status_code == 200
        assert me_response.json()["username"] == credentials["username"]

    def test_password_not_stored_plaintext(self, client):
        """Verify password is hashed, not stored as plaintext."""
        credentials = {"username": "hashuser", "password": "plaintextpassword123"}
        client.post("/auth/register", json=credentials)

        user = user_repository.get_by_username(credentials["username"])
        assert user is not None
        assert user.password_hash != credentials["password"]
        # bcrypt hashes start with $2a$ or $2b$
        assert user.password_hash.startswith("$2")
