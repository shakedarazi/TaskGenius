"""
TASKGENIUS Core API - Telegram Tests

Phase 5: CI-safe tests for Telegram webhook and messaging.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.telegram.schemas import TelegramUpdate, TelegramMessage, TelegramUser
from app.telegram.service import TelegramService
from app.telegram.adapter import TelegramAdapter


class TestTelegramAdapter:
    """Tests for Telegram adapter."""

    @pytest.fixture
    def adapter(self):
        """Create adapter instance without token (for CI)."""
        return TelegramAdapter(bot_token=None)

    @pytest.fixture
    def adapter_with_token(self):
        """Create adapter instance with token."""
        return TelegramAdapter(bot_token="test-token")

    @patch("app.telegram.adapter.httpx.AsyncClient")
    async def test_send_message_success(self, mock_client_class, adapter_with_token):
        """Adapter should send message successfully."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"ok": True, "result": {"message_id": 123}}
        mock_response.raise_for_status = MagicMock()
        
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client_class.return_value = mock_client
        
        response = await adapter_with_token.send_message(
            chat_id=123456,
            text="Test message",
        )
        
        assert response.ok is True
        assert mock_client.post.called

    async def test_send_message_no_token(self, adapter):
        """Adapter should handle missing token gracefully."""
        response = await adapter.send_message(
            chat_id=123456,
            text="Test message",
        )
        
        assert response.ok is False

    @patch("app.telegram.adapter.httpx.AsyncClient")
    async def test_send_message_api_error(self, mock_client_class, adapter_with_token):
        """Adapter should handle API errors gracefully."""
        import httpx
        
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.post = AsyncMock(side_effect=httpx.HTTPError("API error"))
        mock_client_class.return_value = mock_client
        
        response = await adapter_with_token.send_message(
            chat_id=123456,
            text="Test message",
        )
        
        assert response.ok is False


class TestTelegramService:
    """Tests for Telegram service."""

    @pytest.fixture
    def mock_db(self):
        """Mock database."""
        return MagicMock()

    @pytest.fixture
    def service(self, mock_db):
        """Create service instance."""
        return TelegramService(mock_db)

    @pytest.fixture
    def telegram_update(self):
        """Create a sample Telegram update."""
        return TelegramUpdate(
            update_id=1,
            message=TelegramMessage(
                message_id=1,
                **{"from": TelegramUser(
                    id=123456,
                    first_name="Test",
                    is_bot=False,
                )},
                chat={"id": 123456, "type": "private"},
                date=1234567890,
                text="list my tasks",
            ),
        )

    @pytest.fixture
    def task_repository(self):
        """Mock task repository."""
        repo = MagicMock()
        repo.list_by_owner = AsyncMock(return_value=[])
        return repo

    @patch("app.telegram.service.process_message")
    @patch("app.telegram.service.TelegramAdapter.send_message")
    async def test_process_webhook_update_success(
        self,
        mock_send,
        mock_chat_process,
        service,
        telegram_update,
        task_repository,
    ):
        """Service should process webhook update and send response."""
        from app.chat.schemas import ChatResponse
        
        # Set up user mapping
        service.set_user_mapping(123456, "test-user-id")
        
        # Mock chat response
        mock_chat_process.return_value = ChatResponse(
            reply="You have 0 tasks",
        )
        
        # Mock Telegram send
        mock_send.return_value = MagicMock(ok=True)
        
        await service.process_webhook_update(telegram_update, task_repository)
        
        # Verify chat service was called
        assert mock_chat_process.called
        
        # Verify Telegram send was called
        assert mock_send.called
        send_call_args = mock_send.call_args
        chat_id = send_call_args[0][0] if send_call_args[0] else send_call_args[1].get("chat_id")
        text = send_call_args[0][1] if len(send_call_args[0]) > 1 else send_call_args[1].get("text")
        assert chat_id == 123456
        assert text == "You have 0 tasks"

    @patch("app.telegram.service.TelegramAdapter.send_message")
    async def test_process_webhook_update_no_user_mapping(
        self,
        mock_send,
        service,
        telegram_update,
        task_repository,
    ):
        """Service should send helpful message if user mapping doesn't exist."""
        mock_send.return_value = MagicMock(ok=True)
        
        await service.process_webhook_update(telegram_update, task_repository)
        
        # Verify helpful message was sent
        assert mock_send.called
        send_call_args = mock_send.call_args
        text = send_call_args[0][1] if len(send_call_args[0]) > 1 else send_call_args[1].get("text")
        assert "register" in text.lower()

    @patch("app.telegram.service.TelegramAdapter.send_message")
    async def test_process_webhook_update_no_text(
        self,
        mock_send,
        service,
        task_repository,
    ):
        """Service should ignore updates without text."""
        update = TelegramUpdate(
            update_id=1,
            message=TelegramMessage(
                message_id=1,
                **{"from": TelegramUser(
                    id=123456,
                    first_name="Test",
                    is_bot=False,
                )},
                chat={"id": 123456, "type": "private"},
                date=1234567890,
                text=None,  # No text
            ),
        )
        
        await service.process_webhook_update(update, task_repository)
        
        # Should not send anything
        assert not mock_send.called


class TestTelegramWebhookEndpoint:
    """Tests for Telegram webhook endpoint."""

    def test_webhook_endpoint_accepts_update(self, client):
        """Webhook endpoint should accept Telegram update."""
        update = {
            "update_id": 1,
            "message": {
                "message_id": 1,
                "from": {
                    "id": 123456,
                    "is_bot": False,
                    "first_name": "Test",
                },
                "chat": {"id": 123456, "type": "private"},
                "date": 1234567890,
                "text": "hello",
            },
        }
        
        response = client.post("/telegram/webhook", json=update)
        
        # Should accept the update (even if user mapping doesn't exist)
        assert response.status_code == 200
        data = response.json()
        assert "ok" in data

    def test_webhook_info_endpoint(self, client):
        """Webhook info endpoint should return info."""
        response = client.get("/telegram/webhook")
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] == "webhook_endpoint"
