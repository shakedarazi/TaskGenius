"""
TASKGENIUS Chatbot Service - Service

Business logic for generating conversational responses.
This is a read-only facade - no mutations or DB access.
"""

from typing import Optional
from app.schemas import ChatRequest, ChatResponse


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
        """
        message = request.message.lower().strip()

        # Simple rule-based responses for Phase 4
        # In future phases, this can use LLM
        
        # Check for common intents (order matters - check insights before list)
        if any(word in message for word in ["summary", "insights", "report", "weekly"]):
            return self._handle_insights(request)
        elif any(word in message for word in ["list", "show", "tasks", "what"]):
            return self._handle_list_tasks(request)
        elif any(word in message for word in ["create", "add", "new", "task"]):
            return self._handle_create_task(request)
        elif any(word in message for word in ["help", "how", "what can"]):
            return self._handle_help()
        else:
            return self._handle_general(request)

    def _handle_list_tasks(self, request: ChatRequest) -> ChatResponse:
        """Handle list tasks intent."""
        if request.tasks:
            count = len(request.tasks)
            if count == 0:
                reply = "You don't have any tasks yet. Would you like to create one?"
            else:
                reply = f"You have {count} task(s). "
                # List a few tasks
                task_titles = [t.get("title", "Untitled") for t in request.tasks[:3]]
                reply += "Here are some: " + ", ".join(task_titles)
                if count > 3:
                    reply += f", and {count - 3} more."
        else:
            reply = "I can help you list your tasks. Let me fetch them for you."
        
        return ChatResponse(
            reply=reply,
            intent="list_tasks",
            suggestions=["View all tasks", "Filter by status", "Create new task"]
        )

    def _handle_insights(self, request: ChatRequest) -> ChatResponse:
        """Handle insights/summary intent."""
        if request.weekly_summary:
            summary = request.weekly_summary
            completed = summary.get("completed", {}).get("count", 0)
            high_priority = summary.get("high_priority", {}).get("count", 0)
            upcoming = summary.get("upcoming", {}).get("count", 0)
            overdue = summary.get("overdue", {}).get("count", 0)
            
            reply = f"Here's your weekly summary: "
            reply += f"{completed} completed, "
            reply += f"{high_priority} high-priority open, "
            reply += f"{upcoming} upcoming, "
            reply += f"{overdue} overdue."
        else:
            reply = "I can generate a weekly summary for you. Let me fetch your insights."
        
        return ChatResponse(
            reply=reply,
            intent="get_insights",
            suggestions=["View detailed summary", "Filter by category"]
        )

    def _handle_create_task(self, request: ChatRequest) -> ChatResponse:
        """Handle create task intent."""
        reply = "I can help you create a task. Please provide: title, priority (low/medium/high/urgent), and optionally a deadline."
        return ChatResponse(
            reply=reply,
            intent="create_task",
            suggestions=["Set deadline", "Add category", "Set priority"]
        )

    def _handle_help(self) -> ChatResponse:
        """Handle help intent."""
        reply = "I can help you with: listing tasks, creating tasks, viewing weekly summaries, and answering questions about your tasks. What would you like to do?"
        return ChatResponse(
            reply=reply,
            intent="unknown",
            suggestions=["List tasks", "Create task", "View summary"]
        )

    def _handle_general(self, request: ChatRequest) -> ChatResponse:
        """Handle general/unclear messages."""
        reply = "I'm here to help you manage your tasks. You can ask me to list tasks, create new ones, or view your weekly summary. What would you like to do?"
        return ChatResponse(
            reply=reply,
            intent="unknown",
            suggestions=["List tasks", "Create task", "Get help"]
        )
