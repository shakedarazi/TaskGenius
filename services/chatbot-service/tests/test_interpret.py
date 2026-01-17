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
        """Service should handle potential create task intent (Phase 2)."""
        request = ChatRequest(
            message="create a new task",
            user_id="test-user",
        )
        response = await service.generate_response(request)
        
        assert response.reply
        # Phase 2: Returns potential_create (needs clarification)
        assert response.intent == "potential_create"

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

    async def test_empty_message_raises_validation_error(self, service):
        """Service should raise validation error for empty message."""
        # Pydantic validation catches this before service logic
        with pytest.raises(Exception):  # Pydantic ValidationError
            request = ChatRequest(
                message="",
                user_id="test-user",
            )

    async def test_empty_user_id_raises_validation_error(self, service):
        """Service should raise validation error for empty user_id."""
        # Pydantic validation catches this before service logic
        with pytest.raises(Exception):  # Pydantic ValidationError
            request = ChatRequest(
                message="hello",
                user_id="",
            )

    async def test_response_always_has_reply(self, service):
        """Service should always return a reply."""
        request = ChatRequest(
            message="test message",
            user_id="test-user",
        )
        response = await service.generate_response(request)
        
        assert response.reply
        assert len(response.reply) > 0

    async def test_response_with_empty_tasks(self, service):
        """Service should handle empty tasks list."""
        request = ChatRequest(
            message="list my tasks",
            user_id="test-user",
            tasks=[],
        )
        response = await service.generate_response(request)
        
        assert response.reply
        assert response.intent == "list_tasks"
        # Empty tasks list should trigger the "don't have any" message
        assert "don't have any" in response.reply.lower() or "0" in response.reply or "fetch" in response.reply.lower()


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

    def test_interpret_endpoint_empty_message(self, client):
        """Endpoint should reject empty message."""
        request = {
            "message": "",
            "user_id": "test-user",
        }
        response = client.post("/interpret", json=request)
        assert response.status_code == 422  # Validation error

    def test_interpret_endpoint_whitespace_message(self, client):
        """Endpoint should reject whitespace-only message."""
        request = {
            "message": "   ",
            "user_id": "test-user",
        }
        response = client.post("/interpret", json=request)
        assert response.status_code == 422  # Validation error

    def test_interpret_endpoint_empty_user_id(self, client):
        """Endpoint should reject empty user_id."""
        request = {
            "message": "list tasks",
            "user_id": "",
        }
        response = client.post("/interpret", json=request)
        assert response.status_code == 422  # Validation error

    def test_interpret_endpoint_long_message(self, client):
        """Endpoint should handle long messages (within limit)."""
        long_message = "list " * 200  # ~1000 chars
        request = {
            "message": long_message,
            "user_id": "test-user",
        }
        response = client.post("/interpret", json=request)
        assert response.status_code == 200

    def test_interpret_endpoint_very_long_message(self, client):
        """Endpoint should reject very long messages."""
        very_long_message = "a" * 1001  # Over limit
        request = {
            "message": very_long_message,
            "user_id": "test-user",
        }
        response = client.post("/interpret", json=request)
        assert response.status_code == 422  # Validation error

    def test_interpret_endpoint_missing_fields(self, client):
        """Endpoint should require all required fields."""
        # Missing message
        response = client.post("/interpret", json={"user_id": "test-user"})
        assert response.status_code == 422
        
        # Missing user_id
        response = client.post("/interpret", json={"message": "hello"})
        assert response.status_code == 422


