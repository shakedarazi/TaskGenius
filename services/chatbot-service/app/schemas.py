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
    conversation_history: Optional[List[Dict[str, str]]] = Field(
        default=None,
        description="Previous conversation messages for context (list of {role: 'user'|'assistant', content: '...'})"
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


class Command(BaseModel):
    intent: str = Field(description="Command intent: add_task|update_task|delete_task|complete_task|list_tasks|clarify")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score (0.0-1.0)")
    fields: Optional[Dict[str, Any]] = Field(default=None, description="Extracted fields for add_task (title, priority, deadline, etc.)")
    ref: Optional[Dict[str, Any]] = Field(default=None, description="Task reference for update/delete/complete")
    filter: Optional[Dict[str, Any]] = Field(default=None, description="Filter for list_tasks")
    ready: bool = Field(default=False, description="Whether all required fields are collected and command is ready to execute")
    missing_fields: Optional[List[str]] = Field(default=None, description="List of required fields that are still missing")


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
    command: Optional[Command] = Field(
        default=None,
        description="Structured command (optional, backward compatible)"
    )