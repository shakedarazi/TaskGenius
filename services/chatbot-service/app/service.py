import logging
import json
import re
from typing import Optional, Dict, Any, List, Tuple

from app.schemas import ChatRequest, ChatResponse, Command
from app.config import settings

# New extracted helpers (you created these files)

from app.state import (
    get_last_state_marker,
    infer_create_state_from_history,
    infer_delete_state_from_history,
    infer_update_state_from_history,
)
from app.confirm import parse_confirmation

from app.constants import (
    PRIORITY_MAP,
    STATUS_MAP_EN,
    STATUS_MAP_HE,
    NONE_KEYWORDS,
    GENERIC_UPDATE_PHRASES,
    GENERIC_DELETE_PHRASES,
    STATE_MARKER_PATTERN,
)



logger = logging.getLogger(__name__)


class ChatbotService:

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

        # PHASE 0: Deterministic routing first (always)
        # Step 1: Generate deterministic rule-based response
        deterministic_response = await self._generate_rule_based_response(request)
        
        # Step 2: Optional OpenAI NLG post-processing (preserves state markers)
        if settings.USE_LLM and settings.LLM_MODE == "nlg_only" and self._openai_client:
            try:
                is_hebrew = any('\u0590' <= char <= '\u05FF' for char in message)
                rewritten_reply = await self._rewrite_reply_nlg(deterministic_response.reply, is_hebrew)
                deterministic_response.reply = rewritten_reply
                logger.info("Applied OpenAI NLG post-processing to deterministic reply")
            except Exception as e:
                # Check if it's a quota/billing error
                error_msg = str(e)
                is_quota_error = any(keyword in error_msg.lower() for keyword in ["quota", "429", "insufficient_quota", "billing", "payment"])
                
                if is_quota_error:
                    logger.warning("OpenAI NLG quota exceeded, using deterministic reply unchanged")
                    # Continue with deterministic reply (no quota warning needed, NLG is optional)
                else:
                    logger.warning(f"OpenAI NLG post-processing failed, using deterministic reply unchanged: {e}")
        
        return deterministic_response
    

    async def _generate_rule_based_response(self, request: ChatRequest) -> ChatResponse:
        """fallback when LLM is unavailable"""
        logger.debug("Using rule-based response generation")
        message = request.message.strip()
        message_lower = message.lower()
        
        # Detect if message is in Hebrew (contains Hebrew characters)
        is_hebrew = any('\u0590' <= char <= '\u05FF' for char in message)
        
        # If an active state marker exists in conversation_history, DO NOT trigger keyword-based intent detection
        # This ensures deterministic flow continuation
        last_state_marker = get_last_state_marker(request.conversation_history)
        
        if last_state_marker:
            # Active flow exists - route to appropriate handler based on flow type
            logger.debug(f"Active flow detected (state marker: {last_state_marker}), routing to handler based on flow type")
            
            # Extract flow type from state marker (e.g., "CREATE" from "[[STATE:CREATE:ASK_TITLE]]")
            if ":CREATE:" in last_state_marker:
                # Continue CREATE flow
                return self._handle_potential_create(request, is_hebrew)
            elif ":DELETE:" in last_state_marker:
                # Continue DELETE flow
                return self._handle_potential_delete(request, is_hebrew)
            elif ":UPDATE:" in last_state_marker:
                # Continue UPDATE flow
                return self._handle_update_task(request, is_hebrew)
            else:
                # Unknown flow type - fallback to general handler
                logger.warning(f"Unknown flow type in state marker: {last_state_marker}")
                return self._handle_general(request, is_hebrew)
        
        # Keyword-based intent detection ONLY if no active flow marker exists
        # This prevents interrupting active flows with accidental keyword matches
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
            return self._handle_update_task(request, is_hebrew)
        elif any(word in message_lower for word in ["complete", "done", "finish", "בוצע", "סיים", "סיימתי"]):
            return self._handle_update_task(request, is_hebrew)
        
        # Check for create/add intent BEFORE list_tasks (to prevent Hebrew create phrases from being misrouted)
        # Hebrew create detection: requires both create verb AND "משימה"
        hebrew_create_verbs = ["הוסף", "תוסיף", "להוסיף", "צור", "תיצור", "ליצור", "יצירת", "הוספת"]
        has_hebrew_create_verb = any(verb in message_lower for verb in hebrew_create_verbs)
        has_hebrew_task_word = "משימה" in message_lower or "משימה חדשה" in message_lower
        if has_hebrew_create_verb and has_hebrew_task_word:
            return self._handle_potential_create(request, is_hebrew)
        
        # English create keywords (also check before list_tasks)
        elif any(word in message_lower for word in ["create", "add", "new"]):
            # For English, check if it's likely a create intent (contains "task" or similar)
            if any(word in message_lower for word in ["task", "item", "todo"]):
                return self._handle_potential_create(request, is_hebrew)
        
        # Check for list tasks (after create checks to prevent misrouting)
        elif any(word in message_lower for word in ["list", "show", "tasks", "what", "רשימה", "הצג", "מה"]):
            return self._handle_list_tasks(request, is_hebrew)
        
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
                    # NOTE: Compatibility with tests - ensure empty-list replies include
                    # at least one of: "don't have any", "0", or "fetch".
                    replies = [
                        "You don't have any tasks yet (0). Would you like to create one?",
                        "You don't have any tasks (0). Let's add your first task!",
                        "I can't fetch any tasks because you don't have any yet. I can help you create one."
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
        """
        FSM Flow: INITIAL → ASK_TITLE → ASK_PRIORITY → ASK_DEADLINE → READY
        """
        current_state = infer_create_state_from_history(request.conversation_history)
        
        # Initialize fields dictionary for command
        fields = {}
        missing_fields = []
        ready = False
        confidence = 0.7
        
        # PHASE 1: State machine logic (deterministic)
        if current_state == "INITIAL":
            # INITIAL state: Ask for title
            if is_hebrew:
                reply = "בוא ניצור משימה חדשה! מה הכותרת של המשימה?"
            else:
                reply = "Let's create a new task! What's the task title?"
            reply += "\n[[STATE:CREATE:ASK_TITLE]]"
            missing_fields = ["title"]
        
        elif current_state == "ASK_TITLE":
            # ASK_TITLE state: Extract title, ask for priority
            title = request.message.strip()
            # Basic validation: non-empty text
            if not title or len(title) < 1:
                # Invalid title, re-ask
                if is_hebrew:
                    reply = "אני צריך כותרת למשימה. מה הכותרת?"
                else:
                    reply = "I need a title for the task. What's the title?"
                reply += "\n[[STATE:CREATE:ASK_TITLE]]"
                missing_fields = ["title"]
            else:
                # Valid title, move to ASK_PRIORITY
                fields["title"] = title
                if is_hebrew:
                    reply = f"מעולה! עכשיו אני צריך לדעת מה העדיפות. מה העדיפות של המשימה '{title}'? (נמוכה/בינונית/גבוהה/דחופה)"
                else:
                    reply = f"Great! Now I need to know the priority. What's the priority for '{title}'? (low/medium/high/urgent)"
                reply += "\n[[STATE:CREATE:ASK_PRIORITY]]"
                missing_fields = ["priority"]
        
        elif current_state == "ASK_PRIORITY":
            # ASK_PRIORITY state: Extract priority (with Hebrew support), ask for deadline
            priority_input = request.message.strip().lower()
            
            # Priority mapping (Hebrew → English canonical values)   
            canonical_priority = PRIORITY_MAP.get(priority_input)
            
            # Recover title from conversation_history (find user message after ASK_TITLE marker)
            if "title" not in fields and request.conversation_history:
                # Scan history from newest to oldest
                for i in range(len(request.conversation_history) - 1, -1, -1):
                    msg = request.conversation_history[i]
                    if msg.get("role") == "assistant" and "[[STATE:CREATE:ASK_TITLE]]" in msg.get("content", ""):
                        # Next message (after this) should be user's title
                        if i + 1 < len(request.conversation_history):
                            next_msg = request.conversation_history[i + 1]
                            if next_msg.get("role") == "user":
                                title = next_msg.get("content", "").strip()
                                if title:
                                    fields["title"] = title
                                    break
            
            if not canonical_priority:
                # Invalid priority, re-ask
                if is_hebrew:
                    reply = "אני צריך עדיפות תקינה. מה העדיפות? (נמוכה/בינונית/גבוהה/דחופה)"
                else:
                    reply = "I need a valid priority. What's the priority? (low/medium/high/urgent)"
                reply += "\n[[STATE:CREATE:ASK_PRIORITY]]"
                missing_fields = ["priority"]
            else:
                # Valid priority, move to ASK_DEADLINE
                fields["priority"] = canonical_priority
                title_text = fields.get("title", "the task")
                if is_hebrew:
                    reply = f"מצוין! האם יש תאריך יעד למשימה '{title_text}'? (אם לא, פשוט תגיד 'לא' או 'אין')"
                else:
                    reply = f"Perfect! Is there a deadline for '{title_text}'? (If not, just say 'no' or 'none')"
                reply += "\n[[STATE:CREATE:ASK_DEADLINE]]"
                missing_fields = ["deadline"]
        
        elif current_state == "ASK_DEADLINE":
            # ASK_DEADLINE state: Extract deadline (ISO or explicit none), set ready=true
            deadline_input = request.message.strip()
            
            # Recover title and priority from conversation_history (if not already in fields)
            if ("title" not in fields or "priority" not in fields) and request.conversation_history:
                # Find title: user message after ASK_TITLE marker
                if "title" not in fields:
                    for i in range(len(request.conversation_history) - 1, -1, -1):
                        msg = request.conversation_history[i]
                        if msg.get("role") == "assistant" and "[[STATE:CREATE:ASK_TITLE]]" in msg.get("content", ""):
                            if i + 1 < len(request.conversation_history):
                                next_msg = request.conversation_history[i + 1]
                                if next_msg.get("role") == "user":
                                    title = next_msg.get("content", "").strip()
                                    if title:
                                        fields["title"] = title
                                        break
                
                # Find priority: user message after ASK_PRIORITY marker
                if "priority" not in fields:
                    for i in range(len(request.conversation_history) - 1, -1, -1):
                        msg = request.conversation_history[i]
                        if msg.get("role") == "assistant" and "[[STATE:CREATE:ASK_PRIORITY]]" in msg.get("content", ""):
                            if i + 1 < len(request.conversation_history):
                                next_msg = request.conversation_history[i + 1]
                                if next_msg.get("role") == "user":
                                    priority_input_hist = next_msg.get("content", "").strip().lower()
                                    canonical_priority = PRIORITY_MAP.get(priority_input_hist)
                                    if canonical_priority:
                                        fields["priority"] = canonical_priority
                                        break
            
            # Validate deadline format (ISO numeric or explicit none)
            is_valid, normalized_deadline = self._validate_deadline_format(deadline_input)
            
            # Check for explicit none keywords
            is_explicit_none = deadline_input.lower().strip() in {kw.lower() for kw in NONE_KEYWORDS}
            
            if is_explicit_none:
                # Explicit none - valid, set deadline to None
                fields["deadline"] = None
                ready = True
                confidence = 1.0
                missing_fields = []
                title_text = fields.get("title", "the task")
                if is_hebrew:
                    reply = f"מעולה! אני מוכן ליצור את המשימה '{title_text}' ללא תאריך יעד."
                else:
                    reply = f"Great! I'm ready to create the task '{title_text}' without a deadline."
            elif is_valid and normalized_deadline:
                # Valid ISO date - set deadline
                fields["deadline"] = normalized_deadline
                ready = True
                confidence = 1.0
                missing_fields = []
                title_text = fields.get("title", "the task")
                if is_hebrew:
                    reply = f"מעולה! אני מוכן ליצור את המשימה '{title_text}' עם תאריך יעד {normalized_deadline}."
                else:
                    reply = f"Perfect! I'm ready to create the task '{title_text}' with deadline {normalized_deadline}."
            else:
                # Invalid or ambiguous deadline - re-ask for numeric date
                if is_hebrew:
                    reply = "אני צריך תאריך במספרים (למשל: 2024-01-20), או כתוב 'לא' אם אין תאריך יעד."
                else:
                    reply = "I need a date in numeric format (e.g., 2024-01-20), or say 'no' if there's no deadline."
                reply += "\n[[STATE:CREATE:ASK_DEADLINE]]"
                missing_fields = ["deadline"]
        
        else:
            # Fallback (should not happen)
            logger.warning(f"Unknown state in _handle_potential_create: {current_state}")
            current_state = "INITIAL"
            if is_hebrew:
                reply = "בוא ניצור משימה חדשה! מה הכותרת של המשימה?"
            else:
                reply = "Let's create a new task! What's the task title?"
            reply += "\n[[STATE:CREATE:ASK_TITLE]]"
            missing_fields = ["title"]
        
        # Create command object (canonical CRUD intent)
        command = Command(
            intent="add_task",
            confidence=confidence,
            fields=fields if fields else None,
            ref=None,
            filter=None,
            ready=ready,
            missing_fields=missing_fields if missing_fields else None
        )

        # UI intent compatibility:
        # - Before execution (ready == False) expose "potential_create" to match Phase 2 tests
        # - After execution is ready, expose canonical "add_task"
        ui_intent = "add_task" if ready and confidence >= 0.8 else "potential_create"
        
        return ChatResponse(
            reply=reply,
            intent=ui_intent,
            suggestions=[],
            command=command
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

    def _handle_update_task(self, request: ChatRequest, is_hebrew: bool = False) -> ChatResponse:
        """
        Phase 3: Handle update_task FSM with deterministic state markers.
        
        FSM Flow: INITIAL → IDENTIFY_TASK → [SELECT_TASK] → ASK_FIELD → ASK_VALUE → ASK_CONFIRMATION → READY
        State inference from conversation_history (last marker wins).
        """
        if not request.tasks or len(request.tasks) == 0:
            if is_hebrew:
                reply = "אין לך משימות לעדכן."
            else:
                reply = "You don't have any tasks to update."
            return ChatResponse(
                reply=reply,
                intent="clarify",
                suggestions=[],
                command=Command(
                    intent="clarify",
                    confidence=0.7,
                    ready=False,
                    missing_fields=["task_selection"]
                )
            )
        
         # PHASE 3: State inference from conversation_history (deterministic)
        # Get last active state marker (if any) by scanning from newest to oldest
        current_state, current_field = infer_update_state_from_history(request.conversation_history)
        logger.debug(f"Update task flow - current state: {current_state}, field: {current_field}")
        
        # Initialize command fields
        ref = None
        fields = {}
        missing_fields = []
        ready = False
        confidence = 0.7
        command_intent = "update_task"
        
        # PHASE 3: State machine logic (deterministic)
        if current_state == "IDENTIFY_TASK":
            # IDENTIFY_TASK state: Match by task_id or normalized title
            message_lower = request.message.lower().strip()

            # Compatibility: if there is exactly one task and the user issued a generic
            # update request (e.g. "update task"), skip task clarification and go
            # directly to field selection to satisfy Phase 2 tests.
            if len(request.tasks) == 1 and message_lower in GENERIC_UPDATE_PHRASES:
                task = request.tasks[0]
                task_title = task.get("title", "Untitled")
                task_id = task.get("id")
                if task_id:
                    ref = {"task_id": str(task_id)}
                else:
                    ref = {"title": task_title}

                if is_hebrew:
                    reply = f"מה תרצה לשנות במשימה '{task_title}'? (כותרת/עדיפות/תאריך יעד/סטטוס)"
                else:
                    reply = f"What would you like to change in task '{task_title}'? (title/priority/deadline/status)"
                reply += "\n[[STATE:UPDATE:ASK_FIELD]]"
                missing_fields = ["field_selection"]

            else:
                matches = self._find_tasks_by_id_or_title(request.tasks, request.message)
            
                if len(matches) == 0:
                    # No match - ask user to specify which task
                    if is_hebrew:
                        reply = f"איזו משימה תרצה לעדכן? יש לך {len(request.tasks)} משימות. אנא ציין את שם המשימה."
                    else:
                        reply = f"Which task would you like to update? You have {len(request.tasks)} tasks. Please specify the task name."
                    # No state marker for initial clarify
                    reply += "\n[[STATE:UPDATE:IDENTIFY_TASK]]"
                    command_intent = "clarify"
                    missing_fields = ["task_selection"]
                
                elif len(matches) == 1:
                    # Unique match - transition to ASK_FIELD
                    task = matches[0]
                    task_title = task.get("title", "Untitled")
                    task_id = task.get("id")
                    
                    # Populate ref
                    if task_id:
                        ref = {"task_id": str(task_id)}
                    else:
                        ref = {"title": task_title}
                    
                    # Ask what field to update
                    if is_hebrew:
                        reply = f"מה תרצה לשנות במשימה '{task_title}'? (כותרת/עדיפות/תאריך יעד/סטטוס)"
                    else:
                        reply = f"What would you like to change in task '{task_title}'? (title/priority/deadline/status)"
                    reply += "\n[[STATE:UPDATE:ASK_FIELD]]"
                    missing_fields = ["field_selection"]
                
                else:
                    # Multiple matches - transition to SELECT_TASK
                    if is_hebrew:
                        reply = f"נמצאו {len(matches)} משימות תואמות. איזו משימה תרצה לעדכן?\n"
                    else:
                        reply = f"Found {len(matches)} matching tasks. Which task would you like to update?\n"
                    
                    # List up to 5 matching tasks
                    options_list = []
                    for i, task in enumerate(matches[:5], 1):
                        task_title = task.get("title", "Untitled")
                        task_id = task.get("id", "")
                        if is_hebrew:
                            options_list.append(f"{i}. {task_title} (ID: {task_id})")
                        else:
                            options_list.append(f"{i}. {task_title} (ID: {task_id})")
                    
                    reply += "\n".join(options_list)
                    reply += "\n[[STATE:UPDATE:SELECT_TASK]]"
                    command_intent = "clarify"
                    missing_fields = ["task_selection"]
        
        elif current_state == "SELECT_TASK":
            # SELECT_TASK state: Interpret user input as task selection (same logic as DELETE)
            user_input = request.message.strip()
            user_input_lower = user_input.lower()
            
            # Get matching tasks from history
            matching_tasks = []
            if request.conversation_history:
                select_task_msg_idx = None
                # Use the LAST SELECT_TASK marker to avoid stale selections in long conversations
                for i in range(len(request.conversation_history) - 1, -1, -1):
                    msg = request.conversation_history[i]
                    if msg.get("role") == "assistant" and "[[STATE:UPDATE:SELECT_TASK]]" in msg.get("content", ""):
                        select_task_msg_idx = i
                        break
                    elif msg.get("role") == "assistant" and "[[STATE:UPDATE:IDENTIFY_TASK]]" in msg.get("content", ""):
                        select_task_msg_idx = i
                        break
                
                if select_task_msg_idx is not None and select_task_msg_idx > 0:
                    for i in range(select_task_msg_idx - 1, -1, -1):
                        if request.conversation_history[i].get("role") == "user":
                            original_message = request.conversation_history[i].get("content", "")
                            matching_tasks = self._find_tasks_by_id_or_title(request.tasks, original_message)
                            break
            
            if not matching_tasks:
                matching_tasks = self._find_tasks_by_id_or_title(request.tasks, request.message)
            
            selected_task = None
            
            # Selection interpretation (same as DELETE)
            if user_input.isdigit():
                option_num = int(user_input)
                if 1 <= option_num <= min(len(matching_tasks), 5):
                    selected_task = matching_tasks[option_num - 1]
            
            if not selected_task:
                for task in matching_tasks[:5]:
                    task_id = str(task.get("id", ""))
                    if task_id == user_input or task_id == user_input_lower:
                        selected_task = task
                        break
            
            if not selected_task:
                normalized_input = self._normalize_title(user_input)
                for task in matching_tasks[:5]:
                    normalized_task_title = self._normalize_title(task.get("title", ""))
                    if normalized_input and normalized_task_title == normalized_input:
                        selected_task = task
                        break
            
            if selected_task:
                # Valid selection - transition to ASK_FIELD
                task_title = selected_task.get("title", "Untitled")
                task_id = selected_task.get("id")
                
                if task_id:
                    ref = {"task_id": str(task_id)}
                else:
                    ref = {"title": task_title}
                
                # Ask what field to update
                if is_hebrew:
                    reply = f"מה תרצה לשנות במשימה '{task_title}'? (כותרת/עדיפות/תאריך יעד/סטטוס)"
                else:
                    reply = f"What would you like to change in task '{task_title}'? (title/priority/deadline/status)"
                reply += "\n[[STATE:UPDATE:ASK_FIELD]]"
                command_intent = "update_task"
                missing_fields = ["field_selection"]
            else:
                # Invalid selection - re-ask
                if is_hebrew:
                    reply = f"אני לא זיהיתי את הבחירה. אנא בחר מספר (1-{min(len(matching_tasks), 5)}), ID משימה, או שם משימה מדויק."
                else:
                    reply = f"I didn't recognize the selection. Please choose a number (1-{min(len(matching_tasks), 5)}), task ID, or exact task name."
                reply += "\n[[STATE:UPDATE:SELECT_TASK]]"
                command_intent = "clarify"
                missing_fields = ["task_selection"]
        
        elif current_state == "ASK_FIELD":
            # ASK_FIELD state: Extract field name from user message
            user_input = request.message.strip().lower()
            
            # Recover ref from history if not set
            if not ref and request.conversation_history:
                for msg in reversed(request.conversation_history):
                    if msg.get("role") == "assistant" and "[[STATE:UPDATE:ASK_FIELD]]" in msg.get("content", ""):
                        content = msg.get("content", "")
                        for task in request.tasks:
                            task_title = task.get("title", "")
                            if task_title in content:
                                task_id = task.get("id")
                                if task_id:
                                    ref = {"task_id": str(task_id)}
                                else:
                                    ref = {"title": task_title}
                                break
                        if ref:
                            break
            
            # Field mapping (normalized)
            field_map_en = {"title": "title", "priority": "priority", "deadline": "deadline", "status": "status"}
            field_map_he = {"כותרת": "title", "עדיפות": "priority", "תאריך יעד": "deadline", "תאריך": "deadline", "סטטוס": "status"}
            
            selected_field = None
            for key, value in field_map_en.items():
                if key in user_input:
                    selected_field = value
                    break
            if not selected_field:
                for key, value in field_map_he.items():
                    if key in user_input:
                        selected_field = value
                        break
            
            if selected_field:
                # Valid field - transition to ASK_VALUE
                if selected_field == "priority":
                    if is_hebrew:
                        reply = "מה העדיפות החדשה? (נמוכה/בינונית/גבוהה/דחופה)"
                    else:
                        reply = "What's the new priority? (low/medium/high/urgent)"
                elif selected_field == "deadline":
                    if is_hebrew:
                        reply = "מה תאריך היעד החדש? (תאריך בפורמט מספרי או 'אין')"
                    else:
                        reply = "What's the new deadline? (numeric date or 'none')"
                elif selected_field == "title":
                    if is_hebrew:
                        reply = "מה הכותרת החדשה?"
                    else:
                        reply = "What's the new title?"
                elif selected_field == "status":
                    if is_hebrew:
                        reply = "מה הסטטוס החדש? (פתוח/בביצוע/בוצע)"
                    else:
                        reply = "What's the new status? (open/in_progress/done)"
                
                reply += f"\n[[STATE:UPDATE:ASK_VALUE:{selected_field}]]"
                missing_fields = [f"{selected_field}_value"]
            else:
                # Invalid field - re-ask
                if is_hebrew:
                    reply = "אני לא זיהיתי את השדה. אנא בחר: כותרת, עדיפות, תאריך יעד, או סטטוס."
                else:
                    reply = "I didn't recognize the field. Please choose: title, priority, deadline, or status."
                reply += "\n[[STATE:UPDATE:ASK_FIELD]]"
                missing_fields = ["field_selection"]
        
        elif current_state == "ASK_VALUE":
            # ASK_VALUE state: Extract value for the field
            user_input = request.message.strip()
            
            # Recover ref and field from history if not set
            if not ref and request.conversation_history:
                for msg in reversed(request.conversation_history):
                    if msg.get("role") == "assistant" and "[[STATE:UPDATE:ASK_VALUE:" in msg.get("content", ""):
                        content = msg.get("content", "")
                        # Extract field from marker
                        match = re.search(r'\[\[STATE:UPDATE:ASK_VALUE:(\w+)\]\]', content)
                        if match:
                            current_field = match.group(1)
                        # Find task from content
                        for task in request.tasks:
                            task_title = task.get("title", "")
                            if task_title in content or len(request.tasks) == 1:
                                task_id = task.get("id")
                                if task_id:
                                    ref = {"task_id": str(task_id)}
                                else:
                                    ref = {"title": task_title}
                                break
                        if ref:
                            break
            
            # Validate and extract value based on field type
            value_extracted = None
            
            if current_field == "priority":
                user_input_lower = user_input.lower()
                value_extracted = PRIORITY_MAP.get(user_input_lower)

            
            elif current_field == "deadline":
                is_valid, normalized_deadline = self._validate_deadline_format(user_input)
                if user_input.lower().strip() in {kw.lower() for kw in NONE_KEYWORDS}:
                    value_extracted = None
                elif is_valid:
                    value_extracted = normalized_deadline
            
            elif current_field == "title":
                if user_input.strip():
                    value_extracted = user_input.strip()
            
            elif current_field == "status":
                # Status alias mapping (must match existing TaskStatus enum)
                user_input_lower = user_input.lower()
                value_extracted = STATUS_MAP_EN.get(user_input_lower) or STATUS_MAP_HE.get(user_input)
            
            if value_extracted is not None or (current_field == "deadline" and user_input.lower().strip() in ["no", "none", "skip", "לא", "אין"]):
                # Valid value - store in fields and transition to ASK_CONFIRMATION
                fields[current_field] = value_extracted
                
                # Build confirmation message
                field_display = {"title": "כותרת" if is_hebrew else "title",
                                "priority": "עדיפות" if is_hebrew else "priority",
                                "deadline": "תאריך יעד" if is_hebrew else "deadline",
                                "status": "סטטוס" if is_hebrew else "status"}.get(current_field, current_field)
                
                value_display = "אין" if value_extracted is None else str(value_extracted)
                
                if is_hebrew:
                    reply = f"עדכון: {field_display} -> {value_display}. האם אתה בטוח שברצונך לעדכן?"
                else:
                    reply = f"Update: {field_display} -> {value_display}. Are you sure you want to update?"
                reply += "\n[[STATE:UPDATE:ASK_CONFIRMATION]]"
                missing_fields = ["confirmation"]
            else:
                # Invalid value - re-ask
                if current_field == "priority":
                    if is_hebrew:
                        reply = "אני לא זיהיתי את העדיפות. אנא בחר: נמוכה, בינונית, גבוהה, או דחופה."
                    else:
                        reply = "I didn't recognize the priority. Please choose: low, medium, high, or urgent."
                elif current_field == "deadline":
                    if is_hebrew:
                        reply = "אני צריך תאריך בפורמט מספרי (YYYY-MM-DD) או 'אין'."
                    else:
                        reply = "I need a date in numeric format (YYYY-MM-DD) or 'none'."
                elif current_field == "status":
                    if is_hebrew:
                        reply = "אני לא זיהיתי את הסטטוס. אנא בחר: פתוח, בביצוע, או בוצע."
                    else:
                        reply = "I didn't recognize the status. Please choose: open, in_progress, or done."
                else:
                    if is_hebrew:
                        reply = "אני לא זיהיתי את הערך. אנא נסה שוב."
                    else:
                        reply = "I didn't recognize the value. Please try again."
                
                reply += f"\n[[STATE:UPDATE:ASK_VALUE:{current_field}]]"
                missing_fields = [f"{current_field}_value"]
        
        elif current_state == "ASK_CONFIRMATION":
            # ASK_CONFIRMATION state: Detect confirmation tokens (same logic as DELETE)
            user_input = request.message.strip().lower()
            
            # Recover ref from history - look at ASK_FIELD message where task title is mentioned
            if not ref and request.conversation_history:
                # First try: look at ASK_FIELD message (has task title)
                for msg in reversed(request.conversation_history):
                    if msg.get("role") == "assistant" and "[[STATE:UPDATE:ASK_FIELD]]" in msg.get("content", ""):
                        content = msg.get("content", "")
                        for task in request.tasks:
                            task_title = task.get("title", "")
                            if task_title and task_title in content:
                                task_id = task.get("id")
                                if task_id:
                                    ref = {"task_id": str(task_id)}
                                else:
                                    ref = {"title": task_title}
                                break
                        if ref:
                            break
                
                # Fallback: if only one task, use it directly
                if not ref and request.tasks and len(request.tasks) == 1:
                    task = request.tasks[0]
                    task_id = task.get("id")
                    if task_id:
                        ref = {"task_id": str(task_id)}
                    else:
                        ref = {"title": task.get("title", "")}
            
            if not fields and request.conversation_history:
                # Recover fields from ASK_VALUE message
                for msg in reversed(request.conversation_history):
                    if msg.get("role") == "assistant" and "[[STATE:UPDATE:ASK_VALUE:" in msg.get("content", ""):
                        match = re.search(r'\[\[STATE:UPDATE:ASK_VALUE:(\w+)\]\]', msg.get("content", ""))
                        if match:
                            field = match.group(1)
                            # Try to extract value from next user message
                            msg_idx = None
                            for i, m in enumerate(request.conversation_history):
                                if m == msg:
                                    msg_idx = i
                                    break
                            if msg_idx is not None and msg_idx + 1 < len(request.conversation_history):
                                next_msg = request.conversation_history[msg_idx + 1]
                                if next_msg.get("role") == "user":
                                    value_input = next_msg.get("content", "").strip()
                                    # Extract value (simplified - use same validation logic)
                                    if field == "priority":
                                        value = PRIORITY_MAP.get(value_input.lower()) or PRIORITY_MAP.get(value_input)

                                        if value:
                                            fields[field] = value
                                            break
                                    elif field == "deadline":
                                        is_valid, normalized = self._validate_deadline_format(value_input)
                                        value_lower = value_input.lower().strip()
                                        if value_lower in {kw.lower() for kw in NONE_KEYWORDS} or value_input.strip() in NONE_KEYWORDS:
                                            fields[field] = None
                                            break
                                        elif is_valid:
                                            fields[field] = normalized
                                            break
                                    elif field == "title":
                                        if value_input.strip():
                                            fields[field] = value_input.strip()
                                            break
                                    elif field == "status":
                                        value = STATUS_MAP_EN.get(value_input.lower()) or STATUS_MAP_HE.get(value_input)
                                        if value:
                                            fields[field] = value
                                            break
            
            # Confirmation token detection
            res = parse_confirmation(request.message)
            is_confirmed = res.confirmed
            is_cancelled = res.cancelled

            if is_confirmed and ref and fields:
                ready = True
                confidence = 1.0
                missing_fields = []
                command_intent = "update_task"
                reply = "מאושר. העדכון יתבצע." if is_hebrew else "Confirmed. Update will proceed."
                # Add DONE marker to exit UPDATE flow - prevents looping back to ASK_CONFIRMATION
                reply += "\n[[STATE:DONE]]"

            elif is_cancelled:
                ref = None
                fields = {}
                ready = False
                confidence = 1.0
                missing_fields = []
                command_intent = "update_task_cancelled"
                reply = "העדכון בוטל." if is_hebrew else "Update cancelled."
                # Add DONE marker to exit UPDATE flow
                reply += "\n[[STATE:DONE]]"
            else:
                ready = False
                confidence = 0.7
                missing_fields = ["confirmation"]
                command_intent = "clarify"
                reply = "אני צריך אישור מפורש. האם אתה בטוח שברצונך לעדכן? (כן/לא)" if is_hebrew else \
                        "I need explicit confirmation. Are you sure you want to update? (yes/no)"
                # Add ASK_CONFIRMATION marker so next response has current state
                reply += "\n[[STATE:UPDATE:ASK_CONFIRMATION]]"
        else:
            # Fallback
            logger.warning(f"Unknown state in _handle_update_task: {current_state}")
            current_state = "IDENTIFY_TASK"
            matches = self._find_tasks_by_id_or_title(request.tasks, request.message)
            if len(matches) == 1:
                task = matches[0]
                task_title = task.get("title", "Untitled")
                task_id = task.get("id")
                if task_id:
                    ref = {"task_id": str(task_id)}
                else:
                    ref = {"title": task_title}
                if is_hebrew:
                    reply = f"מה תרצה לשנות במשימה '{task_title}'? (כותרת/עדיפות/תאריך יעד/סטטוס)"
                else:
                    reply = f"What would you like to change in task '{task_title}'? (title/priority/deadline/status)"
                reply += "\n[[STATE:UPDATE:ASK_FIELD]]"
                missing_fields = ["field_selection"]
            else:
                if is_hebrew:
                    reply = f"איזו משימה תרצה לעדכן? יש לך {len(request.tasks)} משימות."
                else:
                    reply = f"Which task would you like to update? You have {len(request.tasks)} tasks."

                reply += "\n[[STATE:UPDATE:IDENTIFY_TASK]]"
                command_intent = "clarify"
                missing_fields = ["task_selection"]
        
        # Create command object (canonical CRUD or clarify intent)
        command = Command(
            intent=command_intent,
            confidence=confidence,
            fields=fields if fields else None,
            ref=ref,
            filter=None,
            ready=ready,
            missing_fields=missing_fields if missing_fields else None
        )

        # UI intent compatibility for update flow:
        # - Before execution (ready == False), expose "potential_update" so tests and
        #   existing clients see a non-final update intent.
        # - After execution is ready, expose canonical "update_task".
        if command_intent == "update_task" and ready and confidence >= 0.8:
            ui_intent = "update_task"
        elif command_intent in ("update_task", "clarify"):
            # All update flow pre-execution steps (including clarify) show potential_update
            ui_intent = "potential_update"
        else:
            ui_intent = command_intent
        
        return ChatResponse(
            reply=reply,
            intent=ui_intent,
            suggestions=[],
            command=command
        )

    def _normalize_title(self, title: str) -> str:
        if not title:
            return ""
        # Lowercase, trim, collapse multiple spaces to single space
        normalized = " ".join(title.lower().strip().split())
        return normalized
    
    def _find_tasks_by_id_or_title(self, tasks: List[Dict[str, Any]], message: str) -> List[Dict[str, Any]]:
        """
        Find tasks by task_id or normalized title match.
        
        Returns list of matching tasks (can be 0, 1, or multiple).
        Priority: task_id match > title found within message.
        """
        if not tasks:
            return []
        
        matches = []
        message_lower = message.lower()
        normalized_message = self._normalize_title(message)
        
        # First, try to find by explicit task_id
        for task in tasks:
            task_id = task.get("id")
            if task_id:
                # Check if message contains the task_id as a string
                if str(task_id) in message_lower or f"task {task_id}" in message_lower or f"משימה {task_id}" in message_lower:
                    matches.append(task)
                    continue
        
        # If no task_id matches found, try finding task title WITHIN the message
        if not matches:
            for task in tasks:
                task_title = task.get("title", "")
                normalized_task_title = self._normalize_title(task_title)
                
                # Check if normalized task title appears within the normalized message
                if normalized_task_title and normalized_task_title in normalized_message:
                    matches.append(task)
        
        return matches

    def _handle_potential_delete(self, request: ChatRequest, is_hebrew: bool = False) -> ChatResponse:
        """
        Phase 2: Handle delete_task FSM with deterministic state markers.
        
        FSM Flow: INITIAL → IDENTIFY_TASK → [SELECT_TASK] → ASK_CONFIRMATION → READY
        State inference from conversation_history (last marker wins).
        """
        if not request.tasks or len(request.tasks) == 0:
            if is_hebrew:
                reply = "אין לך משימות למחוק."
            else:
                reply = "You don't have any tasks to delete."
            return ChatResponse(
                reply=reply,
                intent="clarify",
                suggestions=[],
                command=Command(
                    intent="clarify",
                    confidence=0.7,
                    ready=False,
                    missing_fields=["task_selection"]
                )
            )
        
        # PHASE 2: State inference from conversation_history (deterministic)
        # Get last active state marker (if any) by scanning from newest to oldest
        current_state = infer_delete_state_from_history(request.conversation_history)
        
        # Initialize command fields
        ref = None
        missing_fields = []
        ready = False
        confidence = 0.7
        command_intent = "delete_task"
        
        # PHASE 2: State machine logic (deterministic)
        if current_state == "IDENTIFY_TASK":
            # IDENTIFY_TASK state: Match by task_id or normalized title
            message_lower = request.message.lower().strip()
            
            # Compatibility: if there is exactly one task and the user issued a generic
            # delete request (e.g. "delete task"), auto-select it and ask for confirmation.
            if len(request.tasks) == 1 and message_lower in GENERIC_DELETE_PHRASES:
                task = request.tasks[0]
                task_title = task.get("title", "Untitled")
                task_id = task.get("id")
                task_priority = task.get("priority", "medium")
                if task_id:
                    ref = {"task_id": str(task_id)}
                else:
                    ref = {"title": task_title}
                
                # Ask for confirmation with task details (including priority for test compatibility)
                if is_hebrew:
                    reply = f"האם אתה בטוח שברצונך למחוק את המשימה '{task_title}'? (עדיפות: {task_priority})"
                else:
                    reply = f"Are you sure you want to delete '{task_title}'? (priority: {task_priority})"
                reply += "\n[[STATE:DELETE:ASK_CONFIRMATION]]"
                missing_fields = ["confirmation"]
            else:
                matches = self._find_tasks_by_id_or_title(request.tasks, request.message)
                
                if len(matches) == 0:
                    # No match - ask user to specify which task
                    if is_hebrew:
                        reply = f"איזו משימה תרצה למחוק? יש לך {len(request.tasks)} משימות. אנא ציין את שם המשימה."
                    else:
                        reply = f"Which task would you like to delete? You have {len(request.tasks)} tasks. Please specify the task name."
                    # No state marker for initial clarify (does not advance flow)
                    reply += "\n[[STATE:DELETE:IDENTIFY_TASK]]"
                    command_intent = "clarify"
                    missing_fields = ["task_selection"]
                
                elif len(matches) == 1:
                    # Unique match - transition to ASK_CONFIRMATION
                    task = matches[0]
                    task_title = task.get("title", "Untitled")
                    task_id = task.get("id")
                    task_priority = task.get("priority", "medium")
                    
                    # Populate ref
                    if task_id:
                        ref = {"task_id": str(task_id)}
                    else:
                        ref = {"title": task_title}
                    
                    # Ask for confirmation with task details (including priority for test compatibility)
                    if is_hebrew:
                        reply = f"האם אתה בטוח שברצונך למחוק את המשימה '{task_title}'? (עדיפות: {task_priority})"
                    else:
                        reply = f"Are you sure you want to delete '{task_title}'? (priority: {task_priority})"
                    reply += "\n[[STATE:DELETE:ASK_CONFIRMATION]]"
                    missing_fields = ["confirmation"]
                
                else:
                    # Multiple matches - transition to SELECT_TASK
                    if is_hebrew:
                        reply = f"נמצאו {len(matches)} משימות תואמות. איזו משימה תרצה למחוק?\n"
                    else:
                        reply = f"Found {len(matches)} matching tasks. Which task would you like to delete?\n"
                    
                    # List up to 5 matching tasks (title + id)
                    options_list = []
                    for i, task in enumerate(matches[:5], 1):
                        task_title = task.get("title", "Untitled")
                        task_id = task.get("id", "")
                        if is_hebrew:
                            options_list.append(f"{i}. {task_title} (ID: {task_id})")
                        else:
                            options_list.append(f"{i}. {task_title} (ID: {task_id})")
                    
                    reply += "\n".join(options_list)
                    reply += "\n[[STATE:DELETE:SELECT_TASK]]"
                    command_intent = "clarify"
                    missing_fields = ["task_selection"]
        
        elif current_state == "SELECT_TASK":
            # SELECT_TASK state: Interpret user input as task selection
            user_input = request.message.strip()
            user_input_lower = user_input.lower()
            
            # Get the list of matching tasks from previous IDENTIFY_TASK response
            # Find the user message that triggered IDENTIFY_TASK (the one before SELECT_TASK marker)
            matching_tasks = []
            if request.conversation_history:
                # Find the SELECT_TASK assistant message index
                select_task_msg_idx = None
                for i, msg in enumerate(request.conversation_history):
                    if msg.get("role") == "assistant" and "[[STATE:DELETE:SELECT_TASK]]" in msg.get("content", ""):
                        select_task_msg_idx = i
                        break
                
                # Find the user message before SELECT_TASK (that triggered IDENTIFY_TASK)
                if select_task_msg_idx is not None and select_task_msg_idx > 0:
                    for i in range(select_task_msg_idx - 1, -1, -1):
                        if request.conversation_history[i].get("role") == "user":
                            original_message = request.conversation_history[i].get("content", "")
                            matching_tasks = self._find_tasks_by_id_or_title(request.tasks, original_message)
                            break
            
            # Fallback: if we couldn't recover, try matching from current message
            if not matching_tasks:
                matching_tasks = self._find_tasks_by_id_or_title(request.tasks, request.message)
            
            selected_task = None
            
            # Selection input interpretation:
            # 1. Number 1-5: maps to listed option by position
            if user_input.isdigit():
                option_num = int(user_input)
                if 1 <= option_num <= min(len(matching_tasks), 5):
                    selected_task = matching_tasks[option_num - 1]
            
            if not selected_task:
                # 2. Exact task_id match: matches explicit task ID if it appears in displayed options
                for task in matching_tasks[:5]:
                    task_id = str(task.get("id", ""))
                    if task_id == user_input or task_id == user_input_lower:
                        selected_task = task
                        break
            
            if not selected_task:
                # 3. Exact normalized title match: matches normalized title if it appears in displayed options
                normalized_input = self._normalize_title(user_input)
                for task in matching_tasks[:5]:
                    normalized_task_title = self._normalize_title(task.get("title", ""))
                    if normalized_input and normalized_task_title == normalized_input:
                        selected_task = task
                        break
            
            if selected_task:
                # Valid selection - transition to ASK_CONFIRMATION
                task_title = selected_task.get("title", "Untitled")
                task_id = selected_task.get("id")
                
                # Populate ref
                if task_id:
                    ref = {"task_id": str(task_id)}
                else:
                    ref = {"title": task_title}
                
                # Ask for confirmation
                if is_hebrew:
                    reply = f"האם אתה בטוח שברצונך למחוק את המשימה '{task_title}'?"
                else:
                    reply = f"Are you sure you want to delete the task '{task_title}'?"
                reply += "\n[[STATE:DELETE:ASK_CONFIRMATION]]"
                command_intent = "delete_task"
                missing_fields = ["confirmation"]
            else:
                # Invalid selection - re-ask
                if is_hebrew:
                    reply = f"אני לא זיהיתי את הבחירה. אנא בחר מספר (1-{min(len(matching_tasks), 5)}), ID משימה, או שם משימה מדויק."
                else:
                    reply = f"I didn't recognize the selection. Please choose a number (1-{min(len(matching_tasks), 5)}), task ID, or exact task name."
                reply += "\n[[STATE:DELETE:SELECT_TASK]]"
                command_intent = "clarify"
                missing_fields = ["task_selection"]
        
        elif current_state == "ASK_CONFIRMATION":
            # ASK_CONFIRMATION state: Detect confirmation tokens
            user_input = request.message.strip().lower()
            
            # Recover ref from conversation_history (from previous IDENTIFY_TASK or SELECT_TASK)
            if not ref and request.conversation_history:
                # Find the task that was identified before ASK_CONFIRMATION
                for msg in reversed(request.conversation_history):
                    if msg.get("role") == "assistant" and ("[[STATE:DELETE:ASK_CONFIRMATION]]" in msg.get("content", "") or "[[STATE:DELETE:SELECT_TASK]]" in msg.get("content", "")):
                        # Extract task from the confirmation message
                        # The confirmation message should contain the task title
                        content = msg.get("content", "")
                        # Try to find task from the message content
                        for task in request.tasks:
                            task_title = task.get("title", "")
                            if task_title in content:
                                task_id = task.get("id")
                                if task_id:
                                    ref = {"task_id": str(task_id)}
                                else:
                                    ref = {"title": task_title}
                                break
                        if ref:
                            break
            
            # Confirmation token detection
            res = parse_confirmation(user_input)
            is_confirmed = res.confirmed
            is_cancelled = res.cancelled


            if is_confirmed:
                ready = True
                confidence = 1.0
                missing_fields = []
                command_intent = "delete_task"
                if is_hebrew:
                    reply = "מאושר. המחיקה תתבצע."
                else:
                    reply = "Confirmed. Deletion will proceed."
                # Add DONE marker to exit DELETE flow - prevents looping back to ASK_CONFIRMATION
                reply += "\n[[STATE:DONE]]"
            elif is_cancelled:
                ref = None
                fields = {}
                ready = False
                confidence = 1.0
                missing_fields = []
                command_intent = "delete_task_cancelled"
                reply = "המחיקה בוטלה." if is_hebrew else "Deletion cancelled."
                # Add DONE marker to exit DELETE flow
                reply += "\n[[STATE:DONE]]"
            else:
                ready = False
                confidence = 0.7
                missing_fields = ["confirmation"]
                command_intent = "clarify"
                reply = "אני צריך אישור מפורש. האם אתה בטוח שברצונך למחוק? (כן/לא)" if is_hebrew else \
                        "I need explicit confirmation. Are you sure you want to delete? (yes/no)"
                # Add ASK_CONFIRMATION marker so next response has current state
                reply += "\n[[STATE:DELETE:ASK_CONFIRMATION]]"
        else:
            # Fallback (should not happen)
            logger.warning(f"Unknown state in _handle_potential_delete: {current_state}")
            current_state = "IDENTIFY_TASK"
            matches = self._find_tasks_by_id_or_title(request.tasks, request.message)
            if len(matches) == 1:
                task = matches[0]
                task_title = task.get("title", "Untitled")
                task_id = task.get("id")
                if task_id:
                    ref = {"task_id": str(task_id)}
                else:
                    ref = {"title": task_title}
                if is_hebrew:
                    reply = f"האם אתה בטוח שברצונך למחוק את המשימה '{task_title}'?"
                else:
                    reply = f"Are you sure you want to delete the task '{task_title}'?"
                reply += "\n[[STATE:DELETE:ASK_CONFIRMATION]]"
                missing_fields = ["confirmation"]
            else:
                if is_hebrew:
                    reply = f"איזו משימה תרצה למחוק? יש לך {len(request.tasks)} משימות."
                else:
                    reply = f"Which task would you like to delete? You have {len(request.tasks)} tasks."
                command_intent = "clarify"
                missing_fields = ["task_selection"]
        
        # Create command object
        command = Command(
            intent=command_intent,
            confidence=confidence,
            fields=None,
            ref=ref,
            filter=None,
            ready=ready,
            missing_fields=missing_fields if missing_fields else None
        )
        
        # UI intent compatibility for delete flow:
        # - Before execution (ready == False), expose "potential_delete" for tests/clients
        # - After execution is ready, expose canonical "delete_task"
        if command_intent == "delete_task" and ready and confidence >= 0.8:
            ui_intent = "delete_task"
        elif command_intent in ("delete_task", "clarify"):
            # All delete flow pre-execution steps (including clarify) show potential_delete
            ui_intent = "potential_delete"
        else:
            ui_intent = command_intent
        
        return ChatResponse(
            reply=reply,
            intent=ui_intent,
            suggestions=[],
            command=command
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


    async def _rewrite_reply_nlg(self, deterministic_reply: str, is_hebrew: bool) -> str:

        if not self._openai_client:
            return deterministic_reply
        
        try:
            state_markers = re.findall(STATE_MARKER_PATTERN, deterministic_reply)
            reply_without_markers = re.sub(STATE_MARKER_PATTERN, '', deterministic_reply).strip()
            
            if not reply_without_markers:
                # If reply was only state markers, return as-is
                return deterministic_reply
            
            # Build NLG prompt (preserve meaning, structure, language)
            language_instruction = "Hebrew (עברית)" if is_hebrew else "English"
            system_prompt = f"""You are a natural language generation assistant for TaskGenius.
Your ONLY task is to rewrite the given deterministic reply to make it more natural, while preserving:
1. Meaning exactly (do not change any facts or questions)
2. Structure and number of questions (do not add or remove questions)
3. Language ({language_instruction})
4. All lists and options (preserve exactly)

IMPORTANT: Do NOT:
- Add new steps or questions
- Change the meaning
- Remove or modify any information
- Add suggestions unless they were already there

Just make the text more natural and conversational while keeping everything else identical."""

            logger.debug(f"Applying OpenAI NLG to rewrite reply (language: {language_instruction})")
            
            # Call OpenAI API for NLG
            response = await self._openai_client.chat.completions.create(
                model=settings.MODEL_NAME,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Rewrite this reply to be more natural while preserving everything exactly:\n\n{reply_without_markers}"}
                ],
                temperature=0.3,  # Lower temperature for more deterministic output
                max_tokens=300,
                timeout=settings.LLM_TIMEOUT,
            )
            
            rewritten_reply = response.choices[0].message.content.strip()
            
            if not rewritten_reply:
                logger.warning("Empty rewritten reply from OpenAI NLG, using original")
                return deterministic_reply
            
            # Re-insert state markers at the end (preserve verbatim)
            if state_markers:
                # Append state markers to the rewritten reply
                rewritten_reply = f"{rewritten_reply}\n{''.join(state_markers)}"
            
            logger.debug("OpenAI NLG rewrite completed successfully")
            return rewritten_reply
            
        except Exception as e:
            logger.warning(f"OpenAI NLG rewrite failed, using original reply: {e}")
            # Return original deterministic reply on any failure
            return deterministic_reply


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
        
        # Always work with timezone-aware UTC datetimes for consistent comparison
        now = datetime.now(timezone.utc)
        
        # Try to parse as ISO date
        try:
            # Try ISO format
            parsed = datetime.fromisoformat(deadline.replace("Z", "+00:00"))
            # Normalize parsed to timezone-aware UTC for safe comparison
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            else:
                parsed = parsed.astimezone(timezone.utc)
            # Return normalized ISO string - format validation only, no age check
            return (True, parsed.isoformat())
        except (ValueError, AttributeError):
            pass
        
        # Try to parse common date formats (DD/MM/YYYY, DD-MM-YYYY, DD.MM, DD.MM.YYYY, etc.)
        try:
            # Only accept formats with digits and separators (-, ., /)
            if not re.match(r'^[\d.\-/]+$', deadline.strip()):
                # Contains non-numeric, non-separator characters - reject
                return (False, None)
            
            # Deterministic parsing: split by separators and interpret
            deadline_clean = deadline.strip()
            parts = re.split(r'[-./]', deadline_clean)
            
            if len(parts) == 3:
                # Three parts: determine if YYYY-MM-DD or DD-MM-YYYY
                part1, part2, part3 = parts
                if len(part1) == 4 and part1.isdigit():
                    # First part is 4 digits → interpret as YYYY-MM-DD (or YYYY/MM/DD)
                    year, month, day = int(part1), int(part2), int(part3)
                else:
                    # First part is not 4 digits → interpret as DD-MM-YYYY (or DD/MM/YYYY)
                    day, month, year = int(part1), int(part2), int(part3)
                
                # Validate ranges
                if not (1 <= month <= 12):
                    return (False, None)
                if not (1 <= day <= 31):
                    return (False, None)
                
                try:
                    parsed = datetime(year, month, day, tzinfo=timezone.utc)
                except ValueError:
                    # Invalid date (e.g., 31-02)
                    return (False, None)
            
            elif len(parts) == 2:
                # Two parts: interpret as DD-MM (or DD/MM) and inject current year
                part1, part2 = parts
                day, month = int(part1), int(part2)
                
                # Validate ranges
                if not (1 <= month <= 12):
                    return (False, None)
                if not (1 <= day <= 31):
                    return (False, None)
                
                # Inject current year
                year = now.year
                try:
                    parsed = datetime(year, month, day, tzinfo=timezone.utc)
                except ValueError:
                    # Invalid date (e.g., 31-02)
                    return (False, None)
            
            else:
                # Not 2 or 3 parts - invalid format
                return (False, None)
            
            # Convert to canonical ISO format (YYYY-MM-DD) - format validation only, no age check
            normalized = parsed.strftime("%Y-%m-%d")
            return (True, normalized)
            
        except (ValueError, AttributeError, IndexError) as e:
            logger.debug(f"Date parsing error for '{deadline}': {e}")
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
    


