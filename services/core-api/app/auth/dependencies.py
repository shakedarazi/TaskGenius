from typing import Annotated, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.database import get_database
from app.auth.models import User
from app.auth.service import AuthService
from app.auth.repository import MongoUserRepository


# HTTP Bearer token scheme - auto_error=False to handle missing tokens ourselves
bearer_scheme = HTTPBearer(auto_error=False)


def get_auth_service(
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)]
) -> AuthService:
    """Dependency to get AuthService instance with MongoDB repository."""
    user_repo = MongoUserRepository(db)
    return AuthService(user_repo)


async def get_current_user(
    credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(bearer_scheme)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if credentials is None:
        raise credentials_exception

    token = credentials.credentials
    
    # Create temporary AuthService just for token decoding (synchronous operation)
    from app.auth.service import AuthService
    from app.auth.repository import UserRepositoryInterface
    
    class DummyRepo(UserRepositoryInterface):
        async def create(self, user): pass
        async def get_by_id(self, user_id): return None
        async def get_by_username(self, username): return None
        async def exists_by_username(self, username): return False
    
    temp_auth = AuthService(DummyRepo())
    user_id = temp_auth.decode_token(token)

    if user_id is None:
        raise credentials_exception

    user = await auth_service.get_user_by_id(user_id)
    if user is None:
        raise credentials_exception

    return user


# Type alias for cleaner dependency injection
CurrentUser = Annotated[User, Depends(get_current_user)]
