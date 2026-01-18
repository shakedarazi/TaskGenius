/**
 * TaskForm
 *
 * Purpose: Create new tasks via form input
 */

import { useState, type FormEvent } from 'react';
import { tasksApi } from '@/api';
import type { Task, TaskPriority } from '@/types';

interface TaskFormProps {
  onSubmit: (task: Task) => void;
  onCancel: () => void;
}

export function TaskForm({ onSubmit, onCancel }: TaskFormProps) {
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [priority, setPriority] = useState<TaskPriority>('medium');
  const [deadline, setDeadline] = useState(''); // backend field
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      const task = await tasksApi.createTask({
        title,
        description: description || undefined,
        priority,
        deadline: deadline || undefined,
      });

      onSubmit(task);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create task');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="card">
      <div className="card-header bg-primary text-white">
        <h2 className="h4 mb-0">New Task</h2>
      </div>
      <div className="card-body">
        <form onSubmit={handleSubmit}>
          {error && (
            <div className="alert alert-danger" role="alert">
              {error}
            </div>
          )}

          <div className="mb-3">
            <label htmlFor="title" className="form-label">Title *</label>
            <input
              id="title"
              type="text"
              className="form-control"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              required
              disabled={loading}
              placeholder="What needs to be done?"
            />
          </div>

          <div className="mb-3">
            <label htmlFor="description" className="form-label">Description</label>
            <textarea
              id="description"
              className="form-control"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              disabled={loading}
              placeholder="Add more details..."
              rows={3}
            />
          </div>

          <div className="row">
            <div className="col-md-6 mb-3">
              <label htmlFor="priority" className="form-label">Priority</label>
              <select
                id="priority"
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
              <label htmlFor="deadline" className="form-label">Due Date</label>
              <input
                id="deadline"
                type="date"
                className="form-control"
                value={deadline}
                onChange={(e) => setDeadline(e.target.value)}
                disabled={loading}
              />
            </div>
          </div>

          <div className="d-flex gap-2 justify-content-end">
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
                  Creating...
                </>
              ) : (
                <>
                  <i className="bi bi-plus-lg me-1"></i>Create Task
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
