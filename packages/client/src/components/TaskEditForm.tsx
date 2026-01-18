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
    <>
      <div className="modal-header bg-primary text-white">
        <h2 className="modal-title h5" id="editTaskModalLabel">Edit Task</h2>
        <button 
          type="button" 
          className="btn-close btn-close-white" 
          onClick={onCancel}
          aria-label="Close"
        ></button>
      </div>
      <div className="modal-body">
        <form onSubmit={handleSubmit}>
          {error && (
            <div className="alert alert-danger" role="alert">
              {error}
            </div>
          )}

          <div className="mb-3">
            <label htmlFor={`edit-title-${task.id}`} className="form-label">Title *</label>
            <input
              id={`edit-title-${task.id}`}
              type="text"
              className="form-control"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              required
              disabled={loading}
            />
          </div>

          <div className="mb-3">
            <label htmlFor={`edit-description-${task.id}`} className="form-label">Description</label>
            <textarea
              id={`edit-description-${task.id}`}
              className="form-control"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              disabled={loading}
              rows={3}
            />
          </div>

          <div className="row">
            <div className="col-md-6 mb-3">
              <label htmlFor={`edit-priority-${task.id}`} className="form-label">Priority</label>
              <select
                id={`edit-priority-${task.id}`}
                className="form-select"
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

            <div className="col-md-6 mb-3">
              <label htmlFor={`edit-deadline-${task.id}`} className="form-label">Due Date</label>
              <input
                id={`edit-deadline-${task.id}`}
                type="date"
                className="form-control"
                value={deadline}
                onChange={(e) => setDeadline(e.target.value)}
                disabled={loading}
              />
            </div>
          </div>

          <div className="modal-footer">
            <button 
              type="button" 
              className="btn btn-outline-secondary"
              onClick={onCancel} 
              disabled={loading}
            >
              Cancel
            </button>
            <button 
              type="submit" 
              className="btn btn-primary"
              disabled={loading}
            >
              {loading ? (
                <>
                  <span className="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>
                  Saving...
                </>
              ) : (
                <>
                  <i className="bi bi-check-lg me-1"></i>Save Changes
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </>
  );
}
