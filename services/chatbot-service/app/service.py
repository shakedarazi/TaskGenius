"""
TASKGENIUS Chatbot Service - Service

Business logic for generating conversational responses.
This is a read-only facade - no mutations or DB access.
"""

import logging
import json
import re
from typing import Optional, Dict, Any, List
from app.schemas import ChatRequest, ChatResponse, Command
from app.config import settings

logger = logging.getLogger(__name__)


class ChatbotService:
    """
    Service for generating conversational responses.
    
    This service:
    - Generates responses based on provided data
    - Does NOT access databases
    - Does NOT mutate state
    - Outputs are proposals/suggestions only
    """

    def __init__(self):
        # LLM client abstraction (mockable for tests)
        self._llm_client = None
        self._openai_client = None
        
        # Initialize OpenAI client if configured
        if settings.USE_LLM and settings.OPENAI_API_KEY:
            try:
                from openai import AsyncOpenAI
                self._openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
                logger.info("OpenAI client initialized")
            except ImportError:
                logger.warning("OpenAI package not installed, LLM features disabled")
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI client: {e}")

    def _get_llm_client(self):
        """Get LLM client (can be mocked in tests)."""
        return self._llm_client

    def _set_llm_client(self, client):
        """Set LLM client (for dependency injection in tests)."""
        self._llm_client = client

    async def generate_response(self, request: ChatRequest) -> ChatResponse:
        """
        Generate a conversational response based on user message and context.
        
        Args:
            request: Chat request with message and context data
        
        Returns:
            ChatResponse with conversational reply
        
        Raises:
            ValueError: If request is invalid
        """
        # Validate request
        if not request.message:
            logger.warning("Empty message in request")
            raise ValueError("Message cannot be empty")
        
        if not request.user_id:
            logger.warning("Empty user_id in request")
            raise ValueError("User ID cannot be empty")
        
        message = request.message.strip()
        logger.debug(f"Processing message: {message[:100]}...")
        
        # Log context info
        task_count = len(request.tasks) if request.tasks else 0
        has_summary = request.weekly_summary is not None
        logger.debug(f"Context: {task_count} tasks, summary={has_summary}")

        # Phase 1: Try LLM first, fallback to rule-based
        if settings.USE_LLM and self._openai_client:
            try:
                response = await self._generate_llm_response(request)
                if response:
                    logger.info("Generated response using LLM")
                    return response
            except Exception as e:
                # Check if it's a quota/billing error
                error_msg = str(e)
                is_quota_error = any(keyword in error_msg.lower() for keyword in ["quota", "429", "insufficient_quota", "billing", "payment"])
                
                if is_quota_error:
                    logger.warning("LLM quota exceeded or billing issue, using rule-based fallback")
                    # Return a user-friendly message about quota issue
                    is_hebrew = any('\u0590' <= char <= '\u05FF' for char in request.message)
                    if is_hebrew:
                        quota_message = "⚠️ הגעת למגבלת ה-quota של OpenAI. התשובה כאן היא מ-rule-based (לא AI). כדי לחדש: פתח את https://platform.openai.com/account/billing והוסף credit."
                    else:
                        quota_message = "⚠️ You've reached your OpenAI quota limit. This response is from rule-based (not AI). To renew: go to https://platform.openai.com/account/billing and add credits."
                    
                    # Still generate a rule-based response, but prepend the quota warning
                    rule_based_response = await self._generate_rule_based_response(request)
                    rule_based_response.reply = f"{quota_message}\n\n{rule_based_response.reply}"
                    return rule_based_response
                else:
                    logger.warning(f"LLM generation failed, falling back to rule-based: {e}")
        
        # Fallback to rule-based logic
        return await self._generate_rule_based_response(request)
    
    async def _generate_rule_based_response(self, request: ChatRequest) -> ChatResponse:
        """Generate rule-based response (fallback when LLM is unavailable)."""
        logger.debug("Using rule-based response generation")
        message = request.message.strip()
        message_lower = message.lower()
        
        # Detect if message is in Hebrew (contains Hebrew characters)
        is_hebrew = any('\u0590' <= char <= '\u05FF' for char in message)
        
        # Phase 2: Improved intent detection with clarification logic
        # Order matters: check more specific intents first
        # Check for task insights (deadlines, priorities, urgency) - highest priority
        if any(word in message_lower for word in ["summary", "insights", "report", "weekly", "סיכום", "דוח"]):
            return self._handle_insights(request, is_hebrew)
        elif any(word in message_lower for word in ["urgent", "priority", "deadline", "due", "דחוף", "עדיפות", "תאריך"]):
            return self._handle_task_insights(request, is_hebrew)
        
        # Check for delete intent FIRST (before update) - more destructive, needs higher priority
        elif any(word in message_lower for word in ["delete", "remove", "מחק", "הסר", "תמחק", "תמחקי"]):
            return self._handle_potential_delete(request, is_hebrew)
        # Check for update/complete intents (less destructive than delete)
        elif any(word in message_lower for word in ["update", "change", "modify", "edit", "עדכן", "שנה", "ערוך"]):
            return self._handle_potential_update(request, is_hebrew)
        elif any(word in message_lower for word in ["complete", "done", "finish", "בוצע", "סיים", "סיימתי"]):
            return self._handle_potential_update(request, is_hebrew)
        
        # Check for list tasks
        elif any(word in message_lower for word in ["list", "show", "tasks", "what", "רשימה", "הצג", "מה"]):
            return self._handle_list_tasks(request, is_hebrew)
        
        # Check for create intent (potential - needs clarification) - last, as "task" is common
        elif any(word in message_lower for word in ["create", "add", "new", "צור", "הוסף", "תוסיף"]):
            return self._handle_potential_create(request, is_hebrew)
        
        # Check for help
        elif any(word in message_lower for word in ["help", "how", "what can", "עזרה", "איך"]):
            return self._handle_help(is_hebrew)
        else:
            return self._handle_general(request, is_hebrew)

    def _handle_list_tasks(self, request: ChatRequest, is_hebrew: bool = False) -> ChatResponse:
        """Handle list tasks intent with natural, varied responses."""
        if request.tasks is not None:
            # tasks was explicitly provided (even if empty list)
            count = len(request.tasks)
            if count == 0:
                if is_hebrew:
                    replies = [
                        "אין לך משימות כרגע. רוצה שאוסיף אחת?",
                        "עדיין לא יצרת משימות. בוא נתחיל!",
                        "הרשימה שלך ריקה. תרצה ליצור משימה חדשה?"
                    ]
                    reply = replies[hash(request.user_id) % len(replies)]
                else:
                    replies = [
                        "You don't have any tasks yet. Would you like to create one?",
                        "Your task list is empty. Let's add your first task!",
                        "No tasks found. I can help you create one."
                    ]
                    reply = replies[hash(request.user_id) % len(replies)]
            else:
                if is_hebrew:
                    task_titles = [t.get("title", "ללא כותרת") for t in request.tasks[:3]]
                    if count == 1:
                        reply = f"יש לך משימה אחת: {task_titles[0]}."
                    elif count <= 3:
                        reply = f"יש לך {count} משימות: {', '.join(task_titles)}."
                    else:
                        reply = f"יש לך {count} משימות. הנה כמה מהן: {', '.join(task_titles)}, ועוד {count - 3} נוספות."
                else:
                    task_titles = [t.get("title", "Untitled") for t in request.tasks[:3]]
                    if count == 1:
                        reply = f"You have one task: {task_titles[0]}."
                    elif count <= 3:
                        reply = f"You have {count} tasks: {', '.join(task_titles)}."
                    else:
                        reply = f"You have {count} tasks. Here are a few: {', '.join(task_titles)}, and {count - 3} more."
        else:
            # tasks was not provided
            if is_hebrew:
                reply = "אני יכול לעזור לך לראות את המשימות שלך. תן לי רגע לאסוף אותן."
            else:
                reply = "I can help you see your tasks. Let me fetch them for you."
        
        suggestions = ["הצג את כל המשימות", "סנן לפי סטטוס", "צור משימה חדשה"] if is_hebrew else ["View all tasks", "Filter by status", "Create new task"]
        
        return ChatResponse(
            reply=reply,
            intent="list_tasks",
            suggestions=suggestions
        )

    def _handle_insights(self, request: ChatRequest, is_hebrew: bool = False) -> ChatResponse:
        """Handle insights/summary intent."""
        if request.weekly_summary:
            summary = request.weekly_summary
            completed = summary.get("completed", {}).get("count", 0)
            high_priority = summary.get("high_priority", {}).get("count", 0)
            upcoming = summary.get("upcoming", {}).get("count", 0)
            overdue = summary.get("overdue", {}).get("count", 0)
            
            if is_hebrew:
                reply = f"הנה הסיכום השבועי שלך: "
                reply += f"{completed} הושלמו, "
                reply += f"{high_priority} בעדיפות גבוהה פתוחות, "
                reply += f"{upcoming} קרובות, "
                reply += f"{overdue} באיחור."
            else:
                reply = f"Here's your weekly summary: "
                reply += f"{completed} completed, "
                reply += f"{high_priority} high-priority open, "
                reply += f"{upcoming} upcoming, "
                reply += f"{overdue} overdue."
        else:
            reply = "אני יכול ליצור לך סיכום שבועי. תן לי לאסוף את הנתונים שלך." if is_hebrew else "I can generate a weekly summary for you. Let me fetch your insights."
        
        suggestions = ["הצג סיכום מפורט", "סנן לפי קטגוריה"] if is_hebrew else ["View detailed summary", "Filter by category"]
        
        return ChatResponse(
            reply=reply,
            intent="get_insights",
            suggestions=suggestions
        )

    def _handle_potential_create(self, request: ChatRequest, is_hebrew: bool = False) -> ChatResponse:
        """Handle potential create task intent - asks for clarification."""
        # Check conversation history to see what was already asked
        has_title = False
        has_priority = False
        has_deadline_asked = False
        
        # Check current message for title
        message_words = request.message.split()
        has_title = any(len(word) > 3 for word in message_words if word.lower() not in ["create", "add", "new", "task", "צור", "הוסף", "תוסיף", "משימה", "low", "medium", "high", "urgent", "נמוכה", "בינונית", "גבוהה", "דחופה"])
        
        # Check conversation history for collected fields
        if request.conversation_history:
            prev_assistant_asked_title = False
            for i, msg in enumerate(request.conversation_history[-5:]):  # Check last 5 messages
                content_lower = msg.get("content", "").lower()
                role = msg.get("role", "")
                if role == "user":
                    # Check if user provided title (if previous assistant asked for title, this is likely the answer)
                    if prev_assistant_asked_title:
                        # If previous message was assistant asking for title, current user message is the title
                        has_title = True
                    # Also check if message contains substantial text (not just commands)
                    elif any(len(word) > 3 for word in content_lower.split() if word not in ["create", "add", "new", "task", "צור", "הוסף", "תוסיף", "משימה"]):
                        has_title = True
                    # Check if user provided priority
                    if any(priority_word in content_lower for priority_word in ["low", "medium", "high", "urgent", "נמוכה", "בינונית", "גבוהה", "דחופה"]):
                        has_priority = True
                    prev_assistant_asked_title = False  # Reset after user message
                elif role == "assistant":
                    # Check if assistant asked for title
                    if "title" in content_lower or "כותרת" in content_lower or "which task" in content_lower or "איזו משימה" in content_lower:
                        prev_assistant_asked_title = True
                    # Check if we already asked about deadline
                    if "deadline" in content_lower or "תאריך" in content_lower or "יעד" in content_lower:
                        has_deadline_asked = True
        
        if is_hebrew:
            if not has_title:
                replies = [
                    "אני מבין שאתה רוצה ליצור משימה. איזו משימה תרצה ליצור? תן לי כותרת.",
                    "בוא ניצור משימה חדשה! מה הכותרת של המשימה?",
                    "אני יכול לעזור לך ליצור משימה. מה תרצה להוסיף לרשימה?"
                ]
                reply = replies[hash(request.user_id + request.message) % len(replies)]
            elif not has_priority:
                replies = [
                    "מעולה! עכשיו אני צריך לדעת מה העדיפות. מה העדיפות של המשימה? (נמוכה/בינונית/גבוהה/דחופה)",
                    "טוב! כדי להמשיך, מה העדיפות? (נמוכה/בינונית/גבוהה/דחופה)",
                    "נהדר! עכשיו אני צריך לדעת מה העדיפות. מה העדיפות? (נמוכה/בינונית/גבוהה/דחופה)"
                ]
                reply = replies[hash(request.user_id + request.message) % len(replies)]
            elif not has_deadline_asked:
                replies = [
                    "מצוין! האם יש תאריך יעד למשימה? (אם לא, פשוט תגיד 'לא' או 'אין')",
                    "טוב! האם יש תאריך יעד? (אם לא, תגיד 'לא')",
                    "נהדר! האם יש תאריך יעד למשימה? (אם לא, תגיד 'אין')"
                ]
                reply = replies[hash(request.user_id + request.message) % len(replies)]
            else:
                # All fields collected, should be ready (but LLM will validate)
                reply = "מעולה! אני מוכן ליצור את המשימה. האם אתה מוכן?"
            suggestions = ["הגדר תאריך יעד", "הוסף קטגוריה", "הגדר עדיפות"] if not has_priority else (["הגדר תאריך יעד"] if not has_deadline_asked else [])
        else:
            if not has_title:
                replies = [
                    "I understand you want to create a task. Which task would you like to create? Please provide a title.",
                    "Let's create a new task! What's the task title?",
                    "I can help you create a task. What would you like to add to your list?"
                ]
                reply = replies[hash(request.user_id + request.message) % len(replies)]
            elif not has_priority:
                replies = [
                    "Great! Now I need to know the priority. What's the priority? (low/medium/high/urgent)",
                    "Good! To continue, what's the priority? (low/medium/high/urgent)",
                    "Perfect! Now I need to know the priority. What's the priority? (low/medium/high/urgent)"
                ]
                reply = replies[hash(request.user_id + request.message) % len(replies)]
            elif not has_deadline_asked:
                replies = [
                    "Excellent! Is there a deadline for this task? (If not, just say 'no' or 'none')",
                    "Good! Is there a deadline? (If not, say 'no')",
                    "Perfect! Is there a deadline for this task? (If not, say 'none')"
                ]
                reply = replies[hash(request.user_id + request.message) % len(replies)]
            else:
                # All fields collected, should be ready (but LLM will validate)
                reply = "Great! I'm ready to create the task. Are you ready?"
            suggestions = ["Set deadline", "Add category", "Set priority"] if not has_priority else (["Set deadline"] if not has_deadline_asked else [])
        
        return ChatResponse(
            reply=reply,
            intent="potential_create",
            suggestions=suggestions
        )

    def _handle_task_insights(self, request: ChatRequest, is_hebrew: bool = False) -> ChatResponse:
        """Handle task insights intent (deadlines, priorities, urgency) with natural responses."""
        if not request.tasks:
            if is_hebrew:
                replies = [
                    "אין לך משימות כרגע, אז אין מה לנתח. בוא נתחיל ליצור!",
                    "הרשימה שלך ריקה. תרצה ליצור משימה כדי שאוכל לעזור לך?",
                    "עדיין לא יצרת משימות. בוא נתחיל!"
                ]
                reply = replies[hash(request.user_id) % len(replies)]
                suggestions = ["צור משימה", "ראה את כל המשימות"]
            else:
                replies = [
                    "You don't have any tasks right now, so there's nothing to analyze. Let's create one!",
                    "Your task list is empty. Would you like to create a task so I can help you?",
                    "No tasks found yet. Let's get started!"
                ]
                reply = replies[hash(request.user_id) % len(replies)]
                suggestions = ["Create a task", "View all tasks"]
            return ChatResponse(
                reply=reply,
                intent="task_insights",
                suggestions=suggestions
            )
        
        # Analyze tasks for insights
        high_priority = [t for t in request.tasks if t.get("priority", "").lower() in ["high", "urgent", "גבוהה", "דחופה"]]
        upcoming = [t for t in request.tasks if t.get("deadline")]  # Simplified - would need date parsing
        
        if is_hebrew:
            if high_priority and upcoming:
                reply = f"בוא נבדוק מה דחוף: יש לך {len(high_priority)} משימות בעדיפות גבוהה ו-{len(upcoming)} משימות עם תאריכי יעד. כדאי להתמקד בהן!"
            elif high_priority:
                reply = f"יש לך {len(high_priority)} משימות בעדיפות גבוהה שדורשות תשומת לב מיידית."
            elif upcoming:
                reply = f"יש לך {len(upcoming)} משימות עם תאריכי יעד. כדאי לבדוק מה קרוב."
            else:
                reply = "כרגע אין משימות דחופות או עם תאריכי יעד קרובים. הכל בשליטה!"
            suggestions = ["ראה משימות דחופות", "ראה משימות עם תאריכי יעד", "ראה סיכום שבועי"]
        else:
            if high_priority and upcoming:
                reply = f"Let's see what's urgent: You have {len(high_priority)} high-priority tasks and {len(upcoming)} tasks with deadlines. You should focus on these!"
            elif high_priority:
                reply = f"You have {len(high_priority)} high-priority tasks that need immediate attention."
            elif upcoming:
                reply = f"You have {len(upcoming)} tasks with deadlines. You should check what's coming up."
            else:
                reply = "No urgent tasks or upcoming deadlines right now. You're all set!"
            suggestions = ["View urgent tasks", "View tasks with deadlines", "View weekly summary"]
        
        return ChatResponse(
            reply=reply,
            intent="task_insights",
            suggestions=suggestions
        )

    def _handle_potential_update(self, request: ChatRequest, is_hebrew: bool = False) -> ChatResponse:
        """Handle potential update task intent - asks for clarification."""
        # Initialize has_confirmation at the start to avoid UnboundLocalError
        has_confirmation = False
        
        if not request.tasks:
            if is_hebrew:
                reply = "אין לך משימות לעדכן."
                suggestions = ["צור משימה", "ראה את כל המשימות"]
            else:
                reply = "You don't have any tasks to update."
                suggestions = ["Create a task", "View all tasks"]
            return ChatResponse(
                reply=reply,
                intent="potential_update",
                suggestions=suggestions
            )
        
        # Check if task is specified
        message_lower = request.message.lower()
        task_titles = [t.get("title", "").lower() for t in request.tasks]
        task_mentioned = any(title in message_lower for title in task_titles if title)
        
        if is_hebrew:
            if not task_mentioned:
                if len(request.tasks) == 1:
                    replies = [
                        f"אני מבין שאתה רוצה לעדכן משימה. האם אתה מתכוון ל'{request.tasks[0].get('title', 'המשימה')}'?",
                        f"בוא נעדכן משימה! האם זו '{request.tasks[0].get('title', 'המשימה')}' שאתה רוצה לשנות?",
                        f"אני יכול לעזור לך לעדכן. האם '{request.tasks[0].get('title', 'המשימה')}' היא המשימה?"
                    ]
                    reply = replies[hash(request.user_id + request.message) % len(replies)]
                else:
                    task_list = ", ".join([t.get("title", "ללא כותרת") for t in request.tasks[:5]])
                    replies = [
                        f"אני מבין שאתה רוצה לעדכן משימה. איזו משימה? יש לך {len(request.tasks)} משימות: {task_list}",
                        f"בוא נעדכן משימה! איזו מהמשימות שלך? ({task_list})",
                        f"אני יכול לעזור לך לעדכן. איזו משימה? הנה המשימות שלך: {task_list}"
                    ]
                    reply = replies[hash(request.user_id + request.message) % len(replies)]
            else:
                # Task identified
                # Rule 8: Check for confirmation
                has_confirmation = False
                if request.conversation_history:
                    for msg in request.conversation_history[-3:]:
                        content_lower = msg.get("content", "").lower()
                        role = msg.get("role", "")
                        if role == "assistant":
                            # Check if confirmation was requested
                            if "אישור" in content_lower or "confirm" in content_lower or "מוכן" in content_lower or "ready" in content_lower:
                                # Next user message should be confirmation
                                pass
                        elif role == "user":
                            # Check if user confirmed
                            confirm_keywords = ["כן", "yes", "אשר", "confirm", "מוכן", "ok", "אוקיי", "ready"]
                            if any(keyword in content_lower for keyword in confirm_keywords):
                                has_confirmation = True
                
                # Check conversation history for collected fields
                has_title = False
                has_priority = False
                has_deadline_asked = False
                
                if request.conversation_history:
                    for msg in request.conversation_history[-5:]:
                        content_lower = msg.get("content", "").lower()
                        role = msg.get("role", "")
                        if role == "user":
                            if any(len(word) > 3 for word in content_lower.split()):
                                has_title = True
                            if any(priority_word in content_lower for priority_word in ["low", "medium", "high", "urgent", "נמוכה", "בינונית", "גבוהה", "דחופה"]):
                                has_priority = True
                        elif role == "assistant":
                            if "תאריך" in content_lower or "יעד" in content_lower:
                                has_deadline_asked = True
                
                if not has_title:
                    replies = [
                        "מעולה! מה הכותרת החדשה של המשימה? (או תגיד 'להשאיר' אם לא רוצה לשנות)",
                        "בוא נעדכן! מה הכותרת? (או 'להשאיר' אם לא רוצה לשנות)",
                        "אני יכול לעזור לך לעדכן. מה הכותרת החדשה? (או 'להשאיר' אם לא רוצה לשנות)"
                    ]
                    reply = replies[hash(request.user_id + request.message) % len(replies)]
                elif not has_priority:
                    replies = [
                        "טוב! מה העדיפות החדשה? (נמוכה/בינונית/גבוהה/דחופה)",
                        "מעולה! מה העדיפות? (נמוכה/בינונית/גבוהה/דחופה)",
                        "נהדר! מה העדיפות החדשה? (נמוכה/בינונית/גבוהה/דחופה)"
                    ]
                    reply = replies[hash(request.user_id + request.message) % len(replies)]
                elif not has_deadline_asked:
                    replies = [
                        "מצוין! האם יש תאריך יעד חדש? (אם לא, פשוט תגיד 'לא' או 'אין')",
                        "טוב! האם יש תאריך יעד? (אם לא, תגיד 'לא')",
                        "נהדר! האם יש תאריך יעד חדש? (אם לא, תגיד 'אין')"
                    ]
                    reply = replies[hash(request.user_id + request.message) % len(replies)]
                elif not has_confirmation:
                    # Rule 8: Final step - ask for confirmation
                    replies = [
                        "מעולה! אני מוכן לעדכן את המשימה. האם אתה מוכן? (כן/לא)",
                        "טוב! אני מוכן לעדכן. האם אתה מוכן? (כן/לא)",
                        "נהדר! אני מוכן לעדכן את המשימה. האם אתה מוכן? (כן/לא)"
                    ]
                    reply = replies[hash(request.user_id + request.message) % len(replies)]
                else:
                    # Confirmation received - this should trigger LLM to set ready=true
                    reply = "מעולה! אני מעדכן את המשימה עכשיו..."
            suggestions = ["שנה עדיפות", "שנה תאריך יעד", "שנה סטטוס"] if not has_confirmation else []
        else:
            if not task_mentioned:
                if len(request.tasks) == 1:
                    replies = [
                        f"I understand you want to update a task. Do you mean '{request.tasks[0].get('title', 'the task')}'?",
                        f"Let's update a task! Is '{request.tasks[0].get('title', 'the task')}' the one you want to change?",
                        f"I can help you update. Is '{request.tasks[0].get('title', 'the task')}' the task?"
                    ]
                    reply = replies[hash(request.user_id + request.message) % len(replies)]
                else:
                    task_list = ", ".join([t.get("title", "Untitled") for t in request.tasks[:5]])
                    replies = [
                        f"I understand you want to update a task. Which task? You have {len(request.tasks)} tasks: {task_list}",
                        f"Let's update a task! Which one? ({task_list})",
                        f"I can help you update. Which task? Here are your tasks: {task_list}"
                    ]
                    reply = replies[hash(request.user_id + request.message) % len(replies)]
            else:
                # Task identified
                # Rule 8: Check for confirmation
                has_confirmation = False
                if request.conversation_history:
                    for msg in request.conversation_history[-3:]:
                        content_lower = msg.get("content", "").lower()
                        role = msg.get("role", "")
                        if role == "assistant":
                            # Check if confirmation was requested
                            if "confirm" in content_lower or "ready" in content_lower:
                                # Next user message should be confirmation
                                pass
                        elif role == "user":
                            # Check if user confirmed
                            confirm_keywords = ["yes", "confirm", "ok", "okay", "ready"]
                            if any(keyword in content_lower for keyword in confirm_keywords):
                                has_confirmation = True
                
                # Check conversation history for collected fields
                has_title = False
                has_priority = False
                has_deadline_asked = False
                
                if request.conversation_history:
                    for msg in request.conversation_history[-5:]:
                        content_lower = msg.get("content", "").lower()
                        role = msg.get("role", "")
                        if role == "user":
                            if any(len(word) > 3 for word in content_lower.split()):
                                has_title = True
                            if any(priority_word in content_lower for priority_word in ["low", "medium", "high", "urgent"]):
                                has_priority = True
                        elif role == "assistant":
                            if "deadline" in content_lower:
                                has_deadline_asked = True
                
                if not has_title:
                    replies = [
                        "Great! What's the new title for the task? (or say 'keep' if you don't want to change it)",
                        "Let's update! What's the title? (or 'keep' if you don't want to change)",
                        "I can help you update. What's the new title? (or 'keep' if you don't want to change)"
                    ]
                    reply = replies[hash(request.user_id + request.message) % len(replies)]
                elif not has_priority:
                    replies = [
                        "Good! What's the new priority? (low/medium/high/urgent)",
                        "Perfect! What's the priority? (low/medium/high/urgent)",
                        "Great! What's the new priority? (low/medium/high/urgent)"
                    ]
                    reply = replies[hash(request.user_id + request.message) % len(replies)]
                elif not has_deadline_asked:
                    replies = [
                        "Excellent! Is there a new deadline? (If not, just say 'no' or 'none')",
                        "Good! Is there a deadline? (If not, say 'no')",
                        "Perfect! Is there a new deadline? (If not, say 'none')"
                    ]
                    reply = replies[hash(request.user_id + request.message) % len(replies)]
                elif not has_confirmation:
                    # Rule 8: Final step - ask for confirmation
                    replies = [
                        "Great! I'm ready to update the task. Are you ready? (yes/no)",
                        "Perfect! I'm ready to update. Are you ready? (yes/no)",
                        "Excellent! I'm ready to update the task. Are you ready? (yes/no)"
                    ]
                    reply = replies[hash(request.user_id + request.message) % len(replies)]
                else:
                    # Confirmation received - this should trigger LLM to set ready=true
                    reply = "Great! I'm updating the task now..."
            suggestions = ["Change priority", "Change deadline", "Change status"] if not has_confirmation else []
        
        return ChatResponse(
            reply=reply,
            intent="potential_update",
            suggestions=suggestions
        )

    def _handle_potential_delete(self, request: ChatRequest, is_hebrew: bool = False) -> ChatResponse:
        """Handle potential delete task intent - asks for clarification."""
        if not request.tasks:
            if is_hebrew:
                reply = "אין לך משימות למחוק."
                suggestions = ["צור משימה", "ראה את כל המשימות"]
            else:
                reply = "You don't have any tasks to delete."
                suggestions = ["Create a task", "View all tasks"]
            return ChatResponse(
                reply=reply,
                intent="potential_delete",
                suggestions=suggestions
            )
        
        # Check if task is specified
        message_lower = request.message.lower()
        task_titles = [t.get("title", "").lower() for t in request.tasks]
        task_mentioned = any(title in message_lower for title in task_titles if title)
        
        # Rule 9: Check for confirmation
        has_confirmation = False
        if request.conversation_history:
            for msg in request.conversation_history[-3:]:
                content_lower = msg.get("content", "").lower()
                role = msg.get("role", "")
                if role == "assistant":
                    # Check if confirmation was requested
                    if "אישור" in content_lower or "confirm" in content_lower or "בטוח" in content_lower:
                        # Next user message should be confirmation
                        pass
                elif role == "user":
                    # Check if user confirmed
                    confirm_keywords = ["כן", "yes", "אשר", "confirm", "בטוח", "ok", "אוקיי"]
                    if any(keyword in content_lower for keyword in confirm_keywords):
                        has_confirmation = True
        
        if is_hebrew:
            if not task_mentioned:
                if len(request.tasks) == 1:
                    task = request.tasks[0]
                    task_desc = f"משימה: '{task.get('title', 'ללא כותרת')}', עדיפות: {task.get('priority', 'לא צוין')}, תאריך יעד: {task.get('deadline', 'אין')}"
                    reply = f"אני מבין שאתה רוצה למחוק משימה. האם אתה מתכוון ל'{task.get('title', 'המשימה')}'?\n{task_desc}\nזה ימחק את המשימה לצמיתות."
                else:
                    reply = f"אני מבין שאתה רוצה למחוק משימה. איזו משימה? יש לך {len(request.tasks)} משימות. אנא ציין את שם המשימה."
                    task_list = ", ".join([t.get("title", "ללא כותרת") for t in request.tasks[:5]])
                    reply += f" המשימות שלך: {task_list}"
            elif not has_confirmation:
                # Task identified, present description and ask for confirmation (Rule 9)
                task = None
                for t in request.tasks:
                    if t.get("title", "").lower() in message_lower:
                        task = t
                        break
                if task:
                    task_desc = f"משימה: '{task.get('title', 'ללא כותרת')}', עדיפות: {task.get('priority', 'לא צוין')}, תאריך יעד: {task.get('deadline', 'אין')}"
                    reply = f"אני מבין שאתה רוצה למחוק משימה.\n{task_desc}\nזה ימחק את המשימה לצמיתות. האם אתה בטוח? (כן/לא)"
                else:
                    reply = "אני מבין שאתה רוצה למחוק משימה. זה ימחק את המשימה לצמיתות. האם אתה בטוח? (כן/לא)"
            else:
                # Confirmation received, ready to delete
                reply = "ממתין למחיקה..."
            suggestions = ["אשר מחיקה", "בטל", "ראה את כל המשימות"] if not has_confirmation else []
        else:
            if not task_mentioned:
                if len(request.tasks) == 1:
                    task = request.tasks[0]
                    task_desc = f"Task: '{task.get('title', 'Untitled')}', Priority: {task.get('priority', 'Not specified')}, Deadline: {task.get('deadline', 'None')}"
                    reply = f"I understand you want to delete a task. Do you mean '{task.get('title', 'the task')}'?\n{task_desc}\nThis will permanently delete the task."
                else:
                    reply = f"I understand you want to delete a task. Which task? You have {len(request.tasks)} tasks. Please specify the task name."
                    task_list = ", ".join([t.get("title", "Untitled") for t in request.tasks[:5]])
                    reply += f" Your tasks: {task_list}"
            elif not has_confirmation:
                # Task identified, present description and ask for confirmation (Rule 9)
                task = None
                for t in request.tasks:
                    if t.get("title", "").lower() in message_lower:
                        task = t
                        break
                if task:
                    task_desc = f"Task: '{task.get('title', 'Untitled')}', Priority: {task.get('priority', 'Not specified')}, Deadline: {task.get('deadline', 'None')}"
                    reply = f"I understand you want to delete a task.\n{task_desc}\nThis will permanently delete the task. Are you sure? (yes/no)"
                else:
                    reply = "I understand you want to delete a task. This will permanently delete the task. Are you sure? (yes/no)"
            else:
                # Confirmation received, ready to delete
                reply = "Waiting for deletion..."
            suggestions = ["Confirm deletion", "Cancel", "View all tasks"] if not has_confirmation else []
        
        return ChatResponse(
            reply=reply,
            intent="potential_delete",
            suggestions=suggestions
        )

    def _handle_help(self, is_hebrew: bool = False) -> ChatResponse:
        """Handle help intent."""
        if is_hebrew:
            reply = "אני יכול לעזור לך עם: רשימת משימות, יצירת משימות, צפייה בסיכומים שבועיים, וענה על שאלות על המשימות שלך. מה תרצה לעשות?"
            suggestions = ["רשימת משימות", "צור משימה", "הצג סיכום"]
        else:
            reply = "I can help you with: listing tasks, creating tasks, viewing weekly summaries, and answering questions about your tasks. What would you like to do?"
            suggestions = ["List tasks", "Create task", "View summary"]
        
        return ChatResponse(
            reply=reply,
            intent="unknown",
            suggestions=suggestions
        )

    def _handle_general(self, request: ChatRequest, is_hebrew: bool = False) -> ChatResponse:
        """Handle general/unclear messages."""
        if is_hebrew:
            reply = "אני כאן כדי לעזור לך לנהל את המשימות שלך. אתה יכול לבקש ממני לרשום משימות, ליצור חדשות, או לראות את הסיכום השבועי שלך. מה תרצה לעשות?"
            suggestions = ["רשימת משימות", "צור משימה", "קבל עזרה"]
        else:
            reply = "I'm here to help you manage your tasks. You can ask me to list tasks, create new ones, or view your weekly summary. What would you like to do?"
            suggestions = ["List tasks", "Create task", "Get help"]
        
        return ChatResponse(
            reply=reply,
            intent="unknown",
            suggestions=suggestions
        )

    def _build_prompt(self, request: ChatRequest) -> str:
        """
        Build prompt for LLM based on user message and context.
        
        Args:
            request: Chat request with message and context data
        
        Returns:
            Formatted prompt string
        """
        prompt_parts = [
            "You are a helpful assistant for TaskGenius, a task management system.",
            "",
            "YOUR ROLE:",
            "- Help users manage their tasks by understanding their intent",
            "- Ask for clarification when information is missing or ambiguous",
            "- Refer to specific tasks when relevant (use task titles, deadlines, priorities)",
            "- Be aware of task context: deadlines, priorities, statuses",
            "- NEVER assume or guess - always ask if unclear",
            "- REMEMBER previous conversation context - users may continue previous requests",
            "",
        ]
        
        # Add conversation history if available
        if request.conversation_history:
            prompt_parts.append("CONVERSATION HISTORY (IMPORTANT - USE THIS CONTEXT):")
            # Limit to last 10 messages to avoid token limits
            recent_history = request.conversation_history[-10:]
            
            # Check if last assistant message was a completion confirmation
            last_assistant_was_completion = False
            if recent_history:
                last_msg = recent_history[-1]
                if last_msg.get("role") == "assistant":
                    last_content = last_msg.get("content", "").lower()
                    # Check for completion indicators
                    completion_indicators = [
                        "✅", "הוספתי", "עדכנתי", "מחקתי", "added", "updated", "deleted",
                        "created", "completed", "done", "finished", "successfully"
                    ]
                    if any(indicator in last_content for indicator in completion_indicators):
                        last_assistant_was_completion = True
            
            for msg in recent_history:
                role = msg.get("role", "unknown")
                content = msg.get("content", "")
                if role == "user":
                    prompt_parts.append(f"User: {content}")
                elif role == "assistant":
                    prompt_parts.append(f"Assistant: {content}")
            prompt_parts.append("")
            
            if last_assistant_was_completion:
                prompt_parts.append("⚠️ CRITICAL: The last assistant message was a COMPLETION CONFIRMATION (task was added/updated/deleted).")
                prompt_parts.append("This means the previous transaction is FINISHED. The user's current message is likely a NEW request.")
                prompt_parts.append("DO NOT continue the old transaction. Treat the user's current message as a fresh start.")
                prompt_parts.append("If the user asks a new question or wants to do something different, respond to the NEW request.")
                prompt_parts.append("IMPORTANT: When answering questions about tasks, use the CURRENT TASKS LIST above (from database), NOT the conversation history.")
                prompt_parts.append("The tasks list is always up-to-date and reflects the current state after the completed operation.")
                prompt_parts.append("Only use the conversation history for general context, NOT to continue the completed transaction or to get task data.")
                prompt_parts.append("")
            else:
                prompt_parts.append("CRITICAL: The user's current message may be a continuation of the conversation above.")
                prompt_parts.append("For example, if you asked 'What priority?' and the user responds 'medium', they are answering your question.")
                prompt_parts.append("Extract information from BOTH the current message AND the conversation history.")
                prompt_parts.append("")
                prompt_parts.append("IMPORTANT: When answering questions about tasks (e.g., 'what tasks do I have?', 'what's due tomorrow?'),")
                prompt_parts.append("ALWAYS use the CURRENT TASKS LIST above (from database), NOT the conversation history.")
                prompt_parts.append("The tasks list is always the most up-to-date source of truth.")
                prompt_parts.append("")
        
        prompt_parts.append(f"User's CURRENT message: {request.message}")
        prompt_parts.append("")
        
        # Add tasks context
        if request.tasks:
            prompt_parts.append("=" * 50)
            prompt_parts.append("CURRENT USER TASKS (ALWAYS UP-TO-DATE - USE THIS DATA, NOT HISTORY):")
            prompt_parts.append("=" * 50)
            prompt_parts.append("⚠️ CRITICAL: The tasks listed below are ALWAYS the most current data from the database.")
            prompt_parts.append("If the conversation history mentions tasks that differ from this list, TRUST THIS LIST.")
            prompt_parts.append("After a task is created/updated/deleted, this list reflects the current state.")
            prompt_parts.append("When answering questions about tasks, ALWAYS use this list, not the conversation history.")
            prompt_parts.append("")
            for task in request.tasks[:10]:  # Limit to 10 tasks
                title = task.get("title", "Untitled")
                status = task.get("status", "unknown")
                priority = task.get("priority", "unknown")
                deadline = task.get("deadline", "No deadline")
                task_id = task.get("id", "unknown")
                prompt_parts.append(f"  - {title} (ID: {task_id}, Status: {status}, Priority: {priority}, Deadline: {deadline})")
            if len(request.tasks) > 10:
                prompt_parts.append(f"  ... and {len(request.tasks) - 10} more tasks")
            prompt_parts.append("")
            prompt_parts.append("IMPORTANT: When the user mentions tasks, refer to them by title from THIS LIST. If they mention 'tomorrow', 'urgent', 'high priority', etc., filter the tasks from THIS LIST accordingly.")
            prompt_parts.append("=" * 50)
            prompt_parts.append("")
        else:
            prompt_parts.append("User's tasks: None (user has no tasks yet)")
            prompt_parts.append("")
        
        # Add weekly summary if available
        if request.weekly_summary:
            summary = request.weekly_summary
            prompt_parts.append("Weekly summary:")
            completed = summary.get("completed", {}).get("count", 0)
            high_priority = summary.get("high_priority", {}).get("count", 0)
            upcoming = summary.get("upcoming", {}).get("count", 0)
            overdue = summary.get("overdue", {}).get("count", 0)
            prompt_parts.append(f"  - Completed: {completed}")
            prompt_parts.append(f"  - High priority: {high_priority}")
            prompt_parts.append(f"  - Upcoming: {upcoming}")
            prompt_parts.append(f"  - Overdue: {overdue}")
            prompt_parts.append("")
        
        prompt_parts.append("INTENT DETECTION & CLARIFICATION RULES:")
        prompt_parts.append("- If user wants to CREATE a task but didn't provide title → ask: 'What task would you like to create? Please provide a title.'")
        prompt_parts.append("- If user wants to UPDATE/DELETE but task is ambiguous (e.g., 'tomorrow's task' when multiple exist) → list the matching tasks and ask which one")
        prompt_parts.append("- If user mentions urgency/priority/deadline but it's unclear → ask for clarification")
        prompt_parts.append("- If user asks about 'urgent' or 'high priority' tasks → refer to actual high-priority tasks from the list above")
        prompt_parts.append("- If user asks 'what's due' or 'what's coming' → refer to tasks with upcoming deadlines")
        prompt_parts.append("- NEVER guess or assume - always ask if information is missing or ambiguous")
        prompt_parts.append("")
        prompt_parts.append("INTENT TYPES (use these in your reasoning):")
        prompt_parts.append("- 'list_tasks' - user wants to see their tasks")
        prompt_parts.append("- 'task_insights' - user wants insights about tasks (deadlines, priorities, urgency)")
        prompt_parts.append("- 'potential_create' - user wants to create a task but information is incomplete")
        prompt_parts.append("- 'potential_update' - user wants to update a task but target is unclear")
        prompt_parts.append("- 'potential_delete' - user wants to delete a task but target is unclear")
        prompt_parts.append("")
        prompt_parts.append("OUTPUT FORMAT (Phase 3 - Structured Output):")
        prompt_parts.append("You must respond with TWO SEPARATE parts:")
        prompt_parts.append("1. A natural conversational reply (for the user) - NO JSON, NO CODE, ONLY NATURAL TEXT")
        prompt_parts.append("2. A JSON command object (for the system)")
        prompt_parts.append("")
        prompt_parts.append("Format your response EXACTLY as:")
        prompt_parts.append("REPLY: [your natural conversational response - ONLY TEXT, NO JSON, NO CODE]")
        prompt_parts.append("COMMAND: [JSON object with command structure]")
        prompt_parts.append("")
        prompt_parts.append("CRITICAL OUTPUT RULES:")
        prompt_parts.append("- The REPLY section MUST contain ONLY natural conversational text")
        prompt_parts.append("- DO NOT include JSON, code blocks, or any structured data in the REPLY section")
        prompt_parts.append("- DO NOT repeat the command structure in the REPLY section")
        prompt_parts.append("- The REPLY is what the user will see - keep it clean and natural")
        prompt_parts.append("- The COMMAND section is separate and only for the system")
        prompt_parts.append("- If you include JSON in REPLY, it will confuse the user - NEVER do this")
        prompt_parts.append("")
        prompt_parts.append("COMMAND JSON Structure:")
        prompt_parts.append("{")
        prompt_parts.append('  "intent": "add_task|update_task|delete_task|complete_task|list_tasks|clarify",')
        prompt_parts.append('  "confidence": 0.0-1.0,  // High (>=0.8) only when all required fields are clear')
        prompt_parts.append('  "fields": {  // For add_task: title, priority, deadline, etc.')
        prompt_parts.append('    "title": "string or null",')
        prompt_parts.append('    "priority": "low|medium|high|urgent or null",')
        prompt_parts.append('    "deadline": "ISO date string or null"')
        prompt_parts.append('  },')
        prompt_parts.append('  "ref": {  // For update/delete/complete: task reference')
        prompt_parts.append('    "task_id": "string or null",')
        prompt_parts.append('    "title": "string or null"  // For matching')
        prompt_parts.append('  },')
        prompt_parts.append('  "ready": true/false,  // true only when all required fields are present')
        prompt_parts.append('  "missing_fields": ["field1", "field2"]  // List missing required fields')
        prompt_parts.append("}")
        prompt_parts.append("")
        prompt_parts.append("DATE/DEADLINE HANDLING RULES (CRITICAL - MUST FOLLOW):")
        prompt_parts.append("- When user provides a date/deadline, try to understand it (e.g., 'tomorrow', 'יום רביעי', '20.1', '2024-01-20')")
        prompt_parts.append("- If user says 'no', 'none', 'אין', or 'לא' when asked about deadline → set deadline to null (no deadline)")
        prompt_parts.append("- CRITICAL: If user provides ANYTHING ELSE that is NOT 'no'/'none'/'אין'/'לא' AND is NOT a clear, valid date,")
        prompt_parts.append("  DO NOT guess or use default dates. DO NOT use old dates (e.g., 2023, 25/10/2023).")
        prompt_parts.append("  DO NOT try to interpret unclear text as a date.")
        prompt_parts.append("  Instead, in your REPLY, ask the user: 'אנא תן תאריך במספרים (למשל: 2024-01-20 או 20.1.2024), או כתוב 'לא' אם אין תאריך יעד'")
        prompt_parts.append("  (or in English: 'Please provide a date in numbers (e.g., 2024-01-20 or 20.1.2024), or write 'no' if there's no deadline')")
        prompt_parts.append("  In the COMMAND, set deadline to null and set ready=false with 'deadline' in missing_fields.")
        prompt_parts.append("- NEVER use dates from years ago (e.g., 2023, 25/10/2023) - these are invalid and will be rejected by the system.")
        prompt_parts.append("- NEVER use default/placeholder dates - only use dates explicitly provided by the user in a clear format.")
        prompt_parts.append("- Example: If user says 'יום רביעי' and you're not sure which Wednesday, ask: 'איזה יום רביעי? אנא תן תאריך במספרים (למשל: 20.1.2024)'")
        prompt_parts.append("- Example: If user says 'tomorrow' but context is unclear, ask: 'What date is tomorrow? Please provide the date in numbers (e.g., 2024-01-20)'")
        prompt_parts.append("- Example: If user writes something unclear like 'maybe next week' or 'I don't know' (not 'no'/'none' and not a clear date),")
        prompt_parts.append("  ask: 'אנא תן תאריך במספרים (למשל: 2024-01-20), או כתוב 'לא' אם אין תאריך יעד'")
        prompt_parts.append("  (or in English: 'Please provide a date in numbers (e.g., 2024-01-20), or write 'no' if there's no deadline')")
        prompt_parts.append("")
        prompt_parts.append("RULES FOR COMMAND GENERATION:")
        prompt_parts.append("- For 'add_task': Set ready=true ONLY if BOTH title AND priority are provided. confidence>=0.8 only if both are clear.")
        prompt_parts.append("  REQUIRED FIELDS for add_task: title (mandatory), priority (mandatory), deadline (optional - ask but can be null)")
        prompt_parts.append("  WORKFLOW (MUST FOLLOW THIS ORDER - ONE STEP AT A TIME):")
        prompt_parts.append("    1) FIRST: Ask for title ONLY (e.g., 'What task would you like to create? Please provide a title.')")
        prompt_parts.append("    2) SECOND: After user provides title, ask for priority ONLY (e.g., 'What's the priority? (low/medium/high/urgent)')")
        prompt_parts.append("    3) THIRD: After user provides priority, ask for deadline ONLY (e.g., 'Is there a deadline? (If not, say 'no' or 'none')')")
        prompt_parts.append("    4) FINAL: Execute when title+priority are ready (deadline can be null)")
        prompt_parts.append("  CRITICAL: DO NOT ask for multiple fields at once. Ask ONE field at a time, wait for user response, then ask the next field.")
        prompt_parts.append("  CRITICAL: Check conversation history to see what was already asked. If title was asked but not provided, ask for title again.")
        prompt_parts.append("  CRITICAL: If user provides multiple fields at once (e.g., 'add task buy milk high priority'), extract all fields but still follow the workflow order in your reply.")
        prompt_parts.append("- For 'update_task': Set ready=true ONLY if task is unambiguous AND title AND priority are provided/confirmed AND user explicitly confirmed (said 'yes'/'כן'/'confirm').")
        prompt_parts.append("  REQUIRED FIELDS for update_task:")
        prompt_parts.append("    - ref.task_id OR ref.title (mandatory - must identify which task to update)")
        prompt_parts.append("    - fields.title (mandatory - new title)")
        prompt_parts.append("    - fields.priority (mandatory - new priority)")
        prompt_parts.append("    - fields.deadline (optional - ask but can be null)")
        prompt_parts.append("  WORKFLOW (MUST FOLLOW THIS ORDER - ONE STEP AT A TIME):")
        prompt_parts.append("    1) FIRST: Identify which task to update (ask if unclear)")
        prompt_parts.append("    2) SECOND: Ask for new title (or confirm existing)")
        prompt_parts.append("    3) THIRD: Ask for new priority")
        prompt_parts.append("    4) FOURTH: Ask for deadline (can skip)")
        prompt_parts.append("    5) FIFTH: Ask for confirmation (e.g., 'Are you ready to update? (yes/no)')")
        prompt_parts.append("    6) FINAL: Execute ONLY after explicit confirmation")
        prompt_parts.append("  CRITICAL: DO NOT ask for multiple fields at once. Ask ONE field at a time, wait for user response, then ask the next field.")
        prompt_parts.append("  CRITICAL: If the assistant asked 'Are you ready?' or 'Confirm update?' and user replied 'yes'/'כן'/'confirm', then:")
        prompt_parts.append("    - Set intent='update_task' (NOT 'potential_update')")
        prompt_parts.append("    - Set ready=true")
        prompt_parts.append("    - Set ref.task_id or ref.title to identify the task")
        prompt_parts.append("    - Set fields.title and fields.priority with the new values")
        prompt_parts.append("- For 'delete_task': Set ready=true ONLY if task is unambiguous AND user explicitly confirmed (said 'yes'/'כן'/'ok'/'אוקיי').")
        prompt_parts.append("  REQUIRED for delete_task:")
        prompt_parts.append("    - ref.task_id OR ref.title (mandatory - must identify which task to delete)")
        prompt_parts.append("    - User explicit confirmation (mandatory - user must say 'yes'/'כן'/'ok'/'אוקיי' after being asked)")
        prompt_parts.append("  WORKFLOW: 1) Identify task → 2) Present task description → 3) Ask for confirmation → 4) Execute ONLY after explicit confirmation")
        prompt_parts.append("  CRITICAL: If the assistant asked 'Are you sure?' or 'בטוח?' and user replied 'yes'/'כן'/'ok'/'אוקיי', then:")
        prompt_parts.append("    - Set intent='delete_task' (NOT 'potential_delete')")
        prompt_parts.append("    - Set ready=true")
        prompt_parts.append("    - Set ref.task_id or ref.title to identify the task")
        prompt_parts.append("  CRITICAL: If user wrote something else (not 'yes'/'כן'/'ok'/'אוקיי'), set ready=false and clear history.")
        prompt_parts.append("- For 'complete_task': Set ready=true ONLY if task is unambiguous. confidence>=0.8 only if task reference is clear.")
        prompt_parts.append("- If information is missing or ambiguous → set ready=false, confidence<0.8, and list missing_fields")
        prompt_parts.append("- Extract fields progressively from the conversation (title, priority, deadline, etc.)")
        prompt_parts.append("- NEVER set ready=true if required fields (title, priority) are missing")
        prompt_parts.append("- ALWAYS ask about deadline as the final step before execution (user can say 'no' or 'skip' to set it as null)")
        prompt_parts.append("")
        prompt_parts.append("CONFIDENCE CALCULATION (CRITICAL - MUST BE A NUMBER 0.0-1.0):")
        prompt_parts.append("- confidence MUST be a number between 0.0 and 1.0 (e.g., 0.8, 0.9, 0.5)")
        prompt_parts.append("- DO NOT use strings like 'A A' or 'high' - ONLY use numbers")
        prompt_parts.append("- High confidence (>=0.8): All required information is clear and unambiguous")
        prompt_parts.append("- Medium confidence (0.5-0.7): Some information is present but incomplete or ambiguous")
        prompt_parts.append("- Low confidence (<0.5): Information is missing or very unclear")
        prompt_parts.append("- Example: If user says 'add task buy milk' → confidence=0.9 (title is clear)")
        prompt_parts.append("- Example: If user says 'add task' → confidence=0.3 (title is missing)")
        prompt_parts.append("- Example: If user says 'medium' after you asked 'what priority?' → confidence=0.8 (answering your question)")
        prompt_parts.append("")
        prompt_parts.append("Generate a helpful, conversational response. Be concise and friendly.")
        prompt_parts.append("Respond naturally as if you're helping the user manage their tasks.")
        prompt_parts.append("")
        prompt_parts.append("=" * 50)
        prompt_parts.append("CRITICAL LANGUAGE INSTRUCTIONS:")
        prompt_parts.append("=" * 50)
        prompt_parts.append("1. The user may write in Hebrew (עברית), English, or mix both languages.")
        prompt_parts.append("2. You MUST respond in the EXACT same language(s) the user used.")
        prompt_parts.append("3. If the user writes in Hebrew → respond in Hebrew.")
        prompt_parts.append("4. If the user writes in English → respond in English.")
        prompt_parts.append("5. Understand Hebrew slang, informal expressions, and common phrases.")
        prompt_parts.append("6. Examples of Hebrew you should understand:")
        prompt_parts.append("   - 'מה המשימות שלי?' = 'What are my tasks?'")
        prompt_parts.append("   - 'תוסיף משימה' = 'Add a task'")
        prompt_parts.append("   - 'מה דחוף לי?' = 'What's urgent for me?'")
        prompt_parts.append("   - 'סמן כבוצע' = 'Mark as done'")
        prompt_parts.append("   - 'תראה לי סיכום שבועי' = 'Show me weekly summary'")
        prompt_parts.append("7. DO NOT translate Hebrew to English in your response.")
        prompt_parts.append("8. DO NOT respond in English if the user wrote in Hebrew.")
        prompt_parts.append("=" * 50)
        
        return "\n".join(prompt_parts)

    async def _generate_llm_response(self, request: ChatRequest) -> Optional[ChatResponse]:
        """
        Generate response using LLM (OpenAI).
        
        Args:
            request: Chat request with message and context data
        
        Returns:
            ChatResponse if successful, None if failed
        """
        if not self._openai_client:
            return None
        
        try:
            # Build prompt
            prompt = self._build_prompt(request)
            
            logger.debug(f"Sending request to OpenAI (model: {settings.MODEL_NAME})")
            
            # Call OpenAI API
            response = await self._openai_client.chat.completions.create(
                model=settings.MODEL_NAME,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful assistant for TaskGenius, a task management system. Provide concise, friendly responses.\n\nYOUR CORE RESPONSIBILITIES:\n1. Understand user intent (create/update/delete/list/insights)\n2. Ask for clarification when information is missing or ambiguous\n3. Refer to specific tasks when relevant (use task titles, deadlines, priorities)\n4. Be aware of task context (deadlines, priorities, statuses)\n5. NEVER assume or guess - always ask if unclear\n\nCRITICAL LANGUAGE RULES:\n- You MUST support Hebrew (עברית) and English\n- If the user writes in Hebrew, you MUST respond in Hebrew\n- If the user writes in English, respond in English\n- If the user mixes languages, respond in the same mix\n- Understand Hebrew slang, informal expressions, and common phrases\n- Examples of Hebrew task management phrases:\n  * 'מה המשימות שלי?' = 'What are my tasks?'\n  * 'תוסיף משימה' = 'Add a task'\n  * 'מה דחוף לי?' = 'What's urgent for me?'\n  * 'סמן כבוצע' = 'Mark as done'\n- Always match the user's language preference"
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.7,
                max_tokens=300,
                timeout=settings.LLM_TIMEOUT,
            )
            
            # Extract reply and command from response
            content = response.choices[0].message.content.strip()
            
            if not content:
                logger.warning("Empty reply from LLM")
                return None
            
            # Parse structured output (Phase 3)
            reply, command = self._parse_llm_response(content, request)
            
            if not reply:
                logger.warning("Could not extract reply from LLM response")
                return None
            
            # Determine intent from original message (more reliable than extracting from reply)
            # Use the original message to detect intent, as it's more accurate
            intent = self._extract_intent_from_message(request.message, request)
            
            # Generate suggestions based on intent
            suggestions = self._generate_suggestions(intent, request)
            
            return ChatResponse(
                reply=reply,
                intent=intent,
                suggestions=suggestions,
                command=command
            )
            
        except Exception as e:
            logger.error(f"Error calling OpenAI API: {e}", exc_info=True)
            return None

    def _validate_deadline_format(self, deadline: Optional[str]) -> tuple[bool, Optional[str]]:
        """
        Validate deadline format (Rule 1, 3).
        
        Returns:
            (is_valid, normalized_iso_string_or_none)
            - is_valid: True if deadline is either None, explicit "none", or valid ISO date
            - normalized: ISO date string or None
        """
        from datetime import datetime, timezone, timedelta
        
        if not deadline:
            return (True, None)
        
        deadline_lower = deadline.lower().strip()
        
        # Check for explicit "none" keywords
        none_keywords = ["none", "no", "אין", "לא", "null", "skip"]
        if deadline_lower in none_keywords:
            return (True, None)
        
        # CRITICAL: Check for old dates (e.g., 2023, 25/10/2023) - reject them as invalid
        # This prevents using default/old dates when user didn't provide a clear date
        # Specifically check for the problematic date 25/10/2023
        if "2023" in deadline or "2022" in deadline or "2021" in deadline:
            logger.warning(f"Rejecting old date: {deadline}")
            return (False, None)
        # CRITICAL: Specifically reject 25/10/2023 and 2023-10-25 (common default date)
        if "25/10/2023" in deadline or "2023-10-25" in deadline or "25-10-2023" in deadline:
            logger.warning(f"Rejecting problematic default date: {deadline}")
            return (False, None)
        
        now = datetime.now(timezone.utc)
        
        # Try to parse as ISO date
        try:
            # Try ISO format
            parsed = datetime.fromisoformat(deadline.replace("Z", "+00:00"))
            # CRITICAL: Check if date is in the past (more than 1 year ago) or too old
            # Reject dates older than 1 year (likely default/old dates)
            # Only reject if the date is actually in the past (more than 1 year old), not just old years
            if parsed < now - timedelta(days=365):
                logger.warning(f"Rejecting date too old: {deadline} (year: {parsed.year})")
                return (False, None)
            # Return normalized ISO string
            return (True, parsed.isoformat())
        except (ValueError, AttributeError):
            pass
        
        # Try to parse common date formats (DD/MM/YYYY, DD-MM-YYYY, etc.)
        try:
            # Try DD/MM/YYYY or DD-MM-YYYY
            if "/" in deadline or "-" in deadline:
                # Check if it's a date format (has numbers)
                if any(char.isdigit() for char in deadline):
                    # Try parsing with different formats
                    for fmt in ["%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%Y/%m/%d"]:
                        try:
                            parsed = datetime.strptime(deadline.strip(), fmt)
                            # Check if date is too old
                            if parsed.year < now.year - 1:
                                logger.warning(f"Rejecting date too old: {deadline} (year: {parsed.year})")
                                return (False, None)
                            # Return normalized ISO string
                            return (True, parsed.isoformat())
                        except ValueError:
                            continue
        except Exception:
            pass
        
        # If we can't parse, it's invalid
        return (False, None)
    
    def _is_deadline_ambiguous(self, deadline: Optional[str], conversation_history: Optional[List[Dict[str, str]]] = None) -> bool:
        """
        Detect if deadline is ambiguous (Rule 3).
        
        Ambiguous examples: "יום רביעי", "tomorrow" without context, "next week"
        """
        if not deadline:
            return False
        
        deadline_lower = deadline.lower().strip()
        
        # Explicit "none" is not ambiguous
        none_keywords = ["none", "no", "אין", "לא", "null", "skip"]
        if deadline_lower in none_keywords:
            return False
        
        # If it's a valid ISO date, it's not ambiguous
        is_valid, _ = self._validate_deadline_format(deadline)
        if is_valid and deadline:
            # Check if it's ISO format (contains dashes and colons)
            if "-" in deadline and ":" in deadline:
                return False
        
        # Check for ambiguous relative dates (Hebrew and English)
        ambiguous_patterns = [
            "יום", "שבוע", "חודש", "שנה",  # Hebrew: day, week, month, year
            "tomorrow", "yesterday", "today", "next week", "last week",
            "next month", "last month", "next year", "last year",
            "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday",
            "יום ראשון", "יום שני", "יום שלישי", "יום רביעי", "יום חמישי", "יום שישי", "יום שבת"
        ]
        
        for pattern in ambiguous_patterns:
            if pattern in deadline_lower:
                # If we have conversation history, check if context was provided
                if conversation_history:
                    # Check if user provided numeric date in recent messages
                    recent_context = " ".join([msg.get("content", "") for msg in conversation_history[-3:]])
                    # If numeric date found in context, it's less ambiguous
                    if re.search(r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}', recent_context):
                        return False
                return True
        
        # If it's not a clear pattern but also not parseable, it's ambiguous
        return not is_valid
    
    def _was_deadline_asked_last(self, conversation_history: Optional[List[Dict[str, str]]] = None) -> bool:
        """
        Check if deadline was asked in the last assistant message (Rule 2).
        This ensures deadline is the LAST step before CRUD.
        """
        if not conversation_history or len(conversation_history) == 0:
            return False
        
        # Check last assistant message
        last_msg = conversation_history[-1]
        if last_msg.get("role") != "assistant":
            return False
        
        content_lower = last_msg.get("content", "").lower()
        
        # Check if deadline was asked
        deadline_keywords = ["deadline", "תאריך", "יעד", "date", "due date"]
        return any(keyword in content_lower for keyword in deadline_keywords)
    
    def _parse_llm_response(self, content: str, request: ChatRequest) -> tuple[str, Optional[Command]]:
        """
        Parse LLM response to extract reply and command (Phase 3).
        
        Expected format:
        REPLY: [natural text]
        COMMAND: [JSON object]
        
        Returns:
            (reply, command) tuple
        """
        reply = ""
        command = None
        
        # Try to parse structured format
        reply_match = re.search(r'REPLY:\s*(.+?)(?=COMMAND:|$)', content, re.DOTALL | re.IGNORECASE)
        command_match = re.search(r'COMMAND:\s*(\{.*\})', content, re.DOTALL | re.IGNORECASE)
        
        if reply_match:
            reply = reply_match.group(1).strip()
            # Clean up: Remove any JSON objects that might have leaked into the reply
            # This handles cases where LLM includes JSON in the REPLY section
            json_pattern = r'\{[^{}]*"intent"[^{}]*\}'
            reply = re.sub(json_pattern, '', reply, flags=re.DOTALL)
            # Remove any remaining JSON-like structures
            reply = re.sub(r'\{[^{}]*\}', '', reply, flags=re.DOTALL)
            # Clean up extra whitespace
            reply = re.sub(r'\s+', ' ', reply).strip()
        else:
            # Fallback: use entire content as reply, but clean it first
            reply = content
            # Try to remove COMMAND section if it exists
            reply = re.sub(r'COMMAND:\s*\{.*\}', '', reply, flags=re.DOTALL | re.IGNORECASE)
            # Remove any JSON objects
            reply = re.sub(r'\{[^{}]*"intent"[^{}]*\}', '', reply, flags=re.DOTALL)
            reply = re.sub(r'\{[^{}]*\}', '', reply, flags=re.DOTALL)
            reply = re.sub(r'\s+', ' ', reply).strip()
        
        if command_match:
            try:
                command_json = command_match.group(1).strip()
                command_dict = json.loads(command_json)
                
                # Validate and parse confidence (must be a number between 0.0 and 1.0)
                confidence_raw = command_dict.get("confidence", 0.0)
                try:
                    confidence = float(confidence_raw)
                    # Clamp to valid range
                    confidence = max(0.0, min(1.0, confidence))
                except (ValueError, TypeError):
                    logger.warning(f"Invalid confidence value: {confidence_raw}, defaulting to 0.0")
                    confidence = 0.0
                
                # Validate required fields for add_task and update_task
                intent = command_dict.get("intent", "clarify")
                fields = command_dict.get("fields", {})
                ready = command_dict.get("ready", False)
                missing_fields = command_dict.get("missing_fields", [])
                
                # Enforce required fields: title and priority for add_task/update_task
                # CRITICAL: Check conversation history to determine which field should be asked next
                if intent in ["add_task", "update_task"]:
                    # Check conversation history to see what was already asked/collected
                    last_assistant_msg = None
                    if request.conversation_history:
                        for msg in reversed(request.conversation_history[-5:]):
                            if msg.get("role") == "assistant":
                                last_assistant_msg = msg.get("content", "").lower()
                                break
                    
                    # For add_task: Check if fields were collected in order
                    if intent == "add_task":
                        # Check if title is missing
                        if not fields.get("title"):
                            ready = False
                            if "title" not in missing_fields:
                                missing_fields.append("title")
                            # If last assistant message didn't ask for title, it should be asked first
                            if last_assistant_msg and "title" not in last_assistant_msg and "כותרת" not in last_assistant_msg:
                                # Title should be asked first - clear priority if it was set
                                if fields.get("priority"):
                                    fields["priority"] = None
                                    if "priority" in missing_fields:
                                        missing_fields.remove("priority")
                        # Check if priority is missing (only if title is present)
                        elif not fields.get("priority"):
                            ready = False
                            if "priority" not in missing_fields:
                                missing_fields.append("priority")
                            # If last assistant message didn't ask for priority, it should be asked second
                            if last_assistant_msg and "priority" not in last_assistant_msg and "עדיפות" not in last_assistant_msg:
                                # Priority should be asked second - clear deadline if it was set
                                if fields.get("deadline"):
                                    fields["deadline"] = None
                                    if "deadline" in missing_fields:
                                        missing_fields.remove("deadline")
                    
                    # For update_task: Similar logic but with confirmation step
                    elif intent == "update_task":
                        if not fields.get("title"):
                            ready = False
                            if "title" not in missing_fields:
                                missing_fields.append("title")
                        if not fields.get("priority"):
                            ready = False
                            if "priority" not in missing_fields:
                                missing_fields.append("priority")
                    
                    # Rule 8: For update_task, check for explicit confirmation
                    # CRITICAL: Similar to add_task deadline logic - if user didn't write "yes"/"ok"/"כן"/"אוקיי", 
                    # don't execute and clear history (so next commands rely on DB)
                    if intent == "update_task":
                        has_confirmation = False
                        if request.conversation_history:
                            # Check last assistant message for confirmation request
                            last_assistant_msg = None
                            for msg in reversed(request.conversation_history[-5:]):
                                if msg.get("role") == "assistant":
                                    last_assistant_msg = msg.get("content", "").lower()
                                    break
                            
                            if last_assistant_msg and ("confirm" in last_assistant_msg or "ready" in last_assistant_msg or "אישור" in last_assistant_msg or "מוכן" in last_assistant_msg or "בטוח" in last_assistant_msg):
                                # Check if user confirmed in current message
                                message_lower = request.message.lower().strip()
                                confirm_keywords = ["yes", "כן", "confirm", "אשר", "ok", "אוקיי", "ready", "מוכן", "okay"]
                                # CRITICAL: Only accept exact confirmation keywords, not partial matches
                                # This prevents false positives (e.g., "ok" in "look" or "כן" in "כןן")
                                message_words = message_lower.split()
                                has_confirmation = any(keyword in message_words for keyword in confirm_keywords) or message_lower in confirm_keywords
                                
                                if has_confirmation:
                                    # User confirmed - set ready=true if all other fields are present
                                    logger.debug("Update task: User confirmed, setting ready=true if fields are present")
                                    # If title and priority are present, force ready=true
                                    if fields.get("title") and fields.get("priority"):
                                        ready = True
                                        # Force intent to be update_task (not potential_update)
                                        if intent == "potential_update":
                                            intent = "update_task"
                                        # Remove confirmation from missing_fields if it was there
                                        if "confirmation" in missing_fields:
                                            missing_fields.remove("confirmation")
                                else:
                                    # User wrote something else (not "yes"/"ok"/"כן"/"אוקיי")
                                    # Don't execute, but mark as needing history clear (will be handled by frontend)
                                    logger.debug(f"Update task: User wrote '{request.message}' instead of confirmation. Not executing.")
                                    ready = False
                                    # Set intent to indicate this was a non-confirmation response
                                    # Frontend will clear history based on this
                                    if "confirmation" not in missing_fields:
                                        missing_fields.append("confirmation")
                        
                        if not has_confirmation:
                            # No confirmation yet - set ready=false
                            ready = False
                            if "confirmation" not in missing_fields:
                                missing_fields.append("confirmation")
                    
                    # Rule 9: For delete_task, check for explicit confirmation (similar logic)
                    if intent == "delete_task":
                        has_confirmation = False
                        if request.conversation_history:
                            # Check last assistant message for confirmation request
                            last_assistant_msg = None
                            for msg in reversed(request.conversation_history[-5:]):
                                if msg.get("role") == "assistant":
                                    last_assistant_msg = msg.get("content", "").lower()
                                    break
                            
                            if last_assistant_msg and ("confirm" in last_assistant_msg or "בטוח" in last_assistant_msg or "sure" in last_assistant_msg or "אישור" in last_assistant_msg):
                                # Check if user confirmed in current message
                                message_lower = request.message.lower().strip()
                                confirm_keywords = ["yes", "כן", "confirm", "אשר", "ok", "אוקיי", "okay"]
                                # CRITICAL: Only accept exact confirmation keywords
                                message_words = message_lower.split()
                                has_confirmation = any(keyword in message_words for keyword in confirm_keywords) or message_lower in confirm_keywords
                                
                                if has_confirmation:
                                    # User confirmed - set ready=true
                                    logger.debug("Delete task: User confirmed, setting ready=true")
                                    ready = True
                                    # Force intent to be delete_task (not potential_delete)
                                    if intent == "potential_delete":
                                        intent = "delete_task"
                                    # Remove confirmation from missing_fields if it was there
                                    if "confirmation" in missing_fields:
                                        missing_fields.remove("confirmation")
                                else:
                                    # User wrote something else (not "yes"/"ok"/"כן"/"אוקיי")
                                    # Don't execute, but mark as needing history clear
                                    logger.debug(f"Delete task: User wrote '{request.message}' instead of confirmation. Not executing.")
                                    ready = False
                                    if "confirmation" not in missing_fields:
                                        missing_fields.append("confirmation")
                        
                        if not has_confirmation:
                            # No confirmation yet - set ready=false
                            ready = False
                            if "confirmation" not in missing_fields:
                                missing_fields.append("confirmation")
                    
                    # Rule 2: Deadline must be asked as LAST step (only for add_task, or update_task if confirmation already received)
                    # CRITICAL: Only check deadline if priority is already present (for add_task)
                    # Order must be: title → priority → deadline
                    if intent == "add_task":
                        # Only check deadline if priority is already present
                        if fields.get("priority"):
                            deadline = fields.get("deadline")
                            if deadline is not None and deadline != "":
                                # Rule 3: Validate deadline format and clarity
                                is_valid, normalized = self._validate_deadline_format(deadline)
                                is_ambiguous = self._is_deadline_ambiguous(deadline, request.conversation_history)
                                
                                # CRITICAL: Check if user explicitly said "no" or "none" (case-insensitive)
                                deadline_lower = str(deadline).lower().strip()
                                none_keywords = ["none", "no", "אין", "לא", "null", "skip"]
                                is_explicit_none = deadline_lower in none_keywords
                                
                                if is_explicit_none:
                                    # User explicitly said "no" or "none" - set to None
                                    fields["deadline"] = None
                                    # Don't set ready=false for this - deadline is optional
                                elif not is_valid or is_ambiguous:
                                    # Deadline is unclear or invalid (including old dates like 2023)
                                    # Set ready=false and ask for numeric format
                                    ready = False
                                    if "deadline" not in missing_fields:
                                        missing_fields.append("deadline")
                                    # Update fields to None to indicate it needs clarification
                                    fields["deadline"] = None
                                    logger.warning(f"Invalid or ambiguous deadline: {deadline}. Will ask for numeric format.")
                                    # Note: The reply will be generated by LLM based on the prompt instructions
                                    # The prompt explicitly tells LLM to ask for numeric format if date is unclear
                                    # The LLM should respond with: "אנא תן תאריך במספרים (למשל: 2024-01-20), או כתוב 'לא' אם אין תאריך יעד"
                                else:
                                    # Valid and clear - normalize it
                                    fields["deadline"] = normalized
                            else:
                                # Rule 2: Check if deadline was asked as last step (only if priority is present)
                                if not self._was_deadline_asked_last(request.conversation_history):
                                    # Deadline wasn't asked yet - must be asked before ready
                                    ready = False
                                    if "deadline" not in missing_fields:
                                        missing_fields.append("deadline")
                        # If priority is not present, don't check deadline yet (priority must come first)
                        else:
                            # Priority is missing - deadline should not be checked yet
                            if "deadline" in missing_fields:
                                missing_fields.remove("deadline")
                            if fields.get("deadline"):
                                # Clear deadline if it was set before priority
                                fields["deadline"] = None
                    elif intent == "update_task":
                        # For update_task, deadline is optional - only check if confirmation was already received
                        # (deadline check happens before confirmation in the flow)
                        deadline = fields.get("deadline")
                        if deadline is not None and deadline != "":
                            # Rule 3: Validate deadline format and clarity
                            is_valid, normalized = self._validate_deadline_format(deadline)
                            is_ambiguous = self._is_deadline_ambiguous(deadline, request.conversation_history)
                            
                            # CRITICAL: Check if user explicitly said "no" or "none" (case-insensitive)
                            deadline_lower = str(deadline).lower().strip()
                            none_keywords = ["none", "no", "אין", "לא", "null", "skip"]
                            is_explicit_none = deadline_lower in none_keywords
                            
                            if is_explicit_none:
                                # User explicitly said "no" or "none" - set to None
                                fields["deadline"] = None
                                # Don't set ready=false for this - deadline is optional
                            elif not is_valid or is_ambiguous:
                                # Deadline is unclear or invalid (including old dates like 2023)
                                # Set ready=false and ask for numeric format
                                ready = False
                                if "deadline" not in missing_fields:
                                    missing_fields.append("deadline")
                                # Update fields to None to indicate it needs clarification
                                fields["deadline"] = None
                                logger.warning(f"Invalid or ambiguous deadline: {deadline}. Will ask for numeric format.")
                            else:
                                # Valid and clear - normalize it
                                fields["deadline"] = normalized
                
                # For update_task, ensure ref is set (extract from conversation if missing)
                ref = command_dict.get("ref")
                if intent == "update_task" and not ref:
                    # Try to extract task reference from conversation history
                    if request.conversation_history and request.tasks:
                        # Look for task title in recent messages
                        for msg in reversed(request.conversation_history[-10:]):
                            content = msg.get("content", "")
                            for task in request.tasks:
                                task_title = task.get("title", "")
                                if task_title and task_title.lower() in content.lower():
                                    ref = {"task_id": task.get("id"), "title": task_title}
                                    logger.debug(f"Extracted task ref from conversation: {ref}")
                                    break
                            if ref:
                                break
                
                # Create Command object
                command = Command(
                    intent=intent,
                    confidence=confidence,
                    fields=fields,
                    ref=ref,
                    filter=command_dict.get("filter"),
                    ready=ready,
                    missing_fields=missing_fields if missing_fields else None
                )
                logger.debug(f"Parsed command: intent={command.intent}, confidence={command.confidence}, ready={command.ready}, missing_fields={command.missing_fields}")
            except (json.JSONDecodeError, KeyError, ValueError) as e:
                logger.warning(f"Failed to parse command JSON: {e}")
                # Continue without command - backward compatible
        
        return reply, command

    def _extract_intent_from_message(self, message: str, request: ChatRequest) -> Optional[str]:
        """
        Extract intent from user message (more reliable than extracting from LLM reply).
        Phase 2: Improved intent detection with potential_* intents.
        """
        message_lower = message.lower()
        
        # Check for phrases first (more specific), then single words
        # Hebrew phrases for create
        create_phrases_hebrew = ["רוצה להוסיף", "רוצה ליצור", "אני רוצה להוסיף", "אני רוצה ליצור", "בוא נוסיף", "בוא ניצור"]
        # Hebrew phrases for update
        update_phrases_hebrew = ["רוצה לעדכן", "רוצה לשנות", "אני רוצה לעדכן", "אני רוצה לשנות", "בוא נעדכן", "בוא נשנה"]
        # Hebrew phrases for delete
        delete_phrases_hebrew = ["רוצה למחוק", "רוצה להסיר", "אני רוצה למחוק", "אני רוצה להסיר", "בוא נמחק", "בוא נסיר"]
        
        # Check for task insights (deadlines, priorities, urgency) - highest priority
        if any(word in message_lower for word in ["summary", "insights", "report", "weekly", "סיכום", "דוח"]):
            return "get_insights"
        elif any(word in message_lower for word in ["urgent", "priority", "deadline", "due", "דחוף", "עדיפות", "תאריך"]):
            return "task_insights"
        
        # Check for create/update/delete intents FIRST (before list_tasks)
        # These are action verbs - more specific than "list" or "show"
        # Check phrases first (more specific), then single words
        
        # CREATE - check phrases first
        if any(phrase in message_lower for phrase in create_phrases_hebrew):
            return "potential_create"
        # CREATE - check single words
        elif any(word in message_lower for word in ["create", "add", "new", "צור", "הוסף", "תוסיף"]):
            return "potential_create"
        
        # DELETE - check phrases first (BEFORE update - more destructive, needs higher priority)
        if any(phrase in message_lower for phrase in delete_phrases_hebrew):
            return "potential_delete"
        # DELETE - check single words (BEFORE update)
        elif any(word in message_lower for word in ["delete", "remove", "מחק", "הסר", "תמחק", "תמחקי"]):
            return "potential_delete"
        
        # UPDATE - check phrases first
        elif any(phrase in message_lower for phrase in update_phrases_hebrew):
            return "potential_update"
        # UPDATE - check single words
        elif any(word in message_lower for word in ["update", "change", "modify", "edit", "עדכן", "שנה", "ערוך"]):
            return "potential_update"
        elif any(word in message_lower for word in ["complete", "done", "finish", "בוצע", "סיים", "סיימתי"]):
            return "potential_update"
        
        # Check for list tasks (after action verbs)
        # Only match if it's clearly a list query, not an action
        # Exclude "מה" if there are action verbs (create/update/delete)
        action_verbs = ["create", "add", "update", "delete", "remove", "צור", "הוסף", "עדכן", "מחק", "להוסיף", "ליצור", "לעדכן", "למחוק", "להסיר"]
        has_action_verb = any(verb in message_lower for verb in action_verbs)
        
        if any(word in message_lower for word in ["list", "show", "tasks", "רשימה", "הצג"]):
            # Clear list commands
            return "list_tasks"
        elif "מה" in message_lower and not has_action_verb:
            # "מה" only if no action verbs (e.g., "מה המשימות שלי?" not "מה המשימה שתרצה להוסיף?")
            return "list_tasks"
        elif "what" in message_lower and not has_action_verb:
            # "what" only if no action verbs
            return "list_tasks"
        
        return "unknown"

    def _generate_suggestions(self, intent: Optional[str], request: ChatRequest) -> List[str]:
        """Generate suggestions based on intent."""
        if intent == "list_tasks":
            return ["View all tasks", "Filter by status", "Create new task"]
        elif intent == "get_insights" or intent == "task_insights":
            return ["View detailed summary", "Filter by category", "View urgent tasks"]
        elif intent == "create_task" or intent == "potential_create":
            return ["Set deadline", "Add category", "Set priority"]
        elif intent == "potential_update":
            return ["Change priority", "Change deadline", "Change status"]
        elif intent == "potential_delete":
            return ["Confirm deletion", "Cancel", "View all tasks"]
        else:
            return ["List tasks", "Create task", "Get help"]
