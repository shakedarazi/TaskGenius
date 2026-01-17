"""
TASKGENIUS Core API - Chat Schemas

Pydantic models for chat API endpoints.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Request model for chat endpoint."""

    message: str = Field(min_length=1, max_length=1000, description="User's chat message")
    conversation_history: Optional[List[Dict[str, str]]] = Field(
        default=None,
        description="Previous conversation messages for context (list of {role: 'user'|'assistant', content: '...'})"
    )



class Command(BaseModel):
    """Structured command from chatbot (Phase 3/4)."""
    intent: str = Field(description="Command intent: add_task|update_task|delete_task|complete_task|list_tasks|clarify")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score (0.0-1.0)")
    fields: Optional[Dict[str, Any]] = Field(default=None, description="Extracted fields for add_task")
    ref: Optional[Dict[str, Any]] = Field(default=None, description="Task reference for update/delete/complete")
    filter: Optional[Dict[str, Any]] = Field(default=None, description="Filter for list_tasks")
    ready: bool = Field(default=False, description="Whether command is ready to execute")
    missing_fields: Optional[List[str]] = Field(default=None, description="Missing required fields")


class ChatResponse(BaseModel):
    """Response model for chat endpoint."""

    reply: str = Field(description="Conversational response from chatbot")
    intent: Optional[str] = Field(default=None, description="Detected intent")
    suggestions: Optional[List[str]] = Field(default=None, description="Suggested actions")
    command: Optional[Command] = Field(default=None, description="Structured command (Phase 3/4)")