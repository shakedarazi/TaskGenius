"""
Chat Service - Orchestrates suggestions and task creation.
Stateless except for in-memory suggestion cache.
"""
import logging
import httpx
from typing import Dict, List, Optional, Any

from app.config import settings
from app.tasks.repository import TaskRepositoryInterface
from app.tasks.models import Task
from app.tasks.enums import TaskStatus, TaskPriority, TaskCategory, EstimateBucket
from app.chat.schemas import ChatResponse, TaskSuggestion

logger = logging.getLogger(__name__)

# In-memory cache: user_id → list of suggestions
_suggestions_cache: Dict[str, List[Dict[str, Any]]] = {}


def get_cached_suggestions(user_id: str) -> Optional[List[Dict[str, Any]]]:
    return _suggestions_cache.get(user_id)


def set_cached_suggestions(user_id: str, suggestions: List[Dict[str, Any]]) -> None:
    _suggestions_cache[user_id] = suggestions


def clear_cached_suggestions(user_id: str) -> None:
    _suggestions_cache.pop(user_id, None)


def format_reply(summary: str, suggestions: List[Dict[str, Any]], is_hebrew: bool) -> str:
    """Format suggestions as numbered list."""
    priority_labels = {
        "low": "נמוכה" if is_hebrew else "low",
        "medium": "בינונית" if is_hebrew else "medium",
        "high": "גבוהה" if is_hebrew else "high",
        "urgent": "דחופה" if is_hebrew else "urgent",
    }
    
    lines = [summary, ""]
    for i, s in enumerate(suggestions, 1):
        p = priority_labels.get(s.get("priority", "medium"), s.get("priority", ""))
        lines.append(f"{i}. {s['title']} ({p})")
    
    cta = "\nבחר 1-{} להוספה" if is_hebrew else "\nChoose 1-{} to add"
    lines.append(cta.format(len(suggestions)))
    
    return "\n".join(lines)


async def call_chatbot_service(message: str, user_id: str, tasks: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Call chatbot-service for suggestions."""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{settings.CHATBOT_SERVICE_URL}/interpret",
                json={"message": message, "user_id": user_id, "tasks": tasks},
                timeout=10.0,
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Chatbot service error: {e}")
            return None


async def process_message(
    user_id: str,
    message: Optional[str],
    selection: Optional[int],
    task_repository: TaskRepositoryInterface,
    deadline: Optional[str] = None,
) -> ChatResponse:
    """Process chat request - either generate suggestions or add selected task."""
    is_hebrew = message and any('\u0590' <= c <= '\u05FF' for c in message)
    
    # Handle selection
    if selection is not None:
        cached = get_cached_suggestions(user_id)
        if not cached:
            return ChatResponse(
                reply="אין הצעות לבחירה. שלח הודעה חדשה." if is_hebrew else "No suggestions available. Send a new message."
            )
        
        if selection < 1 or selection > len(cached):
            return ChatResponse(
                reply=f"בחר מספר בין 1 ל-{len(cached)}" if is_hebrew else f"Choose a number between 1 and {len(cached)}"
            )
        
        # Add task from selection
        suggestion = cached[selection - 1]
        task = await add_task_from_suggestion(user_id, suggestion, task_repository, deadline)
        clear_cached_suggestions(user_id)
        
        return ChatResponse(
            reply=f"✅ הוספתי: {task.title}" if is_hebrew else f"✅ Added: {task.title}",
            added_task={"id": task.id, "title": task.title, "priority": task.priority.value}
        )
    
    # Handle message - generate suggestions
    if not message or not message.strip():
        return ChatResponse(
            reply="שלח הודעה כדי לקבל הצעות למשימות." if is_hebrew else "Send a message to get task suggestions."
        )
    
    # Get existing tasks for context
    tasks = await task_repository.list_by_owner(user_id)
    tasks_data = [{"id": t.id, "title": t.title, "priority": t.priority.value} for t in tasks]
    
    # Call chatbot-service
    result = await call_chatbot_service(message, user_id, tasks_data)
    
    if not result or "suggestions" not in result:
        return ChatResponse(
            reply="לא הצלחתי ליצור הצעות. נסה שוב." if is_hebrew else "Failed to generate suggestions. Please try again."
        )
    
    suggestions = result["suggestions"]
    summary = result.get("summary", "")
    
    # Cache suggestions
    set_cached_suggestions(user_id, suggestions)
    
    # Format response
    reply = format_reply(summary, suggestions, is_hebrew)
    
    return ChatResponse(
        reply=reply,
        suggestions=[TaskSuggestion(**s) for s in suggestions]
    )


async def add_task_from_suggestion(
    user_id: str,
    suggestion: Dict[str, Any],
    task_repository: TaskRepositoryInterface,
    deadline: Optional[str] = None,
) -> Task:
    """Create task from suggestion."""
    from datetime import datetime
    
    priority_map = {"low": TaskPriority.LOW, "medium": TaskPriority.MEDIUM, "high": TaskPriority.HIGH, "urgent": TaskPriority.URGENT}
    category_map = {"work": TaskCategory.WORK, "study": TaskCategory.STUDY, "personal": TaskCategory.PERSONAL,
                    "health": TaskCategory.HEALTH, "finance": TaskCategory.FINANCE, "errands": TaskCategory.ERRANDS, "other": TaskCategory.OTHER}
    estimate_map = {"lt_15": EstimateBucket.LT_15, "15_30": EstimateBucket._15_30, "30_60": EstimateBucket._30_60,
                    "60_120": EstimateBucket._60_120, "gt_120": EstimateBucket.GT_120}
    
    # Parse deadline if provided
    parsed_deadline = None
    if deadline:
        try:
            parsed_deadline = datetime.fromisoformat(deadline.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            pass  # Invalid deadline format, omit it
    
    task = Task.create(
        owner_id=user_id,
        title=suggestion["title"],
        status=TaskStatus.OPEN,
        priority=priority_map.get(suggestion.get("priority", "medium"), TaskPriority.MEDIUM),
        category=category_map.get(suggestion.get("category")) if suggestion.get("category") else None,
        estimate_bucket=estimate_map.get(suggestion.get("estimate_bucket")) if suggestion.get("estimate_bucket") else None,
        deadline=parsed_deadline,
    )
    
    return await task_repository.create(task)
