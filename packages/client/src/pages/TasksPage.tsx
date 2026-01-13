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

import { useMemo, useState, useEffect } from 'react';
import { tasksApi } from '@/api';
import { TaskList } from '@/components/TaskList';
import { TaskForm } from '@/components/TaskForm';
import { ChatWidget } from '@/components/ChatWidget';
import type { Task, TaskFilters, TaskPriority, TaskStatus } from '@/types';

type UrgencyFilter =
  | 'any'
  | 'no_deadline'
  | 'overdue'
  | 'due_today'
  | 'due_soon'
  | 'not_soon';

type ViewMode = 'active' | 'completed_7d';

export function TasksPage() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Backend fetch mode
  const [viewMode, setViewMode] = useState<ViewMode>('active');

  // Keep as-is (you already have it)
  const [filters, setFilters] = useState<TaskFilters>({});

  // New UI-only filters (client-side)
  const [priorityFilter, setPriorityFilter] = useState<'any' | TaskPriority>('any');
  const [urgencyFilter, setUrgencyFilter] = useState<UrgencyFilter>('any');
  const [search, setSearch] = useState('');

  const [showForm, setShowForm] = useState(false);

  // Fetch tasks on mount and when backend filters/view change
  useEffect(() => {
    loadTasks();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filters, viewMode]);

  function sevenDaysAgoISO(): string {
    const d = new Date();
    d.setDate(d.getDate() - 7);
    return d.toISOString();
  }

  const loadTasks = async () => {
    setLoading(true);
    setError(null);

    try {
      // Build backend query based on mode
      const backendFilters: any = { ...(filters as any) };

      if (viewMode === 'active') {
        // Default backend behavior: active only (include_closed=false)
        // Ensure we do not accidentally send completed_since from some previous state
        delete backendFilters.completed_since;
        delete backendFilters.include_closed;
      } else {
        // Completed in last 7 days:
        // - include_closed=true
        // - completed_since=<ISO>
        backendFilters.include_closed = true;
        backendFilters.completed_since = sevenDaysAgoISO();

        // Optional hardening: ensure status=done on client too.
        // Not required if backend enforces it when completed_since is provided.
        backendFilters.status = 'done' as TaskStatus;
      }

      const response = await tasksApi.listTasks(backendFilters);
      setTasks(response.tasks);

      console.log('[loadTasks] mode:', viewMode, 'filters:', backendFilters, 'response:', response);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load tasks');
    } finally {
      setLoading(false);
    }
  };

  // Apply UI filters client-side (priority + urgency + search)
  const visibleTasks = useMemo(() => {
    const q = search.trim().toLowerCase();

    return tasks
      .filter((t) => (priorityFilter === 'any' ? true : t.priority === priorityFilter))
      .filter((t) => (urgencyFilter === 'any' ? true : (t.urgency as any) === urgencyFilter))
      .filter((t) => {
        if (!q) return true;
        const hay = `${t.title ?? ''} ${t.description ?? ''}`.toLowerCase();
        return hay.includes(q);
      });
  }, [tasks, priorityFilter, urgencyFilter, search]);

  const handleTaskCreated = (task: Task) => {
    // In completed view, a newly created task shouldn't appear (it's not done)
    if (viewMode !== 'active') {
      setShowForm(false);
      return;
    }

    // If created task is done/canceled (unlikely), just refresh
    if (task.status === 'done' || task.status === 'canceled') {
      setShowForm(false);
      void loadTasks();
      return;
    }

    setTasks((prev) => [task, ...prev]);
    setShowForm(false);
  };

  const handleTaskUpdated = (updatedTask: Task) => {
    setTasks((prev) => {
      // ACTIVE view: if it becomes done/canceled, remove from the list
      if (viewMode === 'active') {
        if (updatedTask.status === 'done' || updatedTask.status === 'canceled') {
          return prev.filter((t) => t.id !== updatedTask.id);
        }
      }

      // COMPLETED view: if it stops being done, remove from completed list
      if (viewMode === 'completed_7d') {
        if (updatedTask.status !== 'done') {
          return prev.filter((t) => t.id !== updatedTask.id);
        }
      }

      // Otherwise update in-place
      return prev.map((t) => (t.id === updatedTask.id ? updatedTask : t));
    });
  };

  const handleTaskDeleted = (taskId: string) => {
    setTasks((prev) => prev.filter((t) => t.id !== taskId));
  };

  const isCompletedView = viewMode === 'completed_7d';

  return (
    <div className="tasks-page">
      <header className="tasks-header">
        <h1>{isCompletedView ? 'Completed (last 7 days)' : 'My Tasks'}</h1>

        <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
          {/* View toggle (backend fetch mode) */}
          <select
            value={viewMode}
            onChange={(e) => setViewMode(e.target.value as ViewMode)}
            title="Choose which tasks to fetch from the server"
          >
            <option value="active">View: Active</option>
            <option value="completed_7d">View: Completed (7 days)</option>
          </select>

          {/* UI filters (client-side) */}
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

          {/* Only allow creating tasks in Active view */}
          <button onClick={() => setShowForm(true)} disabled={isCompletedView}>
            + New Task
          </button>

          <button onClick={loadTasks} disabled={loading}>
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

      {/* Floating chat widget for conversational task creation */}
      {!isCompletedView && <ChatWidget onTaskCreated={handleTaskCreated} />}
    </div>
  );
}
