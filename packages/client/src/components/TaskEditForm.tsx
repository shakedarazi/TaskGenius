/**
 * TaskEditForm
 *
 * Purpose: Edit existing task fields via PATCH /tasks/{id}
 * Contract: backend accepts partial updates (title/description/priority/deadline/status)
 */

import { useMemo, useState, type FormEvent } from 'react';
import { tasksApi } from '@/api';
import type { Task, TaskPriority } from '@/types';

interface TaskEditFormProps {
  task: Task;
  onUpdated: (task: Task) => void;
  onCancel: () => void;
}

export function TaskEditForm({ task, onUpdated, onCancel }: TaskEditFormProps) {
  const initialDeadline = useMemo(() => {
    // backend returns "2026-01-15T00:00:00" sometimes. <input type="date"> needs YYYY-MM-DD
    if (!task.deadline) return '';
    return task.deadline.slice(0, 10);
  }, [task.deadline]);

  const [title, setTitle] = useState(task.title);
  const [description, setDescription] = useState(task.description ?? '');
  const [priority, setPriority] = useState<TaskPriority>(task.priority);
  const [deadline, setDeadline] = useState(initialDeadline);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      // Send only fields we actually support editing here.
      // Keep contract snake_case: "deadline"
      const updated = await tasksApi.updateTask(task.id, {
        title,
        description: description.trim() === '' ? undefined : description,
        priority,
        deadline: deadline === '' ? undefined : deadline,
      });
      

      onUpdated(updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update task');
    } finally {
      setLoading(false);
    }
  };

  return (
    <form className="task-form task-edit-form" onSubmit={handleSubmit}>
      <h2>Edit Task</h2>

      {error && <div className="error">{error}</div>}

      <div className="form-group">
        <label htmlFor={`edit-title-${task.id}`}>Title *</label>
        <input
          id={`edit-title-${task.id}`}
          type="text"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          required
          disabled={loading}
        />
      </div>

      <div className="form-group">
        <label htmlFor={`edit-description-${task.id}`}>Description</label>
        <textarea
          id={`edit-description-${task.id}`}
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          disabled={loading}
          rows={3}
        />
      </div>

      <div className="form-row">
        <div className="form-group">
          <label htmlFor={`edit-priority-${task.id}`}>Priority</label>
          <select
            id={`edit-priority-${task.id}`}
            value={priority}
            onChange={(e) => setPriority(e.target.value as TaskPriority)}
            disabled={loading}
          >
            <option value="low">Low</option>
            <option value="medium">Medium</option>
            <option value="high">High</option>
            <option value="urgent">Urgent</option>
          </select>
        </div>

        <div className="form-group">
          <label htmlFor={`edit-deadline-${task.id}`}>Due Date</label>
          <input
            id={`edit-deadline-${task.id}`}
            type="date"
            value={deadline}
            onChange={(e) => setDeadline(e.target.value)}
            disabled={loading}
          />
        </div>
      </div>

      <div className="form-actions">
        <button type="button" onClick={onCancel} disabled={loading}>
          Cancel
        </button>
        <button type="submit" disabled={loading}>
          {loading ? 'Saving...' : 'Save Changes'}
        </button>
      </div>
    </form>
  );
}
