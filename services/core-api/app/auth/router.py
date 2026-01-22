from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.database import get_database
from app.auth.schemas import (
    UserRegisterRequest,
    UserLoginRequest,
    UserResponse,
    TokenResponse,
    MessageResponse,
)
from app.auth.service import AuthService
from app.auth.repository import MongoUserRepository
from app.auth.dependencies import CurrentUser


def get_auth_service(
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)]
) -> AuthService:
    """Dependency to get AuthService instance with MongoDB repository."""
    user_repo = MongoUserRepository(db)
    return AuthService(user_repo)


router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
)
async def register(
    request: UserRegisterRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> MessageResponse:
    user = await auth_service.register_user(
        username=request.username,
        password=request.password,
    )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already exists",
        )

    return MessageResponse(message="User registered successfully")


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login and get access token",
)
async def login(
    request: UserLoginRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> TokenResponse:
    user = await auth_service.authenticate_user(
        username=request.username,
        password=request.password,
    )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = auth_service.create_access_token(user_id=user.id)

    return TokenResponse(access_token=access_token)


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user info",
)
async def get_me(current_user: CurrentUser) -> UserResponse:
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        created_at=current_user.created_at,
    )
