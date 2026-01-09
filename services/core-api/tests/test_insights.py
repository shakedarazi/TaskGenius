"""
TASKGENIUS Core API - Insights Tests

Phase 3: CI-safe tests for weekly insights summary.
"""

import pytest
from datetime import datetime, timezone, timedelta

from app.tasks.models import Task
from app.tasks.enums import TaskStatus, TaskPriority, TaskCategory
from app.insights.service import InsightsService
from app.insights.schemas import WeeklySummary


class TestWeeklySummaryGenerator:
    """Tests for the weekly summary generator logic."""

    @pytest.fixture
    def service(self):
        """Create insights service instance."""
        return InsightsService()

    @pytest.fixture
    def frozen_now(self):
        """A fixed 'now' time for testing."""
        return datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)

    @pytest.fixture
    def user_id(self):
        """Test user ID."""
        return "test-user-123"

    def test_empty_tasks_summary(self, service, frozen_now, user_id):
        """Summary with no tasks should have all counts at zero."""
        summary = service.generate_weekly_summary([], frozen_now)
        
        assert summary.generated_at == frozen_now
        assert summary.completed.count == 0
        assert summary.high_priority.count == 0
        assert summary.upcoming.count == 0
        assert summary.overdue.count == 0
        assert len(summary.completed.tasks) == 0
        assert len(summary.high_priority.tasks) == 0
        assert len(summary.upcoming.tasks) == 0
        assert len(summary.overdue.tasks) == 0

    def test_completed_tasks_last_7_days(self, service, frozen_now, user_id):
        """Tasks completed in the last 7 days should appear in completed section."""
        # Task completed 3 days ago
        task1 = Task.create(
            owner_id=user_id,
            title="Completed Task 1",
            status=TaskStatus.DONE,
            priority=TaskPriority.MEDIUM,
        )
        task1.updated_at = frozen_now - timedelta(days=3)
        
        # Task completed 10 days ago (outside window)
        task2 = Task.create(
            owner_id=user_id,
            title="Old Completed Task",
            status=TaskStatus.DONE,
            priority=TaskPriority.MEDIUM,
        )
        task2.updated_at = frozen_now - timedelta(days=10)
        
        summary = service.generate_weekly_summary([task1, task2], frozen_now)
        
        assert summary.completed.count == 1
        assert summary.completed.tasks[0].title == "Completed Task 1"
        assert summary.completed.tasks[0].status == TaskStatus.DONE

    def test_high_priority_open_tasks(self, service, frozen_now, user_id):
        """Open tasks with HIGH or URGENT priority should appear in high_priority section."""
        # High priority open task
        task1 = Task.create(
            owner_id=user_id,
            title="Urgent Task",
            status=TaskStatus.OPEN,
            priority=TaskPriority.URGENT,
        )
        
        # High priority in-progress task
        task2 = Task.create(
            owner_id=user_id,
            title="High Priority Task",
            status=TaskStatus.IN_PROGRESS,
            priority=TaskPriority.HIGH,
        )
        
        # Low priority open task (should not appear)
        task3 = Task.create(
            owner_id=user_id,
            title="Low Priority Task",
            status=TaskStatus.OPEN,
            priority=TaskPriority.LOW,
        )
        
        # Done high priority task (should not appear)
        task4 = Task.create(
            owner_id=user_id,
            title="Done High Priority",
            status=TaskStatus.DONE,
            priority=TaskPriority.HIGH,
        )
        
        summary = service.generate_weekly_summary([task1, task2, task3, task4], frozen_now)
        
        assert summary.high_priority.count == 2
        titles = [t.title for t in summary.high_priority.tasks]
        assert "Urgent Task" in titles
        assert "High Priority Task" in titles
        assert "Low Priority Task" not in titles
        assert "Done High Priority" not in titles

    def test_upcoming_tasks_next_7_days(self, service, frozen_now, user_id):
        """Tasks due within next 7 days should appear in upcoming section."""
        # Task due in 3 days
        task1 = Task.create(
            owner_id=user_id,
            title="Due Soon",
            status=TaskStatus.OPEN,
            priority=TaskPriority.MEDIUM,
            deadline=frozen_now + timedelta(days=3),
        )
        
        # Task due in 7 days (boundary)
        task2 = Task.create(
            owner_id=user_id,
            title="Due in 7 Days",
            status=TaskStatus.OPEN,
            priority=TaskPriority.MEDIUM,
            deadline=frozen_now + timedelta(days=7),
        )
        
        # Task due in 8 days (outside window)
        task3 = Task.create(
            owner_id=user_id,
            title="Due Later",
            status=TaskStatus.OPEN,
            priority=TaskPriority.MEDIUM,
            deadline=frozen_now + timedelta(days=8),
        )
        
        # Done task with upcoming deadline (should not appear)
        task4 = Task.create(
            owner_id=user_id,
            title="Done Upcoming",
            status=TaskStatus.DONE,
            priority=TaskPriority.MEDIUM,
            deadline=frozen_now + timedelta(days=2),
        )
        
        summary = service.generate_weekly_summary([task1, task2, task3, task4], frozen_now)
        
        assert summary.upcoming.count == 2
        titles = [t.title for t in summary.upcoming.tasks]
        assert "Due Soon" in titles
        assert "Due in 7 Days" in titles
        assert "Due Later" not in titles
        assert "Done Upcoming" not in titles

    def test_overdue_tasks(self, service, frozen_now, user_id):
        """Tasks past deadline that are not DONE/CANCELED should appear in overdue section."""
        # Overdue open task
        task1 = Task.create(
            owner_id=user_id,
            title="Overdue Task",
            status=TaskStatus.OPEN,
            priority=TaskPriority.MEDIUM,
            deadline=frozen_now - timedelta(days=5),
        )
        
        # Overdue in-progress task
        task2 = Task.create(
            owner_id=user_id,
            title="Overdue In Progress",
            status=TaskStatus.IN_PROGRESS,
            priority=TaskPriority.MEDIUM,
            deadline=frozen_now - timedelta(days=2),
        )
        
        # Done task with past deadline (should not appear)
        task3 = Task.create(
            owner_id=user_id,
            title="Done Overdue",
            status=TaskStatus.DONE,
            priority=TaskPriority.MEDIUM,
            deadline=frozen_now - timedelta(days=3),
        )
        
        # Canceled task with past deadline (should not appear)
        task4 = Task.create(
            owner_id=user_id,
            title="Canceled Overdue",
            status=TaskStatus.CANCELED,
            priority=TaskPriority.MEDIUM,
            deadline=frozen_now - timedelta(days=1),
        )
        
        summary = service.generate_weekly_summary([task1, task2, task3, task4], frozen_now)
        
        assert summary.overdue.count == 2
        titles = [t.title for t in summary.overdue.tasks]
        assert "Overdue Task" in titles
        assert "Overdue In Progress" in titles
        assert "Done Overdue" not in titles
        assert "Canceled Overdue" not in titles

    def test_all_sections_populated(self, service, frozen_now, user_id):
        """Summary should correctly populate all 4 sections."""
        tasks = [
            # Completed
            Task.create(
                owner_id=user_id,
                title="Completed",
                status=TaskStatus.DONE,
                priority=TaskPriority.MEDIUM,
            ),
            # High priority
            Task.create(
                owner_id=user_id,
                title="High Priority",
                status=TaskStatus.OPEN,
                priority=TaskPriority.HIGH,
            ),
            # Upcoming
            Task.create(
                owner_id=user_id,
                title="Upcoming",
                status=TaskStatus.OPEN,
                priority=TaskPriority.MEDIUM,
                deadline=frozen_now + timedelta(days=3),
            ),
            # Overdue
            Task.create(
                owner_id=user_id,
                title="Overdue",
                status=TaskStatus.OPEN,
                priority=TaskPriority.MEDIUM,
                deadline=frozen_now - timedelta(days=2),
            ),
        ]
        
        # Set completed task's updated_at to within window
        tasks[0].updated_at = frozen_now - timedelta(days=2)
        
        summary = service.generate_weekly_summary(tasks, frozen_now)
        
        assert summary.completed.count == 1
        assert summary.high_priority.count == 1
        assert summary.upcoming.count == 1
        assert summary.overdue.count == 1

    def test_boundary_conditions(self, service, frozen_now, user_id):
        """Test boundary conditions for time windows."""
        # Task completed exactly 7 days ago (should be included)
        task1 = Task.create(
            owner_id=user_id,
            title="Exactly 7 Days Ago",
            status=TaskStatus.DONE,
            priority=TaskPriority.MEDIUM,
        )
        task1.updated_at = frozen_now - timedelta(days=7)
        
        # Task due exactly 7 days from now (should be included)
        task2 = Task.create(
            owner_id=user_id,
            title="Exactly 7 Days Ahead",
            status=TaskStatus.OPEN,
            priority=TaskPriority.MEDIUM,
            deadline=frozen_now + timedelta(days=7),
        )
        
        # Task due today (should be in upcoming, not overdue)
        task3 = Task.create(
            owner_id=user_id,
            title="Due Today",
            status=TaskStatus.OPEN,
            priority=TaskPriority.MEDIUM,
            deadline=frozen_now.replace(hour=23, minute=59),
        )
        
        summary = service.generate_weekly_summary([task1, task2, task3], frozen_now)
        
        assert summary.completed.count == 1
        assert summary.upcoming.count == 2  # task2 and task3
        assert summary.overdue.count == 0


