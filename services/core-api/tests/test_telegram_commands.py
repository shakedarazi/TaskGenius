"""Tests for Telegram command handlers and priority rendering."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timezone

from app.telegram.service import TelegramService
from app.tasks.models import Task
from app.tasks.enums import TaskStatus, TaskPriority


@pytest.fixture
def telegram_service():
    db = MagicMock()
    service = TelegramService(db=db)
    service.telegram_adapter = AsyncMock()
    return service


class TestCommandRouting:
    """Test that commands are routed correctly."""

    @pytest.mark.asyncio
    async def test_urgent_command(self, telegram_service):
        """Test /urgent command calls _cmd_urgent and sends message."""
        task_repo = AsyncMock()
        task_repo.list_by_owner = AsyncMock(return_value=[])

        await telegram_service._handle_command("/urgent", "user1", 123, task_repo)

        telegram_service.telegram_adapter.send_message.assert_called_once()
        call_args = telegram_service.telegram_adapter.send_message.call_args
        assert "Urgent tasks" in call_args.kwargs["text"]

    @pytest.mark.asyncio
    async def test_soon_command(self, telegram_service):
        """Test /soon command calls _cmd_soon and sends message."""
        task_repo = AsyncMock()
        task_repo.list_by_owner = AsyncMock(return_value=[])

        await telegram_service._handle_command("/soon", "user1", 123, task_repo)

        telegram_service.telegram_adapter.send_message.assert_called_once()
        call_args = telegram_service.telegram_adapter.send_message.call_args
        assert "Due soon" in call_args.kwargs["text"]


class TestPriorityColors:
    """Test priority emoji mapping in _format_task_list."""

    def _make_task(self, priority: TaskPriority) -> Task:
        return Task(
            id="1",
            owner_id="u1",
            title="Test Task",
            status=TaskStatus.OPEN,
            priority=priority,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

    def test_urgent_red(self, telegram_service):
        """URGENT priority should show 🔴 red."""
        task = self._make_task(TaskPriority.URGENT)
        result = telegram_service._format_task_list([task], "Test")
        assert "🔴" in result

    def test_high_purple(self, telegram_service):
        """HIGH priority should show 🟣 purple."""
        task = self._make_task(TaskPriority.HIGH)
        result = telegram_service._format_task_list([task], "Test")
        assert "🟣" in result

    def test_medium_orange(self, telegram_service):
        """MEDIUM priority should show 🟠 orange."""
        task = self._make_task(TaskPriority.MEDIUM)
        result = telegram_service._format_task_list([task], "Test")
        assert "🟠" in result

    def test_low_no_icon(self, telegram_service):
        """LOW priority should show no priority icon."""
        task = self._make_task(TaskPriority.LOW)
        result = telegram_service._format_task_list([task], "Test")
        assert "🔴" not in result
        assert "🟣" not in result
        assert "🟠" not in result


class TestCmdUrgent:
    """Test _cmd_urgent method."""

    @pytest.mark.asyncio
    async def test_filters_urgent_and_high(self, telegram_service):
        """_cmd_urgent should include both URGENT and HIGH priority tasks."""
        urgent_task = Task(
            id="1", owner_id="u1", title="Urgent Task",
            status=TaskStatus.OPEN, priority=TaskPriority.URGENT,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        high_task = Task(
            id="2", owner_id="u1", title="High Task",
            status=TaskStatus.OPEN, priority=TaskPriority.HIGH,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        medium_task = Task(
            id="3", owner_id="u1", title="Medium Task",
            status=TaskStatus.OPEN, priority=TaskPriority.MEDIUM,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        task_repo = AsyncMock()
        task_repo.list_by_owner = AsyncMock(
            return_value=[urgent_task, high_task, medium_task]
        )

        result = await telegram_service._cmd_urgent("u1", task_repo)

        assert "Urgent Task" in result
        assert "High Task" in result
        assert "Medium Task" not in result

    @pytest.mark.asyncio
    async def test_empty_list(self, telegram_service):
        """_cmd_urgent with no tasks shows 'No tasks found'."""
        task_repo = AsyncMock()
        task_repo.list_by_owner = AsyncMock(return_value=[])

        result = await telegram_service._cmd_urgent("u1", task_repo)

        assert "No tasks found" in result