class TestLLMIntegration:
    """Tests for LLM integration (Phase 1)."""

    @pytest.fixture
    def service(self):
        """Create service instance."""
        return ChatbotService()

    async def test_llm_fallback_when_disabled(self, service, monkeypatch):
        """Service should use rule-based when USE_LLM is False."""
        # Mock settings to disable LLM
        monkeypatch.setattr("app.service.settings.USE_LLM", False)
        
        request = ChatRequest(
            message="list my tasks",
            user_id="test-user",
            tasks=[{"id": "1", "title": "Task 1", "status": "open", "priority": "high"}],
        )
        response = await service.generate_response(request)
        
        # Should use rule-based logic
        assert response.reply
        assert response.intent == "list_tasks"
        assert "1" in response.reply or "task" in response.reply.lower()

    async def test_llm_fallback_when_no_api_key(self, service, monkeypatch):
        """Service should fallback to rule-based when API key is missing."""
        # Mock settings to enable LLM but no API key
        monkeypatch.setattr("app.service.settings.USE_LLM", True)
        monkeypatch.setattr("app.service.settings.OPENAI_API_KEY", None)
        
        request = ChatRequest(
            message="list my tasks",
            user_id="test-user",
            tasks=[{"id": "1", "title": "Task 1", "status": "open", "priority": "high"}],
        )
        response = await service.generate_response(request)
        
        # Should fallback to rule-based
        assert response.reply
        assert response.intent == "list_tasks"

    async def test_llm_fallback_on_error(self, service, monkeypatch):
        """Service should fallback to rule-based when LLM call fails."""
        # Create a mock that raises exception
        class MockCompletions:
            async def create(self, *args, **kwargs):
                raise Exception("API Error")
        
        class MockChat:
            completions = MockCompletions()
        
        class MockClient:
            chat = MockChat()
        
        service._openai_client = MockClient()
        monkeypatch.setattr("app.service.settings.USE_LLM", True)
        monkeypatch.setattr("app.service.settings.OPENAI_API_KEY", "test-key")
        
        request = ChatRequest(
            message="list my tasks",
            user_id="test-user",
            tasks=[{"id": "1", "title": "Task 1", "status": "open", "priority": "high"}],
        )
        response = await service.generate_response(request)
        
        # Should fallback to rule-based
        assert response.reply
        assert response.intent == "list_tasks"

    async def test_prompt_building(self, service):
        """Test that prompt is built correctly."""
        request = ChatRequest(
            message="What are my tasks?",
            user_id="test-user",
            tasks=[
                {"id": "1", "title": "Task 1", "status": "open", "priority": "high", "deadline": "2024-01-15"},
                {"id": "2", "title": "Task 2", "status": "done", "priority": "medium", "deadline": None},
            ],
            weekly_summary={
                "completed": {"count": 1},
                "high_priority": {"count": 1},
                "upcoming": {"count": 0},
                "overdue": {"count": 0},
            },
        )
        
        prompt = service._build_prompt(request)
        
        assert "What are my tasks?" in prompt
        assert "Task 1" in prompt
        assert "Task 2" in prompt
        assert "Completed: 1" in prompt
        assert "High priority: 1" in prompt


class TestPhase2IntentQuality:
    """Tests for Phase 2: Intent Quality & Task-Aware Reasoning."""

    @pytest.fixture
    def service(self):
        """Create service instance."""
        return ChatbotService()

    async def test_potential_create_asks_for_title(self, service):
        """Service should ask for title when create intent is incomplete."""
        request = ChatRequest(
            message="add task",
            user_id="test-user",
        )
        response = await service.generate_response(request)
        
        assert response.reply
        assert response.intent == "potential_create"
        assert "title" in response.reply.lower() or "כותרת" in response.reply

    async def test_potential_update_asks_for_task(self, service):
        """Service should ask which task to update when ambiguous."""
        request = ChatRequest(
            message="update task",
            user_id="test-user",
            tasks=[
                {"id": "1", "title": "Task 1", "status": "open", "priority": "high"},
                {"id": "2", "title": "Task 2", "status": "open", "priority": "medium"},
            ],
        )
        response = await service.generate_response(request)
        
        assert response.reply
        assert response.intent == "potential_update"
        assert "which" in response.reply.lower() or "איזו" in response.reply or "איזה" in response.reply

    async def test_potential_delete_asks_for_confirmation(self, service):
        """Service should ask for confirmation when delete intent is detected."""
        request = ChatRequest(
            message="delete task",
            user_id="test-user",
            tasks=[
                {"id": "1", "title": "Task 1", "status": "open", "priority": "high"},
            ],
        )
        response = await service.generate_response(request)
        
        assert response.reply
        assert response.intent == "potential_delete"
        # Check for confirmation-related words (delete, permanently, sure, confirm, etc.)
        reply_lower = response.reply.lower()
        assert any(word in reply_lower for word in ["delete", "permanently", "sure", "confirm", "בטוח", "מחיקה"])

    async def test_task_insights_analyzes_tasks(self, service):
        """Service should provide insights about tasks (deadlines, priorities)."""
        request = ChatRequest(
            message="what's urgent for me?",
            user_id="test-user",
            tasks=[
                {"id": "1", "title": "Urgent Task", "status": "open", "priority": "high"},
                {"id": "2", "title": "Normal Task", "status": "open", "priority": "low"},
            ],
        )
        response = await service.generate_response(request)
        
        assert response.reply
        assert response.intent == "task_insights"
        assert "urgent" in response.reply.lower() or "דחוף" in response.reply or "priority" in response.reply.lower()

    async def test_task_insights_with_no_tasks(self, service):
        """Service should handle task insights request when no tasks exist."""
        request = ChatRequest(
            message="what's urgent?",
            user_id="test-user",
            tasks=[],
        )
        response = await service.generate_response(request)
        
        assert response.reply
        assert response.intent == "task_insights"
