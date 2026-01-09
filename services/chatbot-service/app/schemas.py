"""
TASKGENIUS Chatbot Service - Schemas

Pydantic models for chatbot request/response.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """
    Request from core-api to chatbot-service.
    
    Contains user message and relevant context data.
    """

    message: str = Field(description="User's chat message")
    user_id: str = Field(description="User ID for context")
    tasks: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="User's tasks (if relevant to the query)"
    )
    weekly_summary: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Weekly insights summary (if requested)"
    )


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
