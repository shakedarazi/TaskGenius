/**
 * TasksPage
 *
 * Default behavior:
 * - By default, backend returns ACTIVE tasks only (excludes DONE/CANCELED).
 *
 * Additions:
 * - View toggle: Active vs Completed (last 7 days) fetched from backend
 * - Client-side filtering by priority + urgency + search on the fetched set
 * - Refresh button
 */

import { useMemo, useState, useEffect, useCallback } from "react";
import { tasksApi } from "@/api";
import { TaskList } from "@/components/TaskList";
import { TaskForm } from "@/components/TaskForm";
import { ChatWidget } from "@/components/ChatWidget";
import type { Task, TaskFilters, TaskPriority, TaskStatus } from "@/types";

type UrgencyFilter =
  | "any"
  | "no_deadline"
  | "overdue"
  | "due_today"
  | "due_soon"
  | "not_soon";

type ViewMode = "active" | "completed_7d";

export function TasksPage() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Backend fetch mode
  const [viewMode, setViewMode] = useState<ViewMode>("active");

  // Backend filters (kept as-is)
  const [filters, setFilters] = useState<TaskFilters>({});

  // UI-only filters (client-side)
  const [priorityFilter, setPriorityFilter] = useState<"any" | TaskPriority>("any");
  const [urgencyFilter, setUrgencyFilter] = useState<UrgencyFilter>("any");
  const [search, setSearch] = useState("");

  const [showForm, setShowForm] = useState(false);

  function sevenDaysAgoISO(): string {
    const d = new Date();
    d.setDate(d.getDate() - 7);
    return d.toISOString();
  }

  // NOTE: mode is a parameter to avoid stale closures and cross-mode double fetch
  const loadTasks = useCallback(
    async (mode: ViewMode) => {
      setLoading(true);
      setError(null);

      try {
        const backendFilters: any = { ...(filters as any) };

        if (mode === "active") {
          // Active contract: /tasks only
          delete backendFilters.completed_since;
          delete backendFilters.include_closed;
          delete backendFilters.status;
        } else {
          // Completed contract: /tasks?status=done&completed_since=...
          delete backendFilters.include_closed;
          backendFilters.completed_since = sevenDaysAgoISO();
          backendFilters.status = "done" as TaskStatus;
        }

        const response = await tasksApi.listTasks(backendFilters);
        setTasks(response.tasks);

        console.log(
          "[loadTasks] mode:",
          mode,
          "filters:",
          backendFilters,
          "response:",
          response
        );
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load tasks");
      } finally {
        setLoading(false);
      }
    },
    [filters]
  );

  // Fetch tasks when mode or backend filters change
  useEffect(() => {
    void loadTasks(viewMode);
  }, [loadTasks, viewMode]);

  // Apply UI filters client-side (priority + urgency + search)
  const visibleTasks = useMemo(() => {
    const q = search.trim().toLowerCase();

    return tasks
      .filter((t) => (priorityFilter === "any" ? true : t.priority === priorityFilter))
      .filter((t) => (urgencyFilter === "any" ? true : (t.urgency as any) === urgencyFilter))
      .filter((t) => {
        if (!q) return true;
        const hay = `${t.title ?? ""} ${t.description ?? ""}`.toLowerCase();
        return hay.includes(q);
      });
  }, [tasks, priorityFilter, urgencyFilter, search]);

  const handleTaskCreated = (task: Task) => {
    if (viewMode !== "active") {
      setShowForm(false);
      return;
    }

    if (task.status === "done" || task.status === "canceled") {
      setShowForm(false);
      void loadTasks("active");
      return;
    }

    setTasks((prev) => [task, ...prev]);
    setShowForm(false);
  };

  const handleTaskUpdated = (updatedTask: Task) => {
    setTasks((prev) => {
      if (viewMode === "active") {
        if (updatedTask.status === "done" || updatedTask.status === "canceled") {
          return prev.filter((t) => t.id !== updatedTask.id);
        }
      }

      if (viewMode === "completed_7d") {
        if (updatedTask.status !== "done") {
          return prev.filter((t) => t.id !== updatedTask.id);
        }
      }

      return prev.map((t) => (t.id === updatedTask.id ? updatedTask : t));
    });
  };

  const handleTaskDeleted = (taskId: string) => {
    setTasks((prev) => prev.filter((t) => t.id !== taskId));
  };

  const isCompletedView = viewMode === "completed_7d";

  return (
    <div className="tasks-page">
      <header className="tasks-header">
        <h1>{isCompletedView ? "Completed (last 7 days)" : "My Tasks"}</h1>

        <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
          <select
            value={viewMode}
            onChange={(e) => setViewMode(e.target.value as ViewMode)}
            title="Choose which tasks to fetch from the server"
          >
            <option value="active">View: Active</option>
            <option value="completed_7d">View: Completed (7 days)</option>
          </select>

          <input
            type="text"
            placeholder="Search..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />

          <select
            value={priorityFilter}
            onChange={(e) => setPriorityFilter(e.target.value as any)}
            title="Filter by priority"
          >
            <option value="any">Priority: Any</option>
            <option value="low">Priority: Low</option>
            <option value="medium">Priority: Medium</option>
            <option value="high">Priority: High</option>
            <option value="urgent">Priority: Urgent</option>
          </select>

          <select
            value={urgencyFilter}
            onChange={(e) => setUrgencyFilter(e.target.value as any)}
            title="Filter by urgency"
          >
            <option value="any">Urgency: Any</option>
            <option value="overdue">Urgency: Overdue</option>
            <option value="due_today">Urgency: Due today</option>
            <option value="due_soon">Urgency: Due soon</option>
            <option value="not_soon">Urgency: Not soon</option>
            <option value="no_deadline">Urgency: No deadline</option>
          </select>

          <button onClick={() => setShowForm(true)} disabled={isCompletedView}>
            + New Task
          </button>

          <button onClick={() => loadTasks(viewMode)} disabled={loading}>
            Refresh
          </button>
        </div>
      </header>

      {error && <div className="error">{error}</div>}

      {showForm && !isCompletedView && (
        <TaskForm onSubmit={handleTaskCreated} onCancel={() => setShowForm(false)} />
      )}

      <TaskList
        tasks={visibleTasks}
        loading={loading}
        onUpdate={handleTaskUpdated}
        onDelete={handleTaskDeleted}
      />

      {!isCompletedView && <ChatWidget onTaskCreated={handleTaskCreated} />}
    </div>
  );
}
