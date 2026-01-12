/**
 * TasksPage
 *
 * Default behavior (A):
 * - "Complete" marks task as status="done" (kept in DB)
 * - UI shows ACTIVE tasks only by default (hides done/canceled)
 */

import { useState, useEffect } from 'react';
import { tasksApi } from '@/api';
import { TaskList } from '@/components/TaskList';
import { TaskForm } from '@/components/TaskForm';
import { ChatWidget } from '@/components/ChatWidget';
import type { Task, TaskFilters } from '@/types';

const HIDDEN_STATUSES = new Set(['done', 'canceled'] as const);

export function TasksPage() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState<TaskFilters>({});
  const [showForm, setShowForm] = useState(false);

  // Fetch tasks on mount and when filters change
  useEffect(() => {
    loadTasks();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filters]);

  const loadTasks = async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await tasksApi.listTasks(filters);

      // Default view: active tasks only (hide done/canceled)
      const visible = response.tasks.filter((t) => !HIDDEN_STATUSES.has(t.status as any));

      setTasks(visible);
      console.log('[loadTasks] response:', response);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load tasks');
    } finally {
      setLoading(false);
    }
  };

  const handleTaskCreated = (task: Task) => {
    // If a created task is already done/canceled (unlikely), don't show it in active list
    if (HIDDEN_STATUSES.has(task.status as any)) {
      setShowForm(false);
      return;
    }

    setTasks((prev) => [task, ...prev]);
    setShowForm(false);
  };

  const handleTaskUpdated = (updatedTask: Task) => {
    setTasks((prev) => {
      // If it became done/canceled, remove from active list immediately
      if (HIDDEN_STATUSES.has(updatedTask.status as any)) {
        return prev.filter((t) => t.id !== updatedTask.id);
      }

      // Otherwise update in-place
      return prev.map((t) => (t.id === updatedTask.id ? updatedTask : t));
    });
  };

  const handleTaskDeleted = (taskId: string) => {
    setTasks((prev) => prev.filter((t) => t.id !== taskId));
  };

  return (
    <div className="tasks-page">
      <header className="tasks-header">
        <h1>My Tasks</h1>
        <button onClick={() => setShowForm(true)}>+ New Task</button>
      </header>

      {error && <div className="error">{error}</div>}

      {showForm && (
        <TaskForm onSubmit={handleTaskCreated} onCancel={() => setShowForm(false)} />
      )}

      <TaskList tasks={tasks} loading={loading} onUpdate={handleTaskUpdated} onDelete={handleTaskDeleted} />

      {/* Floating chat widget for conversational task creation */}
      <ChatWidget onTaskCreated={handleTaskCreated} />
    </div>
  );
}
