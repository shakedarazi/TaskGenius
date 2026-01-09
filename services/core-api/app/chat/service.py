"""
TASKGENIUS Core API - Chat Service

Service for orchestrating chat interactions with chatbot-service.
This service:
- Fetches user data from MongoDB (via repository)
- Calls chatbot-service with context
- Returns conversational response
- Never mutates state during chat flow
"""

import httpx
from typing import List, Dict, Any
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.config import settings
from app.tasks.repository import TaskRepositoryInterface
from app.tasks.schemas import TaskResponse
from app.insights.service import InsightsService
from app.chat.schemas import ChatResponse


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
            now = datetime.now(timezone.utc)
            summary = self.insights_service.generate_weekly_summary(tasks, now)
            weekly_summary_data = summary.model_dump()
        
        # Build request for chatbot-service
        chatbot_request = {
            "message": message,
            "user_id": user_id,
            "tasks": tasks_data,
            "weekly_summary": weekly_summary_data,
        }
        
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
                
                return ChatResponse(
                    reply=chatbot_response["reply"],
                    intent=chatbot_response.get("intent"),
                    suggestions=chatbot_response.get("suggestions"),
                )
            except httpx.HTTPError as e:
                # Fallback response if chatbot-service is unavailable
                return ChatResponse(
                    reply="I'm having trouble processing your request right now. Please try again later.",
                    intent="unknown",
                    suggestions=None,
                )
