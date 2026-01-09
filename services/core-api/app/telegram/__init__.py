"""
TASKGENIUS Core API - Telegram Integration Module

Telegram webhook and messaging integration.
"""

from app.telegram.router import router as telegram_router

__all__ = ["telegram_router"]
