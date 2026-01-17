"""
TASKGENIUS Chatbot Service - Service

Business logic for generating conversational responses.
This is a read-only facade - no mutations or DB access.
"""

import logging
from typing import Optional, Dict, Any, List
from app.schemas import ChatRequest, ChatResponse
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
                logger.warning(f"LLM generation failed, falling back to rule-based: {e}")
        
        # Fallback to rule-based logic
        logger.debug("Using rule-based response generation")
        message_lower = message.lower()
        
        # Detect if message is in Hebrew (contains Hebrew characters)
        is_hebrew = any('\u0590' <= char <= '\u05FF' for char in message)
        
        # Check for common intents (order matters - check insights before list)
        # Support both English and Hebrew keywords
        hebrew_keywords = {
            "summary": ["סיכום", "סיכום שבועי", "דוח", "insights"],
            "list": ["רשימה", "הצג", "מה", "tasks", "list", "show"],
            "create": ["צור", "הוסף", "תוסיף", "new", "add", "create"],
            "help": ["עזרה", "איך", "help", "how"]
        }
        
        if any(word in message_lower for word in ["summary", "insights", "report", "weekly", "סיכום", "דוח"]):
            return self._handle_insights(request, is_hebrew)
        elif any(word in message_lower for word in ["list", "show", "tasks", "what", "רשימה", "הצג", "מה"]):
            return self._handle_list_tasks(request, is_hebrew)
        elif any(word in message_lower for word in ["create", "add", "new", "task", "צור", "הוסף", "תוסיף"]):
            return self._handle_create_task(request, is_hebrew)
        elif any(word in message_lower for word in ["help", "how", "what can", "עזרה", "איך"]):
            return self._handle_help(is_hebrew)
        else:
            return self._handle_general(request, is_hebrew)

    def _handle_list_tasks(self, request: ChatRequest, is_hebrew: bool = False) -> ChatResponse:
        """Handle list tasks intent."""
        if request.tasks is not None:
            # tasks was explicitly provided (even if empty list)
            count = len(request.tasks)
            if count == 0:
                reply = "אין לך משימות עדיין. תרצה ליצור אחת?" if is_hebrew else "You don't have any tasks yet. Would you like to create one?"
            else:
                if is_hebrew:
                    reply = f"יש לך {count} משימה/ות. "
                    task_titles = [t.get("title", "ללא כותרת") for t in request.tasks[:3]]
                    reply += "הנה כמה: " + ", ".join(task_titles)
                    if count > 3:
                        reply += f", ועוד {count - 3}."
                else:
                    reply = f"You have {count} task(s). "
                    task_titles = [t.get("title", "Untitled") for t in request.tasks[:3]]
                    reply += "Here are some: " + ", ".join(task_titles)
                    if count > 3:
                        reply += f", and {count - 3} more."
        else:
            # tasks was not provided
            reply = "אני יכול לעזור לך לראות את המשימות שלך. תן לי לאסוף אותן." if is_hebrew else "I can help you list your tasks. Let me fetch them for you."
        
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

    def _handle_create_task(self, request: ChatRequest, is_hebrew: bool = False) -> ChatResponse:
        """Handle create task intent."""
        if is_hebrew:
            reply = "אני יכול לעזור לך ליצור משימה. אנא ספק: כותרת, עדיפות (נמוכה/בינונית/גבוהה/דחופה), ואופציונלית תאריך יעד."
            suggestions = ["הגדר תאריך יעד", "הוסף קטגוריה", "הגדר עדיפות"]
        else:
            reply = "I can help you create a task. Please provide: title, priority (low/medium/high/urgent), and optionally a deadline."
            suggestions = ["Set deadline", "Add category", "Set priority"]
        
        return ChatResponse(
            reply=reply,
            intent="create_task",
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
            f"User's message: {request.message}",
            ""
        ]
        
        # Add tasks context
        if request.tasks:
            prompt_parts.append("User's tasks:")
            for task in request.tasks[:10]:  # Limit to 10 tasks
                title = task.get("title", "Untitled")
                status = task.get("status", "unknown")
                priority = task.get("priority", "unknown")
                deadline = task.get("deadline", "No deadline")
                prompt_parts.append(f"  - {title} (Status: {status}, Priority: {priority}, Deadline: {deadline})")
            if len(request.tasks) > 10:
                prompt_parts.append(f"  ... and {len(request.tasks) - 10} more tasks")
            prompt_parts.append("")
        else:
            prompt_parts.append("User's tasks: None")
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
                        "content": "You are a helpful assistant for TaskGenius, a task management system. Provide concise, friendly responses.\n\nCRITICAL LANGUAGE RULES:\n- You MUST support Hebrew (עברית) and English\n- If the user writes in Hebrew, you MUST respond in Hebrew\n- If the user writes in English, respond in English\n- If the user mixes languages, respond in the same mix\n- Understand Hebrew slang, informal expressions, and common phrases\n- Examples of Hebrew task management phrases:\n  * 'מה המשימות שלי?' = 'What are my tasks?'\n  * 'תוסיף משימה' = 'Add a task'\n  * 'מה דחוף לי?' = 'What's urgent for me?'\n  * 'סמן כבוצע' = 'Mark as done'\n- Always match the user's language preference"
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
            
            # Extract reply from response
            reply = response.choices[0].message.content.strip()
            
            if not reply:
                logger.warning("Empty reply from LLM")
                return None
            
            # Determine intent from reply (simple heuristic, can be improved)
            intent = self._extract_intent_from_reply(reply, request.message)
            
            # Generate suggestions
            suggestions = self._generate_suggestions(intent, request)
            
            return ChatResponse(
                reply=reply,
                intent=intent,
                suggestions=suggestions
            )
            
        except Exception as e:
            logger.error(f"Error calling OpenAI API: {e}", exc_info=True)
            return None

    def _extract_intent_from_reply(self, reply: str, original_message: str) -> Optional[str]:
        """
        Extract intent from LLM reply and original message.
        Simple heuristic - can be improved in Phase 2.
        """
        message_lower = original_message.lower()
        reply_lower = reply.lower()
        
        # Check for common intents
        if any(word in message_lower for word in ["summary", "insights", "report", "weekly"]):
            return "get_insights"
        elif any(word in message_lower for word in ["list", "show", "tasks", "what"]):
            return "list_tasks"
        elif any(word in message_lower for word in ["create", "add", "new", "task"]):
            return "create_task"
        elif any(word in message_lower for word in ["help", "how", "what can"]):
            return "unknown"
        else:
            return "unknown"

    def _generate_suggestions(self, intent: Optional[str], request: ChatRequest) -> List[str]:
        """Generate suggestions based on intent."""
        if intent == "list_tasks":
            return ["View all tasks", "Filter by status", "Create new task"]
        elif intent == "get_insights":
            return ["View detailed summary", "Filter by category"]
        elif intent == "create_task":
            return ["Set deadline", "Add category", "Set priority"]
        else:
            return ["List tasks", "Create task", "Get help"]
