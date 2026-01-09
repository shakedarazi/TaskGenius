"""
TASKGENIUS Core API - Authentication Dependencies

FastAPI dependencies for JWT validation and user context.
"""

from typing import Annotated, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.auth.models import User
from app.auth.service import auth_service


# HTTP Bearer token scheme - auto_error=False to handle missing tokens ourselves
bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(bearer_scheme)]
) -> User:
    """
    Dependency to get the current authenticated user from JWT token.
    
    Usage:
        @app.get("/protected")
        async def protected_route(current_user: User = Depends(get_current_user)):
            return {"user_id": current_user.id}
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if credentials is None:
        raise credentials_exception

    token = credentials.credentials
    user_id = auth_service.decode_token(token)

    if user_id is None:
        raise credentials_exception

    user = auth_service.get_user_by_id(user_id)
    if user is None:
        raise credentials_exception

    return user


# Type alias for cleaner dependency injection
CurrentUser = Annotated[User, Depends(get_current_user)]
