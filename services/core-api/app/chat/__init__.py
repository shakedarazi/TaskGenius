"""
TASKGENIUS Core API - Chat Module

Phase 4: Chat facade via chatbot-service.
"""

from app.chat.router import router as chat_router

__all__ = ["chat_router"]