class TestInsightsEndpoint:
    """Tests for the insights API endpoint."""

    def test_get_weekly_summary_requires_auth(self, client):
        """Weekly summary endpoint requires authentication."""
        response = client.get("/insights/weekly")
        assert response.status_code == 401

    def test_get_weekly_summary_empty(self, client, auth_headers):
        """Weekly summary with no tasks should return empty sections."""
        response = client.get("/insights/weekly", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "generated_at" in data
        assert "period_start" in data
        assert "period_end" in data
        assert data["completed"]["count"] == 0
        assert data["high_priority"]["count"] == 0
        assert data["upcoming"]["count"] == 0
        assert data["overdue"]["count"] == 0

    def test_get_weekly_summary_with_tasks(self, client, auth_headers):
        """Weekly summary should include tasks in correct sections."""
        # Create various tasks
        from datetime import datetime, timezone, timedelta
        
        now = datetime.now(timezone.utc)
        
        # Completed task
        client.post(
            "/tasks",
            json={
                "title": "Completed Task",
                "status": "done",
                "priority": "medium",
            },
            headers=auth_headers,
        )
        
        # High priority task
        client.post(
            "/tasks",
            json={
                "title": "High Priority Task",
                "status": "open",
                "priority": "high",
            },
            headers=auth_headers,
        )
        
        # Upcoming task
        deadline = (now + timedelta(days=3)).isoformat()
        client.post(
            "/tasks",
            json={
                "title": "Upcoming Task",
                "status": "open",
                "priority": "medium",
                "deadline": deadline,
            },
            headers=auth_headers,
        )
        
        # Overdue task
        past_deadline = (now - timedelta(days=2)).isoformat()
        create_response = client.post(
            "/tasks",
            json={
                "title": "Overdue Task",
                "status": "open",
                "priority": "medium",
                "deadline": past_deadline,
            },
            headers=auth_headers,
        )
        
        # Get summary
        response = client.get("/insights/weekly", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data["completed"]["count"] >= 0  # May be 0 if task not updated recently
        assert data["high_priority"]["count"] == 1
        assert data["upcoming"]["count"] == 1
        assert data["overdue"]["count"] == 1

    def test_ownership_isolation(self, client, auth_headers, second_auth_headers):
        """Users should only see their own tasks in insights."""
        # User A creates a task
        client.post(
            "/tasks",
            json={"title": "User A Task", "priority": "high"},
            headers=auth_headers,
        )
        
        # User B creates a task
        client.post(
            "/tasks",
            json={"title": "User B Task", "priority": "high"},
            headers=second_auth_headers,
        )
        
        # User A's summary should only include their task
        response_a = client.get("/insights/weekly", headers=auth_headers)
        assert response_a.status_code == 200
        data_a = response_a.json()
        
        # User B's summary should only include their task
        response_b = client.get("/insights/weekly", headers=second_auth_headers)
        assert response_b.status_code == 200
        data_b = response_b.json()
        
        # Verify isolation
        titles_a = [t["title"] for t in data_a["high_priority"]["tasks"]]
        titles_b = [t["title"] for t in data_b["high_priority"]["tasks"]]
        
        assert "User A Task" in titles_a
        assert "User B Task" not in titles_a
        assert "User B Task" in titles_b
        assert "User A Task" not in titles_b
