"""
TASKGENIUS Core API - Chat Schemas

Pydantic models for chat API endpoints.
"""

from typing import Optional, List
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Request model for chat endpoint."""

    message: str = Field(min_length=1, max_length=1000, description="User's chat message")


class ChatResponse(BaseModel):
    """Response model for chat endpoint."""

    reply: str = Field(description="Conversational response from chatbot")
    intent: Optional[str] = Field(default=None, description="Detected intent")
    suggestions: Optional[List[str]] = Field(default=None, description="Suggested actions")
