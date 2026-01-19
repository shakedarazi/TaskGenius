"""
TASKGENIUS Core API - Chat Service

Service for orchestrating chat interactions with chatbot-service.
This service:
- Fetches user data from MongoDB (via repository)
- Calls chatbot-service with context
- Returns conversational response
- Never mutates state during chat flow
"""

import logging
import httpx
from typing import List, Dict, Any, Optional
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.config import settings
from app.tasks.repository import TaskRepositoryInterface
from app.tasks.schemas import TaskResponse
from app.insights.service import InsightsService
from app.chat.schemas import ChatResponse

logger = logging.getLogger(__name__)


class ChatService:
    """
    Service for chat orchestration.
    
    Orchestrates:
    - Data fetching from MongoDB (via repository)
    - Communication with chatbot-service
    - Response formatting
    """

    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.chatbot_service_url = settings.CHATBOT_SERVICE_URL
        self.task_repository = None  # Will be injected
        self.insights_service = InsightsService()

    async def process_message(
        self,
        user_id: str,
        message: str,
        task_repository: TaskRepositoryInterface,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> ChatResponse:
        """
        Process a chat message by:
        1. Fetching user's tasks
        2. Optionally fetching weekly summary if requested
        3. Calling chatbot-service with context
        4. Returning response
        
        Args:
            user_id: Authenticated user ID
            message: User's chat message
            task_repository: Task repository for fetching user tasks
        
        Returns:
            ChatResponse from chatbot-service
        """
        # Fetch user's tasks (ownership enforced by repository)
        tasks = await task_repository.list_by_owner(user_id)
        
        # Convert tasks to dict format for chatbot-service
        tasks_data = []
        for task in tasks:
            tasks_data.append({
                "id": task.id,
                "title": task.title,
                "status": task.status.value,
                "priority": task.priority.value,
                "deadline": task.deadline.isoformat() if task.deadline else None,
            })
        
        # Check if user is asking for insights/summary
        message_lower = message.lower()
        weekly_summary_data = None
        if any(word in message_lower for word in ["summary", "insights", "report", "weekly"]):
            # Generate weekly summary
            from datetime import datetime, timezone
            import json
            now = datetime.now(timezone.utc)
            summary = self.insights_service.generate_weekly_summary(tasks, now)
            # Convert to JSON string and back to dict to ensure datetime serialization
            weekly_summary_data = json.loads(summary.model_dump_json())
        
        # Build request for chatbot-service
        chatbot_request = {
            "message": message,
            "user_id": user_id,
            "tasks": tasks_data,
            "weekly_summary": weekly_summary_data,
        }
        
        # Add conversation history if provided
        if conversation_history:
            chatbot_request["conversation_history"] = conversation_history
        
        # Call chatbot-service
        tasks_count = len(tasks_data) if tasks_data else 0
        conversation_history_count = len(conversation_history) if conversation_history else 0
        logger.info(f"Calling chatbot-service: user_id={user_id}, tasks_count={tasks_count}, conversation_history_count={conversation_history_count}")
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.chatbot_service_url}/interpret",
                    json=chatbot_request,
                    timeout=10.0,
                )
                response.raise_for_status()
                chatbot_response = response.json()  # httpx response.json() is synchronous
                
                # Build ChatResponse with command (Phase 3/4)
                chat_response = ChatResponse(
                    reply=chatbot_response["reply"],
                    intent=chatbot_response.get("intent"),
                    suggestions=chatbot_response.get("suggestions"),
                )
                
                # PHASE 0: Set intent from command (removed intent rewriting hacks)
                if chatbot_response.get("command"):
                    from app.chat.schemas import Command
                    command_dict = chatbot_response["command"]
                    command = Command(**command_dict)
                    chat_response.command = command
                    
                    # Set response.intent = command.intent if command exists
                    # This ensures consistent intent propagation from chatbot-service to frontend
                    if command.intent:
                        chat_response.intent = command.intent
                    
                    # Execute add_task if conditions are met
                    if command.intent == "add_task" and command.confidence >= 0.8 and command.ready:
                        if command.fields and command.fields.get("title") and command.fields.get("priority"):
                            # Create task
                            from app.tasks.models import Task
                            from app.tasks.enums import TaskStatus, TaskPriority
                            from datetime import datetime
                            
                            # Parse priority (required field)
                            priority_str = command.fields.get("priority", "").lower()
                            priority_map = {
                                "low": TaskPriority.LOW,
                                "medium": TaskPriority.MEDIUM,
                                "high": TaskPriority.HIGH,
                                "urgent": TaskPriority.URGENT,
                                "נמוכה": TaskPriority.LOW,
                                "בינונית": TaskPriority.MEDIUM,
                                "גבוהה": TaskPriority.HIGH,
                                "דחופה": TaskPriority.URGENT,
                            }
                            priority = priority_map.get(priority_str, TaskPriority.MEDIUM)
                            
                            # Parse deadline if provided (Rule 1, 3: Validate format)
                            deadline = None
                            deadline_value = command.fields.get("deadline")
                            if deadline_value:
                                try:
                                    # Rule 3: Must be valid ISO format (validated by chatbot-service, but double-check here)
                                    deadline = datetime.fromisoformat(deadline_value.replace("Z", "+00:00"))
                                except (ValueError, AttributeError):
                                    # Invalid format - reject execution (Rule 3)
                                    logger.warning(f"Invalid deadline format from chatbot: {deadline_value}")
                                    is_hebrew = any('\u0590' <= char <= '\u05FF' for char in message)
                                    if is_hebrew:
                                        chat_response.reply = "❌ שגיאה: תאריך היעד לא תקין. אנא תן תאריך בפורמט מספרי (למשל: 2024-01-20)."
                                    else:
                                        chat_response.reply = "❌ Error: Invalid deadline format. Please provide a date in numeric format (e.g., 2024-01-20)."
                                    chat_response.intent = "error"
                                    return chat_response
                            
                            # Create task
                            new_task = Task.create(
                                owner_id=user_id,
                                title=command.fields["title"],
                                status=TaskStatus.OPEN,
                                priority=priority,
                                deadline=deadline,
                            )
                            
                            # Save to database
                            created_task = await task_repository.create(new_task)
                            
                            # Update reply to confirm creation
                            is_hebrew = any('\u0590' <= char <= '\u05FF' for char in message)
                            if is_hebrew:
                                chat_response.reply = f"✅ הוספתי משימה: '{created_task.title}'"
                            else:
                                chat_response.reply = f"✅ Added task: '{created_task.title}'"
                            # Intent already set above, but ensure it's create_task after successful execution
                            chat_response.intent = "create_task"
                            logger.info(f"Created task via chat: {created_task.id} for user {user_id}")
                        else:
                            # Missing required fields - should not happen if ready=true, but handle gracefully
                            missing = []
                            if not command.fields or not command.fields.get("title"):
                                missing.append("title")
                            if not command.fields or not command.fields.get("priority"):
                                missing.append("priority")
                            logger.warning(f"Command ready but missing required fields: {missing}. Fields: {command.fields}")
                            # Update reply to ask for missing fields
                            is_hebrew = any('\u0590' <= char <= '\u05FF' for char in message)
                            if is_hebrew:
                                if "title" in missing:
                                    chat_response.reply = "אני צריך כותרת למשימה. מה הכותרת?"
                                elif "priority" in missing:
                                    chat_response.reply = "אני צריך עדיפות למשימה. מה העדיפות? (נמוכה/בינונית/גבוהה/דחופה)"
                            else:
                                if "title" in missing:
                                    chat_response.reply = "I need a title for the task. What's the title?"
                                elif "priority" in missing:
                                    chat_response.reply = "I need a priority for the task. What's the priority? (low/medium/high/urgent)"
                    elif command.intent == "add_task" and command.confidence < 0.8:
                        # Low confidence - don't execute, reply already asks for clarification
                        logger.debug(f"Add task command has low confidence ({command.confidence}), not executing")
                    
                    # Rule 8: Execute update_task if conditions are met
                    elif command.intent == "update_task" and command.confidence >= 0.8 and command.ready:
                        from app.tasks.models import Task
                        from app.tasks.enums import TaskStatus, TaskPriority
                        from datetime import datetime
                        
                        if not command.ref:
                            logger.warning("Update task command missing ref (task_id or title)")
                            is_hebrew = any('\u0590' <= char <= '\u05FF' for char in message)
                            if is_hebrew:
                                chat_response.reply = "❌ שגיאה: לא זיהיתי איזו משימה לעדכן. אנא ציין את שם המשימה."
                            else:
                                chat_response.reply = "❌ Error: Could not identify which task to update. Please specify the task name."
                            chat_response.intent = "error"
                            return chat_response
                        
                        # Find task by ID or title
                        task_id = command.ref.get("task_id")
                        task_title = command.ref.get("title")
                        
                        if not task_id and not task_title:
                            logger.warning("Update task command missing both task_id and title in ref")
                            is_hebrew = any('\u0590' <= char <= '\u05FF' for char in message)
                            if is_hebrew:
                                chat_response.reply = "❌ שגיאה: לא זיהיתי איזו משימה לעדכן."
                            else:
                                chat_response.reply = "❌ Error: Could not identify which task to update."
                            chat_response.intent = "error"
                            return chat_response
                        
                        # Get task
                        if task_id:
                            task = await task_repository.get_by_id(task_id, user_id)
                        else:
                            # Find by title
                            tasks = await task_repository.list_by_owner(user_id)
                            task = None
                            for t in tasks:
                                if t.title.lower() == task_title.lower():
                                    task = t
                                    break
                        
                        if not task:
                            logger.warning(f"Task not found for update: id={task_id}, title={task_title}")
                            is_hebrew = any('\u0590' <= char <= '\u05FF' for char in message)
                            if is_hebrew:
                                chat_response.reply = "❌ שגיאה: לא מצאתי את המשימה לעדכון."
                            else:
                                chat_response.reply = "❌ Error: Task not found for update."
                            chat_response.intent = "error"
                            return chat_response
                        
                        # Build updates dict (only non-None fields from command.fields)
                        updates = {}
                        if command.fields:
                            if command.fields.get("title"):
                                updates["title"] = command.fields["title"]
                            if command.fields.get("priority"):
                                priority_str = command.fields.get("priority", "").lower()
                                priority_map = {
                                    "low": TaskPriority.LOW,
                                    "medium": TaskPriority.MEDIUM,
                                    "high": TaskPriority.HIGH,
                                    "urgent": TaskPriority.URGENT,
                                    "נמוכה": TaskPriority.LOW,
                                    "בינונית": TaskPriority.MEDIUM,
                                    "גבוהה": TaskPriority.HIGH,
                                    "דחופה": TaskPriority.URGENT,
                                }
                                priority = priority_map.get(priority_str, TaskPriority.MEDIUM)
                                updates["priority"] = priority.value
                            
                            # Parse deadline if provided (Rule 1, 3: Validate format)
                            deadline_value = command.fields.get("deadline")
                            if deadline_value:
                                try:
                                    deadline = datetime.fromisoformat(deadline_value.replace("Z", "+00:00"))
                                    updates["deadline"] = deadline
                                except (ValueError, AttributeError):
                                    logger.warning(f"Invalid deadline format in update: {deadline_value}")
                                    is_hebrew = any('\u0590' <= char <= '\u05FF' for char in message)
                                    if is_hebrew:
                                        chat_response.reply = "❌ שגיאה: תאריך היעד לא תקין. אנא תן תאריך בפורמט מספרי."
                                    else:
                                        chat_response.reply = "❌ Error: Invalid deadline format. Please provide a date in numeric format."
                                    chat_response.intent = "error"
                                    return chat_response
                            elif "deadline" in command.fields and command.fields["deadline"] is None:
                                # Explicit null - clear deadline
                                updates["deadline"] = None
                        
                        if not updates:
                            logger.warning("Update task command has no fields to update")
                            is_hebrew = any('\u0590' <= char <= '\u05FF' for char in message)
                            if is_hebrew:
                                chat_response.reply = "❌ שגיאה: לא צוינו שדות לעדכון."
                            else:
                                chat_response.reply = "❌ Error: No fields specified for update."
                            chat_response.intent = "error"
                            return chat_response
                        
                        # Update task
                        updated_task = await task_repository.update(task.id, user_id, updates)
                        
                        if not updated_task:
                            logger.error(f"Failed to update task {task.id} for user {user_id}")
                            is_hebrew = any('\u0590' <= char <= '\u05FF' for char in message)
                            if is_hebrew:
                                chat_response.reply = "❌ שגיאה: לא הצלחתי לעדכן את המשימה."
                            else:
                                chat_response.reply = "❌ Error: Failed to update task."
                            chat_response.intent = "error"
                            return chat_response
                        
                        # Update reply to confirm update
                        is_hebrew = any('\u0590' <= char <= '\u05FF' for char in message)
                        if is_hebrew:
                            chat_response.reply = f"✅ עדכנתי משימה: '{updated_task.title}'"
                        else:
                            chat_response.reply = f"✅ Updated task: '{updated_task.title}'"
                        # Intent already set above, but ensure it's update_task after successful execution
                        chat_response.intent = "update_task"
                        logger.info(f"Updated task via chat: {updated_task.id} for user {user_id}")
                    
                    # Rule 9: Execute delete_task if conditions are met
                    elif command.intent == "delete_task" and command.confidence >= 0.8 and command.ready:
                        if not command.ref:
                            logger.warning("Delete task command missing ref (task_id or title)")
                            is_hebrew = any('\u0590' <= char <= '\u05FF' for char in message)
                            if is_hebrew:
                                chat_response.reply = "❌ שגיאה: לא זיהיתי איזו משימה למחוק."
                            else:
                                chat_response.reply = "❌ Error: Could not identify which task to delete."
                            chat_response.intent = "error"
                            return chat_response
                        
                        # Find task by ID or title
                        task_id = command.ref.get("task_id")
                        task_title = command.ref.get("title")
                        
                        if not task_id and not task_title:
                            logger.warning("Delete task command missing both task_id and title in ref")
                            is_hebrew = any('\u0590' <= char <= '\u05FF' for char in message)
                            if is_hebrew:
                                chat_response.reply = "❌ שגיאה: לא זיהיתי איזו משימה למחוק."
                            else:
                                chat_response.reply = "❌ Error: Could not identify which task to delete."
                            chat_response.intent = "error"
                            return chat_response
                        
                        # Get task
                        if task_id:
                            task = await task_repository.get_by_id(task_id, user_id)
                        else:
                            # Find by title
                            tasks = await task_repository.list_by_owner(user_id)
                            task = None
                            for t in tasks:
                                if t.title.lower() == task_title.lower():
                                    task = t
                                    break
                        
                        if not task:
                            logger.warning(f"Task not found for delete: id={task_id}, title={task_title}")
                            is_hebrew = any('\u0590' <= char <= '\u05FF' for char in message)
                            if is_hebrew:
                                chat_response.reply = "❌ שגיאה: לא מצאתי את המשימה למחיקה."
                            else:
                                chat_response.reply = "❌ Error: Task not found for deletion."
                            chat_response.intent = "error"
                            return chat_response
                        
                        # Delete task
                        deleted = await task_repository.delete(task.id, user_id)
                        
                        if not deleted:
                            logger.error(f"Failed to delete task {task.id} for user {user_id}")
                            is_hebrew = any('\u0590' <= char <= '\u05FF' for char in message)
                            if is_hebrew:
                                chat_response.reply = "❌ שגיאה: לא הצלחתי למחוק את המשימה."
                            else:
                                chat_response.reply = "❌ Error: Failed to delete task."
                            chat_response.intent = "error"
                            return chat_response
                        
                        # Update reply to confirm deletion
                        is_hebrew = any('\u0590' <= char <= '\u05FF' for char in message)
                        if is_hebrew:
                            chat_response.reply = f"✅ מחקתי משימה: '{task.title}'"
                        else:
                            chat_response.reply = f"✅ Deleted task: '{task.title}'"
                        # Intent already set above, but ensure it's delete_task after successful execution
                        chat_response.intent = "delete_task"
                        logger.info(f"Deleted task via chat: {task.id} for user {user_id}")
                
                return chat_response
            except httpx.HTTPError as e:
                # Fallback response if chatbot-service is unavailable
                return ChatResponse(
                    reply="I'm having trouble processing your request right now. Please try again later.",
                    intent="unknown",
                    suggestions=None,
                )
