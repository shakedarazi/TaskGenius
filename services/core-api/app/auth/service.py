from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
from jose import jwt, JWTError

from app.config import settings
from app.auth.models import User
from app.auth.repository import UserRepositoryInterface


class AuthService:
    """Authentication service with password hashing and JWT operations."""

    def __init__(self, repository: UserRepositoryInterface):
        self.repository = repository

    def hash_password(self, password: str) -> str:
        """Hash a password using bcrypt."""
        password_bytes = password.encode("utf-8")
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password_bytes, salt).decode("utf-8")

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash."""
        password_bytes = plain_password.encode("utf-8")
        hashed_bytes = hashed_password.encode("utf-8")
        return bcrypt.checkpw(password_bytes, hashed_bytes)

    def create_access_token(self, user_id: str, expires_delta: Optional[timedelta] = None) -> str:
        """Create a JWT access token."""
        if expires_delta is None:
            expires_delta = timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)

        now = datetime.now(timezone.utc)
        expire = now + expires_delta
        to_encode = {
            "sub": user_id,
            "exp": expire,
            "iat": now,
        }
        return jwt.encode(
            to_encode,
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM,
        )

    def decode_token(self, token: str) -> Optional[str]:
        """Decode and validate a JWT token. Returns user_id if valid."""
        try:
            payload = jwt.decode(
                token,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM],
            )
            user_id: str = payload.get("sub")
            if user_id is None:
                return None
            return user_id
        except JWTError:
            return None

    async def register_user(self, username: str, password: str) -> Optional[User]:
        """Register a new user. Returns None if username exists."""
        if await self.repository.exists_by_username(username):
            return None

        password_hash = self.hash_password(password)
        user = User.create(username=username, password_hash=password_hash)
        return await self.repository.create(user)

    async def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """Authenticate user by username and password."""
        user = await self.repository.get_by_username(username)
        if user is None:
            return None
        if not self.verify_password(password, user.password_hash):
            return None
        return user

    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID."""
        return await self.repository.get_by_id(user_id)


# Note: auth_service singleton removed - must be created with database dependency
