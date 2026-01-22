from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Chat request - either a message or a selection."""
    message: Optional[str] = Field(default=None, max_length=1000, description="User message for suggestions")
    selection: Optional[int] = Field(default=None, ge=1, le=10, description="Selection number to add task")
    deadline: Optional[str] = Field(default=None, description="Optional deadline ISO string for selected task")


class TaskSuggestion(BaseModel):
    """Task suggestion for display."""
    title: str
    priority: str
    category: Optional[str] = None
    estimate_bucket: Optional[str] = None


class ChatResponse(BaseModel):
    """Chat response with reply and optional suggestions."""
    reply: str
    suggestions: Optional[List[TaskSuggestion]] = None
    added_task: Optional[Dict[str, Any]] = None
