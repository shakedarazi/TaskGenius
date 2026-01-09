"""
TASKGENIUS Chatbot Service - Interpret Tests

Phase 4: CI-safe tests for interpret endpoint.
"""

import pytest
from app.schemas import ChatRequest, ChatResponse
from app.service import ChatbotService


class TestChatbotService:
    """Tests for ChatbotService logic."""

    @pytest.fixture
    def service(self):
        """Create service instance."""
        return ChatbotService()

    async def test_list_tasks_intent(self, service):
        """Service should handle list tasks intent."""
        request = ChatRequest(
            message="list my tasks",
            user_id="test-user",
            tasks=[
                {"id": "1", "title": "Task 1", "status": "open", "priority": "high"},
                {"id": "2", "title": "Task 2", "status": "done", "priority": "medium"},
            ],
        )
        response = await service.generate_response(request)
        
        assert response.reply
        assert response.intent == "list_tasks"
        assert "2" in response.reply or "task" in response.reply.lower()

    async def test_insights_intent(self, service):
        """Service should handle insights intent."""
        request = ChatRequest(
            message="show me my weekly summary",
            user_id="test-user",
            weekly_summary={
                "completed": {"count": 3},
                "high_priority": {"count": 2},
                "upcoming": {"count": 1},
                "overdue": {"count": 0},
            },
        )
        response = await service.generate_response(request)
        
        assert response.reply
        assert response.intent == "get_insights"
        assert "summary" in response.reply.lower()

    async def test_create_task_intent(self, service):
        """Service should handle create task intent."""
        request = ChatRequest(
            message="create a new task",
            user_id="test-user",
        )
        response = await service.generate_response(request)
        
        assert response.reply
        assert response.intent == "create_task"

    async def test_help_intent(self, service):
        """Service should handle help intent."""
        request = ChatRequest(
            message="help",
            user_id="test-user",
        )
        response = await service.generate_response(request)
        
        assert response.reply
        assert "help" in response.reply.lower() or "can" in response.reply.lower()

    async def test_general_message(self, service):
        """Service should handle general/unclear messages."""
        request = ChatRequest(
            message="hello",
            user_id="test-user",
        )
        response = await service.generate_response(request)
        
        assert response.reply
        assert response.intent == "unknown"


class TestInterpretEndpoint:
    """Tests for /interpret endpoint."""

    def test_interpret_endpoint_requires_message(self, client):
        """Endpoint should require message field."""
        response = client.post("/interpret", json={})
        assert response.status_code == 422

    def test_interpret_endpoint_success(self, client):
        """Endpoint should return response."""
        request = {
            "message": "list my tasks",
            "user_id": "test-user",
            "tasks": [{"id": "1", "title": "Task 1", "status": "open", "priority": "high"}],
        }
        response = client.post("/interpret", json=request)
        
        assert response.status_code == 200
        data = response.json()
        assert "reply" in data
        assert "intent" in data

    def test_interpret_with_weekly_summary(self, client):
        """Endpoint should handle weekly summary in request."""
        request = {
            "message": "show summary",
            "user_id": "test-user",
            "weekly_summary": {
                "completed": {"count": 2},
                "high_priority": {"count": 1},
                "upcoming": {"count": 0},
                "overdue": {"count": 0},
            },
        }
        response = client.post("/interpret", json=request)
        
        assert response.status_code == 200
        data = response.json()
        assert "reply" in data
