"""
TASKGENIUS Core API - Task CRUD Tests

Phase 2: CI-safe tests for task management without MongoDB.
"""

import pytest
from datetime import datetime, timezone, timedelta


class TestCreateTask:
    """Tests for POST /tasks."""

    def test_create_task_minimal(self, client, auth_headers):
        """Create task with only required fields."""
        response = client.post(
            "/tasks",
            json={"title": "Test Task"},
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Test Task"
        assert data["status"] == "open"
        assert data["priority"] == "medium"
        assert "id" in data
        assert "owner_id" in data
        assert "created_at" in data
        assert "updated_at" in data
        assert "urgency" in data

    def test_create_task_all_fields(self, client, auth_headers):
        """Create task with all fields."""
        deadline = (datetime.now(timezone.utc) + timedelta(days=3)).isoformat()
        response = client.post(
            "/tasks",
            json={
                "title": "Full Task",
                "status": "in_progress",
                "priority": "high",
                "description": "A detailed description",
                "category": "work",
                "deadline": deadline,
                "estimate_bucket": "30_60",
            },
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Full Task"
        assert data["status"] == "in_progress"
        assert data["priority"] == "high"
        assert data["description"] == "A detailed description"
        assert data["category"] == "work"
        assert data["estimate_bucket"] == "30_60"

    def test_create_task_requires_auth(self, client):
        """Create task without token should fail."""
        response = client.post("/tasks", json={"title": "Unauthorized"})
        assert response.status_code == 401

    def test_create_task_invalid_status(self, client, auth_headers):
        """Create task with invalid status should fail."""
        response = client.post(
            "/tasks",
            json={"title": "Bad Status", "status": "invalid"},
            headers=auth_headers,
        )
        assert response.status_code == 422

    def test_create_task_invalid_priority(self, client, auth_headers):
        """Create task with invalid priority should fail."""
        response = client.post(
            "/tasks",
            json={"title": "Bad Priority", "priority": "invalid"},
            headers=auth_headers,
        )
        assert response.status_code == 422

    def test_create_task_empty_title(self, client, auth_headers):
        """Create task with empty title should fail."""
        response = client.post(
            "/tasks",
            json={"title": ""},
            headers=auth_headers,
        )
        assert response.status_code == 422


class TestGetTask:
    """Tests for GET /tasks/{task_id}."""

    def test_get_task_success(self, client, auth_headers):
        """Get an existing task."""
        create_response = client.post(
            "/tasks",
            json={"title": "Retrievable Task"},
            headers=auth_headers,
        )
        task_id = create_response.json()["id"]

        get_response = client.get(f"/tasks/{task_id}", headers=auth_headers)
        assert get_response.status_code == 200
        assert get_response.json()["id"] == task_id
        assert get_response.json()["title"] == "Retrievable Task"

    def test_get_task_not_found(self, client, auth_headers):
        """Get non-existent task should return 404."""
        response = client.get("/tasks/nonexistent-id", headers=auth_headers)
        assert response.status_code == 404

    def test_get_task_requires_auth(self, client, auth_headers):
        """Get task without token should fail."""
        create_response = client.post(
            "/tasks",
            json={"title": "Auth Test Task"},
            headers=auth_headers,
        )
        task_id = create_response.json()["id"]

        response = client.get(f"/tasks/{task_id}")
        assert response.status_code == 401


class TestListTasks:
    """Tests for GET /tasks."""

    def test_list_tasks_empty(self, client, auth_headers):
        """List tasks when none exist."""
        response = client.get("/tasks", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["tasks"] == []
        assert data["total"] == 0

    def test_list_tasks_multiple(self, client, auth_headers):
        """List multiple tasks."""
        for i in range(3):
            client.post(
                "/tasks",
                json={"title": f"Task {i}"},
                headers=auth_headers,
            )

        response = client.get("/tasks", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert len(data["tasks"]) == 3

    def test_list_tasks_filter_by_status(self, client, auth_headers):
        """Filter tasks by status."""
        client.post(
            "/tasks",
            json={"title": "Open Task", "status": "open"},
            headers=auth_headers,
        )
        client.post(
            "/tasks",
            json={"title": "Done Task", "status": "done"},
            headers=auth_headers,
        )

        # Filter for open tasks
        response = client.get("/tasks?status=open", headers=auth_headers)
        data = response.json()
        assert data["total"] == 1
        assert data["tasks"][0]["status"] == "open"

        # Filter for done tasks
        response = client.get("/tasks?status=done", headers=auth_headers)
        data = response.json()
        assert data["total"] == 1
        assert data["tasks"][0]["status"] == "done"

    def test_list_tasks_filter_by_deadline(self, client, auth_headers):
        """Filter tasks by deadline range."""
        from urllib.parse import quote
        
        now = datetime.now(timezone.utc)
        tomorrow = (now + timedelta(days=1)).isoformat()
        next_week = (now + timedelta(days=7)).isoformat()

        client.post(
            "/tasks",
            json={"title": "Soon Task", "deadline": tomorrow},
            headers=auth_headers,
        )
        client.post(
            "/tasks",
            json={"title": "Later Task", "deadline": next_week},
            headers=auth_headers,
        )

        # Filter for tasks before 3 days from now
        # URL encode the datetime to handle the '+' in timezone
        cutoff = (now + timedelta(days=3)).isoformat()
        response = client.get(
            "/tasks",
            params={"deadline_before": cutoff},
            headers=auth_headers,
        )
        assert response.status_code == 200, f"Response: {response.json()}"
        data = response.json()
        assert data["total"] == 1
        assert data["tasks"][0]["title"] == "Soon Task"

    def test_list_tasks_requires_auth(self, client):
        """List tasks without token should fail."""
        response = client.get("/tasks")
        assert response.status_code == 401


class TestUpdateTask:
    """Tests for PATCH /tasks/{task_id}."""

    def test_update_task_title(self, client, auth_headers):
        """Update task title."""
        create_response = client.post(
            "/tasks",
            json={"title": "Original Title"},
            headers=auth_headers,
        )
        task_id = create_response.json()["id"]

        update_response = client.patch(
            f"/tasks/{task_id}",
            json={"title": "Updated Title"},
            headers=auth_headers,
        )
        assert update_response.status_code == 200
        assert update_response.json()["title"] == "Updated Title"

    def test_update_task_status(self, client, auth_headers):
        """Update task status."""
        create_response = client.post(
            "/tasks",
            json={"title": "Status Task"},
            headers=auth_headers,
        )
        task_id = create_response.json()["id"]

        update_response = client.patch(
            f"/tasks/{task_id}",
            json={"status": "done"},
            headers=auth_headers,
        )
        assert update_response.status_code == 200
        assert update_response.json()["status"] == "done"

    def test_update_task_multiple_fields(self, client, auth_headers):
        """Update multiple fields at once."""
        create_response = client.post(
            "/tasks",
            json={"title": "Multi Update"},
            headers=auth_headers,
        )
        task_id = create_response.json()["id"]

        update_response = client.patch(
            f"/tasks/{task_id}",
            json={
                "title": "New Title",
                "status": "in_progress",
                "priority": "urgent",
                "description": "Added description",
            },
            headers=auth_headers,
        )
        assert update_response.status_code == 200
        data = update_response.json()
        assert data["title"] == "New Title"
        assert data["status"] == "in_progress"
        assert data["priority"] == "urgent"
        assert data["description"] == "Added description"

    def test_update_task_not_found(self, client, auth_headers):
        """Update non-existent task should return 404."""
        response = client.patch(
            "/tasks/nonexistent-id",
            json={"title": "Wont Work"},
            headers=auth_headers,
        )
        assert response.status_code == 404

    def test_update_task_requires_auth(self, client, auth_headers):
        """Update task without token should fail."""
        create_response = client.post(
            "/tasks",
            json={"title": "Auth Test"},
            headers=auth_headers,
        )
        task_id = create_response.json()["id"]

        response = client.patch(f"/tasks/{task_id}", json={"title": "Hacked"})
        assert response.status_code == 401


class TestDeleteTask:
    """Tests for DELETE /tasks/{task_id}."""

    def test_delete_task_success(self, client, auth_headers):
        """Delete an existing task."""
        create_response = client.post(
            "/tasks",
            json={"title": "To Be Deleted"},
            headers=auth_headers,
        )
        task_id = create_response.json()["id"]

        delete_response = client.delete(f"/tasks/{task_id}", headers=auth_headers)
        assert delete_response.status_code == 200
        assert delete_response.json()["id"] == task_id

        # Verify task is deleted
        get_response = client.get(f"/tasks/{task_id}", headers=auth_headers)
        assert get_response.status_code == 404

    def test_delete_task_not_found(self, client, auth_headers):
        """Delete non-existent task should return 404."""
        response = client.delete("/tasks/nonexistent-id", headers=auth_headers)
        assert response.status_code == 404

    def test_delete_task_requires_auth(self, client, auth_headers):
        """Delete task without token should fail."""
        create_response = client.post(
            "/tasks",
            json={"title": "Auth Delete Test"},
            headers=auth_headers,
        )
        task_id = create_response.json()["id"]

        response = client.delete(f"/tasks/{task_id}")
        assert response.status_code == 401


class TestOwnershipIsolation:
    """Tests to verify users cannot access other users' tasks."""

    def test_user_cannot_read_others_task(
        self, client, auth_headers, second_auth_headers
    ):
        """User A cannot read User B's task."""
        # User A creates a task
        create_response = client.post(
            "/tasks",
            json={"title": "User A Task"},
            headers=auth_headers,
        )
        task_id = create_response.json()["id"]

        # User B tries to read it
        get_response = client.get(f"/tasks/{task_id}", headers=second_auth_headers)
        assert get_response.status_code == 404

    def test_user_cannot_update_others_task(
        self, client, auth_headers, second_auth_headers
    ):
        """User A cannot update User B's task."""
        # User A creates a task
        create_response = client.post(
            "/tasks",
            json={"title": "User A Task"},
            headers=auth_headers,
        )
        task_id = create_response.json()["id"]

        # User B tries to update it
        update_response = client.patch(
            f"/tasks/{task_id}",
            json={"title": "Hacked by B"},
            headers=second_auth_headers,
        )
        assert update_response.status_code == 404

        # Verify task unchanged for User A
        get_response = client.get(f"/tasks/{task_id}", headers=auth_headers)
        assert get_response.json()["title"] == "User A Task"

    def test_user_cannot_delete_others_task(
        self, client, auth_headers, second_auth_headers
    ):
        """User A cannot delete User B's task."""
        # User A creates a task
        create_response = client.post(
            "/tasks",
            json={"title": "User A Task"},
            headers=auth_headers,
        )
        task_id = create_response.json()["id"]

        # User B tries to delete it
        delete_response = client.delete(f"/tasks/{task_id}", headers=second_auth_headers)
        assert delete_response.status_code == 404

        # Verify task still exists for User A
        get_response = client.get(f"/tasks/{task_id}", headers=auth_headers)
        assert get_response.status_code == 200

    def test_list_only_own_tasks(self, client, auth_headers, second_auth_headers):
        """Users only see their own tasks in list."""
        # User A creates 2 tasks
        client.post("/tasks", json={"title": "A Task 1"}, headers=auth_headers)
        client.post("/tasks", json={"title": "A Task 2"}, headers=auth_headers)

        # User B creates 1 task
        client.post("/tasks", json={"title": "B Task 1"}, headers=second_auth_headers)

        # User A sees only their tasks
        response_a = client.get("/tasks", headers=auth_headers)
        assert response_a.json()["total"] == 2
        titles = [t["title"] for t in response_a.json()["tasks"]]
        assert "A Task 1" in titles
        assert "A Task 2" in titles
        assert "B Task 1" not in titles

        # User B sees only their task
        response_b = client.get("/tasks", headers=second_auth_headers)
        assert response_b.json()["total"] == 1
        assert response_b.json()["tasks"][0]["title"] == "B Task 1"
