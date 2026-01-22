import json
import logging
from typing import List, Dict, Any, Optional

from openai import AsyncOpenAI

from app.config import settings
from app.schemas import SuggestResponse, TaskSuggestion

logger = logging.getLogger(__name__)

# OpenAI client (initialized once)
_client: Optional[AsyncOpenAI] = None


def get_client() -> Optional[AsyncOpenAI]:
    global _client
    if _client is None and settings.USE_LLM and settings.OPENAI_API_KEY:
        _client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    return _client


def build_prompt(message: str, tasks: Optional[List[Dict[str, Any]]]) -> str:
    """Build prompt for task suggestion generation."""
    tasks_context = ""
    if tasks:
        titles = [t.get("title", "") for t in tasks[:10]]
        tasks_context = f"\nEXISTING TASKS (avoid duplicates): {', '.join(titles)}"
    
    return f"""You are a task suggestion assistant.

USER MESSAGE: "{message}"
{tasks_context}

Generate a JSON response with:
- "summary": 2 short sentences summarizing what the user said (SAME LANGUAGE as user)
- "suggestions": array of 5-8 task objects

Each task MUST have:
- "title": string (clear, actionable, SAME LANGUAGE as user)
- "priority": "low" | "medium" | "high" | "urgent"

Each task MAY have:
- "category": "work" | "study" | "personal" | "health" | "finance" | "errands" | "other"
- "estimate_bucket": "lt_15" | "15_30" | "30_60" | "60_120" | "gt_120"

RULES:
- Match user's language exactly (Hebrew → Hebrew, English → English)
- Infer priority from urgency words
- Be specific and actionable
- No markdown, ONLY valid JSON"""


def parse_response(content: str) -> Optional[Dict[str, Any]]:
    """Parse AI response JSON."""
    try:
        # Strip markdown code blocks if present
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        return json.loads(content.strip())
    except (json.JSONDecodeError, IndexError):
        return None


def fallback_response(message: str) -> SuggestResponse:
    """Deterministic fallback when AI fails."""
    is_hebrew = any('\u0590' <= c <= '\u05FF' for c in message)
    
    if is_hebrew:
        return SuggestResponse(
            summary="קיבלתי את ההודעה שלך. הנה כמה הצעות למשימות.",
            suggestions=[
                TaskSuggestion(title="לתכנן את המשימה הראשית", priority="high", category="work"),
                TaskSuggestion(title="לפרק למשימות קטנות", priority="medium", category="work"),
                TaskSuggestion(title="להגדיר תאריך יעד", priority="medium", category="personal"),
                TaskSuggestion(title="לסדר סדרי עדיפויות", priority="low", category="personal"),
                TaskSuggestion(title="לבדוק משימות קיימות", priority="low", category="other"),
            ]
        )
    
    return SuggestResponse(
        summary="I received your message. Here are some task suggestions.",
        suggestions=[
            TaskSuggestion(title="Plan the main task", priority="high", category="work"),
            TaskSuggestion(title="Break into smaller tasks", priority="medium", category="work"),
            TaskSuggestion(title="Set a deadline", priority="medium", category="personal"),
            TaskSuggestion(title="Prioritize tasks", priority="low", category="personal"),
            TaskSuggestion(title="Review existing tasks", priority="low", category="other"),
        ]
    )


async def generate_suggestions(
    message: str,
    user_id: str,
    tasks: Optional[List[Dict[str, Any]]] = None
) -> SuggestResponse:
    """Generate task suggestions from user message."""
    client = get_client()
    
    if not client:
        logger.debug("No OpenAI client, using fallback")
        return fallback_response(message)
    
    prompt = build_prompt(message, tasks)
    
    try:
        response = await client.chat.completions.create(
            model=settings.MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500,
            timeout=settings.LLM_TIMEOUT,
        )
        
        content = response.choices[0].message.content
        if not content:
            return fallback_response(message)
        
        data = parse_response(content)
        if not data or "suggestions" not in data:
            logger.warning("Invalid AI response format")
            return fallback_response(message)
        
        # Validate and build response
        suggestions = []
        for s in data.get("suggestions", [])[:8]:
            if not s.get("title"):
                continue
            suggestions.append(TaskSuggestion(
                title=s["title"],
                priority=s.get("priority", "medium"),
                category=s.get("category"),
                estimate_bucket=s.get("estimate_bucket"),
            ))
        
        if len(suggestions) < 3:
            return fallback_response(message)
        
        return SuggestResponse(
            summary=data.get("summary", ""),
            suggestions=suggestions
        )
        
    except Exception as e:
        logger.warning(f"AI request failed: {e}")
        return fallback_response(message)
