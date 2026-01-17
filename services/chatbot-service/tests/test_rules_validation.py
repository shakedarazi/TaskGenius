"""
TASKGENIUS Chatbot Service - Rules Validation Tests

Tests for Rules 1-9 + Global Flow Rule compliance.
"""

import pytest
from datetime import datetime
from app.schemas import ChatRequest, ChatResponse
from app.service import ChatbotService


class TestDateValidationRules:
    """Tests for Rules 1-3: Date resolution & validation."""
    
    @pytest.fixture
    def service(self):
        return ChatbotService()
    
    def test_validate_deadline_format_none(self, service):
        """Rule 1, 3: None deadline is valid."""
        is_valid, normalized = service._validate_deadline_format(None)
        assert is_valid is True
        assert normalized is None
    
    def test_validate_deadline_format_explicit_none(self, service):
        """Rule 1, 3: Explicit 'none' keywords are valid."""
        for none_keyword in ["none", "no", "אין", "לא", "null", "skip"]:
            is_valid, normalized = service._validate_deadline_format(none_keyword)
            assert is_valid is True, f"'{none_keyword}' should be valid"
            assert normalized is None
    
    def test_validate_deadline_format_iso_date(self, service):
        """Rule 1, 3: Valid ISO date format."""
        test_dates = [
            "2024-01-20",
            "2024-01-20T10:30:00",
            "2024-01-20T10:30:00Z",
            "2024-01-20T10:30:00+00:00",
        ]
        for date_str in test_dates:
            is_valid, normalized = service._validate_deadline_format(date_str)
            assert is_valid is True, f"'{date_str}' should be valid"
            assert normalized is not None
    
    def test_validate_deadline_format_invalid(self, service):
        """Rule 3: Invalid date format should be rejected."""
        invalid_dates = ["invalid", "not a date", "12345"]
        for date_str in invalid_dates:
            is_valid, normalized = service._validate_deadline_format(date_str)
            assert is_valid is False, f"'{date_str}' should be invalid"
    
    def test_is_deadline_ambiguous_relative_dates(self, service):
        """Rule 3: Relative dates without context are ambiguous."""
        ambiguous_dates = [
            "tomorrow",
            "יום רביעי",
            "next week",
            "next month",
        ]
        for date_str in ambiguous_dates:
            is_ambiguous = service._is_deadline_ambiguous(date_str, conversation_history=None)
            assert is_ambiguous is True, f"'{date_str}' should be ambiguous without context"
    
    def test_is_deadline_ambiguous_explicit_none(self, service):
        """Rule 3: Explicit 'none' is not ambiguous."""
        for none_keyword in ["none", "no", "אין", "לא"]:
            is_ambiguous = service._is_deadline_ambiguous(none_keyword)
            assert is_ambiguous is False, f"'{none_keyword}' should not be ambiguous"
    
    def test_was_deadline_asked_last(self, service):
        """Rule 2: Check if deadline was asked in last assistant message."""
        # Case 1: Deadline was asked last
        history_with_deadline = [
            {"role": "user", "content": "create a task"},
            {"role": "assistant", "content": "What's the deadline? (If not, say 'no')"},
        ]
        assert service._was_deadline_asked_last(history_with_deadline) is True
        
        # Case 2: Deadline was not asked last
        history_without_deadline = [
            {"role": "user", "content": "create a task"},
            {"role": "assistant", "content": "What's the priority?"},
        ]
        assert service._was_deadline_asked_last(history_without_deadline) is False
        
        # Case 3: Empty history
        assert service._was_deadline_asked_last(None) is False
        assert service._was_deadline_asked_last([]) is False


class TestConfirmationRules:
    """Tests for Rules 8-9: Confirmation flows."""
    
    @pytest.fixture
    def service(self):
        return ChatbotService()
    
    async def test_update_asks_for_field_selection(self, service):
        """Rule 8: Update should ask which field to update."""
        request = ChatRequest(
            message="update task",
            user_id="test-user",
            tasks=[
                {"id": "1", "title": "Test Task", "status": "open", "priority": "high"},
            ],
        )
        response = await service.generate_response(request)
        
        # Should ask which field
        assert "field" in response.reply.lower() or "שדה" in response.reply or "title" in response.reply.lower() or "priority" in response.reply.lower()
        assert response.intent == "potential_update"
    
    async def test_delete_presents_task_description(self, service):
        """Rule 9: Delete should present task description."""
        request = ChatRequest(
            message="delete Test Task",
            user_id="test-user",
            tasks=[
                {"id": "1", "title": "Test Task", "status": "open", "priority": "high", "deadline": "2024-01-20"},
            ],
        )
        response = await service.generate_response(request)
        
        # Should present task description
        assert "Test Task" in response.reply
        assert "priority" in response.reply.lower() or "עדיפות" in response.reply
        assert response.intent == "potential_delete"
    
    async def test_delete_asks_for_confirmation(self, service):
        """Rule 9: Delete should ask for explicit confirmation."""
        request = ChatRequest(
            message="delete Test Task",
            user_id="test-user",
            tasks=[
                {"id": "1", "title": "Test Task", "status": "open", "priority": "high"},
            ],
        )
        response = await service.generate_response(request)
        
        # Should ask for confirmation
        assert "sure" in response.reply.lower() or "בטוח" in response.reply or "confirm" in response.reply.lower() or "אישור" in response.reply


class TestHistoryResetRules:
    """Tests for Rules 4-5: History reset after CRUD."""
    
    @pytest.fixture
    def service(self):
        return ChatbotService()
    
    async def test_empty_history_emphasizes_tasks_data(self, service):
        """Rule 5: Empty history should emphasize reliance on tasks data only."""
        request = ChatRequest(
            message="list tasks",
            user_id="test-user",
            tasks=[
                {"id": "1", "title": "Task 1", "status": "open", "priority": "high"},
            ],
            conversation_history=[],  # Empty history
        )
        response = await service.generate_response(request)
        
        # Should work with empty history
        assert response.reply
        assert response.intent == "list_tasks"


class TestGlobalFlowRule:
    """Tests for Global Flow Rule: clarification → date → confirmation → execution."""
    
    @pytest.fixture
    def service(self):
        return ChatbotService()
    
    async def test_add_task_flow_order(self, service):
        """Global Flow: add_task should follow correct order."""
        # Step 1: Ask for title
        request1 = ChatRequest(
            message="create a task",
            user_id="test-user",
            tasks=[],
        )
        response1 = await service.generate_response(request1)
        assert "title" in response1.reply.lower() or "כותרת" in response1.reply
        
        # Step 2: Ask for priority (after title provided)
        request2 = ChatRequest(
            message="My new task",
            user_id="test-user",
            tasks=[],
            conversation_history=[
                {"role": "user", "content": "create a task"},
                {"role": "assistant", "content": response1.reply},
            ],
        )
        response2 = await service.generate_response(request2)
        assert "priority" in response2.reply.lower() or "עדיפות" in response2.reply
        
        # Step 3: Ask for deadline (after priority provided) - Rule 2: LAST step
        request3 = ChatRequest(
            message="high",
            user_id="test-user",
            tasks=[],
            conversation_history=[
                {"role": "user", "content": "create a task"},
                {"role": "assistant", "content": response1.reply},
                {"role": "user", "content": "My new task"},
                {"role": "assistant", "content": response2.reply},
            ],
        )
        response3 = await service.generate_response(request3)
        assert "deadline" in response3.reply.lower() or "תאריך" in response3.reply or "יעד" in response3.reply
