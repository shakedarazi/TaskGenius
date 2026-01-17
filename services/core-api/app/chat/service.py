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
                
                # Phase 4: Execute add_task if command is present and ready
                if chatbot_response.get("command"):
                    from app.chat.schemas import Command
                    command_dict = chatbot_response["command"]
                    command = Command(**command_dict)
                    chat_response.command = command
                    
                    # Execute add_task if conditions are met
                    if command.intent == "add_task" and command.confidence >= 0.8 and command.ready:
                        if command.fields and command.fields.get("title"):
                            # Create task
                            from app.tasks.models import Task
                            from app.tasks.enums import TaskStatus, TaskPriority
                            from datetime import datetime
                            
                            # Parse priority
                            priority_str = command.fields.get("priority", "medium")
                            priority_map = {
                                "low": TaskPriority.LOW,
                                "medium": TaskPriority.MEDIUM,
                                "high": TaskPriority.HIGH,
                                "urgent": TaskPriority.URGENT,
                            }
                            priority = priority_map.get(priority_str.lower(), TaskPriority.MEDIUM)
                            
                            # Parse deadline if provided
                            deadline = None
                            if command.fields.get("deadline"):
                                try:
                                    deadline = datetime.fromisoformat(command.fields["deadline"].replace("Z", "+00:00"))
                                except (ValueError, AttributeError):
                                    deadline = None
                            
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
                            chat_response.intent = "create_task"
                            logger.info(f"Created task via chat: {created_task.id} for user {user_id}")
                        else:
                            # Missing title - should not happen if ready=true, but handle gracefully
                            logger.warning(f"Command ready but missing title: {command.fields}")
                    elif command.intent == "add_task" and command.confidence < 0.8:
                        # Low confidence - don't execute, reply already asks for clarification
                        logger.debug(f"Add task command has low confidence ({command.confidence}), not executing")
                
                return chat_response
            except httpx.HTTPError as e:
                # Fallback response if chatbot-service is unavailable
                return ChatResponse(
                    reply="I'm having trouble processing your request right now. Please try again later.",
                    intent="unknown",
                    suggestions=None,
                )
