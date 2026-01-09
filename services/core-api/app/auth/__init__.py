"""
TASKGENIUS Core API - Authentication Module

Phase 1: Register/login with JWT authentication.
"""

from app.auth.router import router as auth_router
from app.auth.dependencies import get_current_user

__all__ = ["auth_router", "get_current_user"]
