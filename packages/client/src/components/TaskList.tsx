/**
 * TaskList
 *
 * Purpose: Display list of tasks with actions
 */

import { useState } from 'react';
import { tasksApi } from '@/api';
import type { Task } from '@/types';

interface TaskListProps {
  tasks: Task[];
  loading: boolean;
  onUpdate: (task: Task) => void;
  onDelete: (taskId: string) => void;
}

export function TaskList({ tasks, loading, onUpdate, onDelete }: TaskListProps) {
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  const handleToggleComplete = async (task: Task) => {
    setActionLoading(task.id);
    try {
      const updated =
        task.status === 'done'
          ? await tasksApi.reopenTask(task.id)
          : await tasksApi.completeTask(task.id);

      onUpdate(updated);
    } catch (err) {
      console.error('Failed to update task:', err);
    } finally {
      setActionLoading(null);
    }
  };

  const handleDelete = async (taskId: string) => {
    if (!confirm('Are you sure you want to delete this task?')) return;

    setActionLoading(taskId);
    try {
      await tasksApi.deleteTask(taskId);
      onDelete(taskId);
    } catch (err) {
      console.error('Failed to delete task:', err);
    } finally {
      setActionLoading(null);
    }
  };

  if (loading) return <div className="task-list-loading">Loading tasks...</div>;

  if (tasks.length === 0) {
    return (
      <div className="task-list-empty">
        <p>No tasks yet. Create one to get started!</p>
      </div>
    );
  }

  return (
    <ul className="task-list">
      {tasks.map((task) => (
        <li key={task.id} className={`task-item task-${task.status}`}>
          <div className="task-content">
            <h3 className="task-title">{task.title}</h3>

            {task.description && <p className="task-description">{task.description}</p>}

            <div className="task-meta">
              <span className={`priority priority-${task.priority}`}>{task.priority}</span>

              {task.deadline && (
                <span className="due-date">
                  Due: {new Date(task.deadline).toLocaleDateString()}
                </span>
              )}
            </div>
          </div>

          <div className="task-actions">
            <button onClick={() => handleToggleComplete(task)} disabled={actionLoading === task.id}>
              {task.status === 'done' ? 'Reopen' : 'Complete'}
            </button>

            <button
              onClick={() => handleDelete(task.id)}
              disabled={actionLoading === task.id}
              className="delete-btn"
            >
              Delete
            </button>
          </div>
        </li>
      ))}
    </ul>
  );
}
