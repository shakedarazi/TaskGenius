"""
Chatbot Service - Suggestion Tests
Minimal tests for suggestion-only architecture.
"""
import pytest
from app.schemas import SuggestRequest, SuggestResponse, TaskSuggestion
from app.service import generate_suggestions, fallback_response, build_prompt, parse_response


class TestSuggestionService:
    """Tests for suggestion generation."""

    async def test_fallback_returns_suggestions(self):
        """Fallback should return valid suggestions."""
        response = fallback_response("test message")
        
        assert response.summary
        assert len(response.suggestions) >= 3
        for s in response.suggestions:
            assert s.title
            assert s.priority in ["low", "medium", "high", "urgent"]

    async def test_fallback_hebrew_detection(self):
        """Fallback should detect Hebrew and respond in Hebrew."""
        response = fallback_response("שלום עולם")
        
        assert any('\u0590' <= c <= '\u05FF' for c in response.summary)

    async def test_fallback_english_response(self):
        """Fallback should respond in English for English input."""
        response = fallback_response("hello world")
        
        assert not any('\u0590' <= c <= '\u05FF' for c in response.summary)

    async def test_generate_suggestions_without_llm(self, monkeypatch):
        """Should use fallback when LLM is disabled."""
        monkeypatch.setattr("app.service.settings.USE_LLM", False)
        
        response = await generate_suggestions(
            message="test message",
            user_id="test-user",
        )
        
        assert response.summary
        assert len(response.suggestions) >= 3

    def test_build_prompt_includes_message(self):
        """Prompt should include user message."""
        prompt = build_prompt("test task", None)
        
        assert "test task" in prompt

    def test_build_prompt_includes_tasks(self):
        """Prompt should include existing tasks for context."""
        tasks = [{"title": "Existing Task"}, {"title": "Another Task"}]
        prompt = build_prompt("new task", tasks)
        
        assert "Existing Task" in prompt
        assert "Another Task" in prompt

    def test_parse_response_valid_json(self):
        """Should parse valid JSON response."""
        content = '{"summary": "test", "suggestions": [{"title": "Task", "priority": "high"}]}'
        result = parse_response(content)
        
        assert result["summary"] == "test"
        assert len(result["suggestions"]) == 1

    def test_parse_response_with_markdown(self):
        """Should handle JSON wrapped in markdown."""
        content = '```json\n{"summary": "test", "suggestions": []}\n```'
        result = parse_response(content)
        
        assert result["summary"] == "test"

    def test_parse_response_invalid_json(self):
        """Should return None for invalid JSON."""
        result = parse_response("not json")
        
        assert result is None


class TestInterpretEndpoint:
    """Tests for /interpret endpoint."""

    def test_interpret_requires_message(self, client):
        """Endpoint should require message field."""
        response = client.post("/interpret", json={"user_id": "test"})
        assert response.status_code == 422

    def test_interpret_requires_user_id(self, client):
        """Endpoint should require user_id field."""
        response = client.post("/interpret", json={"message": "test"})
        assert response.status_code == 422

    def test_interpret_returns_suggestions(self, client):
        """Endpoint should return summary and suggestions."""
        response = client.post("/interpret", json={
            "message": "I need to prepare for a meeting",
            "user_id": "test-user",
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "summary" in data
        assert "suggestions" in data
        assert len(data["suggestions"]) >= 3

    def test_interpret_empty_message_rejected(self, client):
        """Endpoint should reject empty message."""
        response = client.post("/interpret", json={
            "message": "",
            "user_id": "test-user",
        })
        assert response.status_code == 422

    def test_interpret_with_existing_tasks(self, client):
        """Endpoint should accept existing tasks for context."""
        response = client.post("/interpret", json={
            "message": "more tasks please",
            "user_id": "test-user",
            "tasks": [{"id": "1", "title": "Existing Task", "priority": "high"}],
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "suggestions" in data

    def test_interpret_long_message_accepted(self, client):
        """Endpoint should accept messages up to 1000 chars."""
        response = client.post("/interpret", json={
            "message": "task " * 200,  # ~1000 chars
            "user_id": "test-user",
        })
        assert response.status_code == 200

    def test_interpret_too_long_message_rejected(self, client):
        """Endpoint should reject messages over 1000 chars."""
        response = client.post("/interpret", json={
            "message": "a" * 1001,
            "user_id": "test-user",
        })
        assert response.status_code == 422
