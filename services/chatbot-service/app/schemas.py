from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class TaskSuggestion(BaseModel):
    """Single task suggestion matching Task schema."""
    title: str
    priority: str = "medium"  # low|medium|high|urgent
    category: Optional[str] = None  # work|study|personal|health|finance|errands|other
    estimate_bucket: Optional[str] = None  # lt_15|15_30|30_60|60_120|gt_120


class SuggestRequest(BaseModel):
    """Request for generating task suggestions."""
    message: str = Field(min_length=1, max_length=1000)
    user_id: str = Field(min_length=1)
    tasks: Optional[List[Dict[str, Any]]] = None  # Existing tasks for context


class SuggestResponse(BaseModel):
    """Response with summary and task suggestions."""
    summary: str
    suggestions: List[TaskSuggestion]
