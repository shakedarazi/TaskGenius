"""
Core API - Chat Tests
Tests for suggestion-based chat endpoint.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.chat.service import (
    get_cached_suggestions,
    set_cached_suggestions,
    clear_cached_suggestions,
    format_reply,
)


class TestSuggestionCache:
    """Tests for suggestion caching."""

    def test_cache_set_and_get(self):
        """Should store and retrieve suggestions."""
        suggestions = [{"title": "Task 1", "priority": "high"}]
        set_cached_suggestions("user-1", suggestions)
        
        cached = get_cached_suggestions("user-1")
        assert cached == suggestions

    def test_cache_clear(self):
        """Should clear suggestions after retrieval."""
        suggestions = [{"title": "Task 1", "priority": "high"}]
        set_cached_suggestions("user-1", suggestions)
        clear_cached_suggestions("user-1")
        
        cached = get_cached_suggestions("user-1")
        assert cached is None

    def test_cache_isolation(self):
        """Suggestions should be isolated per user."""
        set_cached_suggestions("user-1", [{"title": "Task 1"}])
        set_cached_suggestions("user-2", [{"title": "Task 2"}])
        
        assert get_cached_suggestions("user-1")[0]["title"] == "Task 1"
        assert get_cached_suggestions("user-2")[0]["title"] == "Task 2"


class TestFormatReply:
    """Tests for reply formatting."""

    def test_format_english(self):
        """Should format reply with summary + CTA only (no numbered list)."""
        suggestions = [
            {"title": "Task 1", "priority": "high"},
            {"title": "Task 2", "priority": "low"},
        ]
        reply = format_reply("Here are your tasks.", suggestions, is_hebrew=False)
        
        assert "Here are your tasks." in reply
        assert "Choose 1-2 to add" in reply
        # Numbered list should NOT be in reply (rendered by UI instead)
        assert "1. Task 1" not in reply

    def test_format_hebrew(self):
        """Should format reply with summary + CTA only (Hebrew)."""
        suggestions = [
            {"title": "משימה 1", "priority": "high"},
        ]
        reply = format_reply("הנה המשימות שלך.", suggestions, is_hebrew=True)
        
        assert "הנה המשימות שלך." in reply
        assert "בחר 1-1 להוספה" in reply
        # Numbered list should NOT be in reply
        assert "1. משימה 1" not in reply


class TestChatEndpoint:
    """Tests for POST /chat endpoint."""

    def test_chat_requires_auth(self, client):
        """Chat endpoint requires authentication."""
        response = client.post("/chat", json={"message": "hello"})
        assert response.status_code == 401

    def test_chat_requires_message_or_selection(self, client, auth_headers):
        """Chat endpoint requires either message or selection."""
        response = client.post("/chat", json={}, headers=auth_headers)
        assert response.status_code == 400

    @patch("app.chat.service.call_chatbot_service")
    async def test_chat_returns_suggestions(self, mock_call, client, auth_headers):
        """Chat should return suggestions from chatbot-service."""
        mock_call.return_value = {
            "summary": "Test summary",
            "suggestions": [
                {"title": "Task 1", "priority": "high"},
                {"title": "Task 2", "priority": "medium"},
            ]
        }
        
        response = client.post(
            "/chat",
            json={"message": "I need to prepare"},
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "reply" in data
        assert "suggestions" in data

    @patch("app.chat.service.call_chatbot_service")
    def test_chat_handles_service_failure(self, mock_call, client, auth_headers):
        """Chat should handle chatbot-service failure gracefully."""
        mock_call.return_value = None  # Service failed
        
        response = client.post(
            "/chat",
            json={"message": "hello"},
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "reply" in data
        assert "Failed" in data["reply"] or "לא הצלחתי" in data["reply"]
