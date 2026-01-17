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
        
        # Check for update/delete/complete intents BEFORE create (more specific)
        elif any(word in message_lower for word in ["update", "change", "modify", "edit", "עדכן", "שנה", "ערוך"]):
            return self._handle_potential_update(request, is_hebrew)
        elif any(word in message_lower for word in ["delete", "remove", "מחק", "הסר"]):
            return self._handle_potential_delete(request, is_hebrew)
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
        # Check if title is mentioned (basic heuristic)
        message_words = request.message.split()
        has_title = any(len(word) > 3 for word in message_words if word.lower() not in ["create", "add", "new", "task", "צור", "הוסף", "תוסיף", "משימה"])
        
        if is_hebrew:
            if not has_title:
                replies = [
                    "אני מבין שאתה רוצה ליצור משימה. איזו משימה תרצה ליצור? תן לי כותרת.",
                    "בוא ניצור משימה חדשה! מה הכותרת של המשימה?",
                    "אני יכול לעזור לך ליצור משימה. מה תרצה להוסיף לרשימה?"
                ]
                reply = replies[hash(request.user_id + request.message) % len(replies)]
            else:
                replies = [
                    "מעולה! כדי להשלים את היצירה, אני צריך עוד כמה פרטים. מה העדיפות? (נמוכה/בינונית/גבוהה/דחופה) האם יש תאריך יעד?",
                    "טוב! כדי ליצור את המשימה, אני צריך לדעת: מה העדיפות? האם יש תאריך יעד?",
                    "נהדר! בוא נשלים את הפרטים: מה העדיפות? האם יש תאריך יעד?"
                ]
                reply = replies[hash(request.user_id + request.message) % len(replies)]
            suggestions = ["הגדר תאריך יעד", "הוסף קטגוריה", "הגדר עדיפות"]
        else:
            if not has_title:
                replies = [
                    "I understand you want to create a task. Which task would you like to create? Please provide a title.",
                    "Let's create a new task! What's the task title?",
                    "I can help you create a task. What would you like to add to your list?"
                ]
                reply = replies[hash(request.user_id + request.message) % len(replies)]
            else:
                replies = [
                    "Great! To complete the creation, I need a few more details. What's the priority? (low/medium/high/urgent) Is there a deadline?",
                    "Good! To create the task, I need to know: What's the priority? Is there a deadline?",
                    "Perfect! Let's complete the details: What's the priority? Is there a deadline?"
                ]
                reply = replies[hash(request.user_id + request.message) % len(replies)]
            suggestions = ["Set deadline", "Add category", "Set priority"]
        
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
                replies = [
                    "מעולה! מה תרצה לשנות במשימה? (עדיפות, תאריך יעד, סטטוס, וכו')",
                    "בוא נעדכן! מה תרצה לשנות? (עדיפות, תאריך יעד, סטטוס)",
                    "אני יכול לעזור לך לעדכן. מה תרצה לשנות? (עדיפות, תאריך יעד, סטטוס)"
                ]
                reply = replies[hash(request.user_id + request.message) % len(replies)]
            suggestions = ["שנה עדיפות", "שנה תאריך יעד", "שנה סטטוס"]
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
                replies = [
                    "Great! What would you like to change about the task? (priority, deadline, status, etc.)",
                    "Let's update! What would you like to change? (priority, deadline, status)",
                    "I can help you update. What would you like to change? (priority, deadline, status)"
                ]
                reply = replies[hash(request.user_id + request.message) % len(replies)]
            suggestions = ["Change priority", "Change deadline", "Change status"]
        
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
        
        if is_hebrew:
            if not task_mentioned:
                if len(request.tasks) == 1:
                    reply = f"אני מבין שאתה רוצה למחוק משימה. האם אתה מתכוון ל'{request.tasks[0].get('title', 'המשימה')}'? זה ימחק את המשימה לצמיתות."
                else:
                    reply = f"אני מבין שאתה רוצה למחוק משימה. איזו משימה? יש לך {len(request.tasks)} משימות. אנא ציין את שם המשימה."
                    task_list = ", ".join([t.get("title", "ללא כותרת") for t in request.tasks[:5]])
                    reply += f" המשימות שלך: {task_list}"
            else:
                reply = "אני מבין שאתה רוצה למחוק משימה. זה ימחק את המשימה לצמיתות. האם אתה בטוח?"
            suggestions = ["אשר מחיקה", "בטל", "ראה את כל המשימות"]
        else:
            if not task_mentioned:
                if len(request.tasks) == 1:
                    reply = f"I understand you want to delete a task. Do you mean '{request.tasks[0].get('title', 'the task')}'? This will permanently delete the task."
                else:
                    reply = f"I understand you want to delete a task. Which task? You have {len(request.tasks)} tasks. Please specify the task name."
                    task_list = ", ".join([t.get("title", "Untitled") for t in request.tasks[:5]])
                    reply += f" Your tasks: {task_list}"
            else:
                reply = "I understand you want to delete a task. This will permanently delete the task. Are you sure?"
            suggestions = ["Confirm deletion", "Cancel", "View all tasks"]
        
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
            "",
            f"User's message: {request.message}",
            ""
        ]
        
        # Add tasks context
        if request.tasks:
            prompt_parts.append("User's tasks (REFER TO THESE WHEN RELEVANT):")
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
            prompt_parts.append("IMPORTANT: When the user mentions tasks, refer to them by title. If they mention 'tomorrow', 'urgent', 'high priority', etc., filter the tasks accordingly.")
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
            
            # Extract reply from response
            reply = response.choices[0].message.content.strip()
            
            if not reply:
                logger.warning("Empty reply from LLM")
                return None
            
            # Determine intent from original message (more reliable than extracting from reply)
            # Use the original message to detect intent, as it's more accurate
            intent = self._extract_intent_from_message(request.message, request)
            
            # Generate suggestions based on intent
            suggestions = self._generate_suggestions(intent, request)
            
            return ChatResponse(
                reply=reply,
                intent=intent,
                suggestions=suggestions
            )
            
        except Exception as e:
            logger.error(f"Error calling OpenAI API: {e}", exc_info=True)
            return None

    def _extract_intent_from_message(self, message: str, request: ChatRequest) -> Optional[str]:
        """
        Extract intent from user message (more reliable than extracting from LLM reply).
        Phase 2: Improved intent detection with potential_* intents.
        """
        message_lower = message.lower()
        
        # Check for task insights (deadlines, priorities, urgency) - highest priority
        if any(word in message_lower for word in ["summary", "insights", "report", "weekly", "סיכום", "דוח"]):
            return "get_insights"
        elif any(word in message_lower for word in ["urgent", "priority", "deadline", "due", "דחוף", "עדיפות", "תאריך"]):
            return "task_insights"
        
        # Check for update/delete/complete intents BEFORE create (more specific)
        elif any(word in message_lower for word in ["update", "change", "modify", "edit", "עדכן", "שנה", "ערוך", "עדכן"]):
            return "potential_update"
        elif any(word in message_lower for word in ["delete", "remove", "מחק", "הסר"]):
            return "potential_delete"
        elif any(word in message_lower for word in ["complete", "done", "finish", "בוצע", "סיים", "סיימתי"]):
            return "potential_update"
        
        # Check for list tasks
        elif any(word in message_lower for word in ["list", "show", "tasks", "what", "רשימה", "הצג", "מה"]):
            return "list_tasks"
        
        # Check for create intent (potential - needs clarification) - last, as "task" is common
        elif any(word in message_lower for word in ["create", "add", "new", "צור", "הוסף", "תוסיף", "רוצה להוסיף", "רוצה ליצור"]):
            return "potential_create"
        
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
