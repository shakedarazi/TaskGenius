"""
TASKGENIUS Chatbot Service - Schemas

Pydantic models for chatbot request/response.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator


class ChatRequest(BaseModel):
    """
    Request from core-api to chatbot-service.
    
    Contains user message and relevant context data.
    """

    message: str = Field(
        min_length=1,
        max_length=1000,
        description="User's chat message"
    )
    user_id: str = Field(
        min_length=1,
        description="User ID for context"
    )
    tasks: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="User's tasks (if relevant to the query)"
    )
    weekly_summary: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Weekly insights summary (if requested)"
    )
    
    @field_validator("message")
    @classmethod
    def validate_message(cls, v: str) -> str:
        """Validate message is not just whitespace."""
        if not v or not v.strip():
            raise ValueError("Message cannot be empty or whitespace only")
        return v.strip()
    
    @field_validator("user_id")
    @classmethod
    def validate_user_id(cls, v: str) -> str:
        """Validate user_id is not just whitespace."""
        if not v or not v.strip():
            raise ValueError("User ID cannot be empty or whitespace only")
        return v.strip()


class ChatResponse(BaseModel):
    """
    Response from chatbot-service to core-api.
    
    Contains conversational reply and any structured proposals.
    """

    reply: str = Field(description="Conversational response to the user")
    intent: Optional[str] = Field(
        default=None,
        description="Detected intent (if applicable)"
    )
    suggestions: Optional[List[str]] = Field(
        default=None,
        description="Suggested actions or follow-ups"
    )
