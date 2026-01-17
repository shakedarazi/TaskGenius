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

import { useMemo, useState, useEffect, useRef, useCallback } from "react";
import { tasksApi, telegramApi } from "@/api";
import { TaskList } from "@/components/TaskList";
import { TaskForm } from "@/components/TaskForm";
import { ChatWidget } from "@/components/ChatWidget";
import type { Task, TaskFilters, TaskPriority, TaskStatus, TelegramStatus } from "@/types";

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
  
  // Telegram status for summary button
  const [telegramStatus, setTelegramStatus] = useState<TelegramStatus | null>(null);
  const [sendingSummary, setSendingSummary] = useState(false);
  const [summaryError, setSummaryError] = useState<string | null>(null);

  // AbortController ref to cancel in-flight requests
  const abortControllerRef = useRef<AbortController | null>(null);
  // Track current request ID to prevent stale updates
  const requestIdRef = useRef(0);

  function sevenDaysAgoISO(): string {
    const d = new Date();
    d.setDate(d.getDate() - 7);
    return d.toISOString();
  }

  // Fetch tasks when mode or backend filters change
  useEffect(() => {
    // Cancel any in-flight request
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    // Increment request ID for this fetch
    const currentRequestId = ++requestIdRef.current;

    // Create new AbortController for this request
    const abortController = new AbortController();
    abortControllerRef.current = abortController;

    setLoading(true);
    setError(null);

    const fetchTasks = async () => {
      try {
        const backendFilters: any = { ...(filters as any) };

        if (viewMode === "active") {
          // Active contract: /tasks only (no status, no completed_since)
          delete backendFilters.completed_since;
          delete backendFilters.include_closed;
          delete backendFilters.status;
        } else {
          // Completed contract: /tasks?status=done&completed_since=...
          delete backendFilters.include_closed;
          backendFilters.completed_since = sevenDaysAgoISO();
          backendFilters.status = "done" as TaskStatus;
        }

        const response = await tasksApi.listTasks(backendFilters, abortController.signal);
        
        // Only update state if this is still the latest request and wasn't aborted
        if (currentRequestId === requestIdRef.current && !abortController.signal.aborted) {
          setTasks(response.tasks);
          setLoading(false);
        }
      } catch (err: any) {
        // Ignore abort errors
        if (err?.name === 'AbortError' || abortController.signal.aborted) {
          return;
        }
        // Only update error if this is still the latest request
        if (currentRequestId === requestIdRef.current) {
          setError(err instanceof Error ? err.message : "Failed to load tasks");
          setLoading(false);
        }
      }
    };

    void fetchTasks();
    
    // Cleanup: abort request on unmount or when dependencies change
    return () => {
      if (abortControllerRef.current === abortController) {
        abortController.abort();
      }
    };
  }, [viewMode, filters]);

  // Load Telegram status on mount
  useEffect(() => {
    const loadTelegramStatus = async () => {
      try {
        const status = await telegramApi.getTelegramStatus();
        setTelegramStatus(status);
      } catch (err) {
        // Silently fail - user might not have Telegram linked
        setTelegramStatus(null);
      }
    };
    void loadTelegramStatus();
  }, []);

  // Refresh function for manual refresh (button click, mutations)
  const refreshTasks = useCallback(async () => {
    // Cancel any in-flight request
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    // Increment request ID for this fetch
    const currentRequestId = ++requestIdRef.current;

    // Create new AbortController for this request
    const abortController = new AbortController();
    abortControllerRef.current = abortController;

    setLoading(true);
    setError(null);

    try {
      const backendFilters: any = { ...(filters as any) };

      if (viewMode === "active") {
        // Active contract: /tasks only (no status, no completed_since)
        delete backendFilters.completed_since;
        delete backendFilters.include_closed;
        delete backendFilters.status;
      } else {
        // Completed contract: /tasks?status=done&completed_since=...
        delete backendFilters.include_closed;
        backendFilters.completed_since = sevenDaysAgoISO();
        backendFilters.status = "done" as TaskStatus;
      }

      const response = await tasksApi.listTasks(backendFilters, abortController.signal);
      
      // Only update state if this is still the latest request and wasn't aborted
      if (currentRequestId === requestIdRef.current && !abortController.signal.aborted) {
        setTasks(response.tasks);
        setLoading(false);
      }
    } catch (err: any) {
      // Ignore abort errors
      if (err?.name === 'AbortError' || abortController.signal.aborted) {
        return;
      }
      // Only update error if this is still the latest request
      if (currentRequestId === requestIdRef.current) {
        setError(err instanceof Error ? err.message : "Failed to load tasks");
        setLoading(false);
      }
    }
  }, [viewMode, filters]);

  // Listen for task mutations from ChatWidget (after refreshTasks is defined)
  useEffect(() => {
    const handleTaskMutated = async () => {
      await refreshTasks();
    };
    
    window.addEventListener('taskMutated', handleTaskMutated);
    return () => {
      window.removeEventListener('taskMutated', handleTaskMutated);
    };
  }, [refreshTasks]);

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

  const handleTaskCreated = async (task: Task) => {
    setShowForm(false);
    // Always refresh from server after mutation to ensure consistency
    await refreshTasks();
  };

  const handleTaskUpdated = async (updatedTask: Task) => {
    // Always refresh from server after mutation to ensure consistency
    await refreshTasks();
  };

  const handleTaskDeleted = async (taskId: string) => {
    // Always refresh from server after mutation to ensure consistency
    await refreshTasks();
  };

  const handleSendSummary = async () => {
    if (!telegramStatus?.linked) {
      setSummaryError("Please link your Telegram account first");
      return;
    }

    setSendingSummary(true);
    setSummaryError(null);

    try {
      await telegramApi.sendWeeklySummary();
      setSummaryError(null);
      // Show success message with notification status info
      const message = telegramStatus.notifications_enabled
        ? "Weekly summary sent to Telegram! You'll also receive automatic summaries every 7 days."
        : "Weekly summary sent to Telegram! Note: Automatic summaries are disabled. Enable them in Settings to receive weekly summaries automatically.";
      alert(message);
    } catch (err: any) {
      setSummaryError(err instanceof Error ? err.message : "Failed to send summary");
    } finally {
      setSendingSummary(false);
    }
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

          <button onClick={() => refreshTasks()} disabled={loading}>
            Refresh
          </button>

          {telegramStatus?.linked && (
            <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
              <button 
                onClick={handleSendSummary} 
                disabled={sendingSummary || isCompletedView}
                title={
                  telegramStatus.notifications_enabled
                    ? "Send weekly summary to Telegram"
                    : "Send weekly summary to Telegram (notifications are disabled - you won't receive automatic weekly summaries)"
                }
              >
                {sendingSummary ? "Sending..." : "📊 Send Summary"}
              </button>
              {!telegramStatus.notifications_enabled && (
                <span 
                  style={{ 
                    fontSize: "0.85em", 
                    color: "#666",
                    fontStyle: "italic" 
                  }}
                  title="Automatic weekly summaries are disabled. Enable them in Settings to receive summaries every 7 days."
                >
                  (Auto: Off)
                </span>
              )}
            </div>
          )}
        </div>
      </header>

      {error && <div className="error">{error}</div>}
      {summaryError && <div className="error">{summaryError}</div>}

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
