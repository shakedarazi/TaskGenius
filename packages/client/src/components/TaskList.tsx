/**
 * TaskList
 *
 * Purpose: Display list of tasks with actions
 */

import { useState, useEffect } from 'react';
import { tasksApi } from '@/api';
import type { Task } from '@/types';
import { TaskEditForm } from '@/components/TaskEditForm';

interface TaskListProps {
  tasks: Task[];
  loading: boolean;
  onUpdate: (task: Task) => void;
  onDelete: (taskId: string) => void;
}

export function TaskList({ tasks, loading, onUpdate, onDelete }: TaskListProps) {
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [editingTaskId, setEditingTaskId] = useState<string | null>(null);
  const [editingTask, setEditingTask] = useState<Task | null>(null);
  const [deletingTaskId, setDeletingTaskId] = useState<string | null>(null);
  const [deletingTaskTitle, setDeletingTaskTitle] = useState<string>('');

  // Find the task being edited
  useEffect(() => {
    if (editingTaskId) {
      const task = tasks.find(t => t.id === editingTaskId);
      setEditingTask(task || null);
    } else {
      setEditingTask(null);
    }
  }, [editingTaskId, tasks]);

  // Prevent body scroll when modal is open
  useEffect(() => {
    if (editingTask || deletingTaskId) {
      document.body.classList.add('modal-open');
    } else {
      document.body.classList.remove('modal-open');
    }
    return () => {
      document.body.classList.remove('modal-open');
    };
  }, [editingTask, deletingTaskId]);

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

  const handleDeleteClick = (task: Task) => {
    setDeletingTaskId(task.id);
    setDeletingTaskTitle(task.title);
  };

  const handleDeleteConfirm = async () => {
    if (!deletingTaskId) return;

    setActionLoading(deletingTaskId);
    try {
      await tasksApi.deleteTask(deletingTaskId);
      onDelete(deletingTaskId);
      setDeletingTaskId(null);
      setDeletingTaskTitle('');
    } catch (err) {
      console.error('Failed to delete task:', err);
    } finally {
      setActionLoading(null);
    }
  };

  const handleDeleteCancel = () => {
    setDeletingTaskId(null);
    setDeletingTaskTitle('');
  };

  if (loading) {
    return (
      <div className="text-center py-5">
        <div className="spinner-border text-primary" role="status">
          <span className="visually-hidden">Loading tasks...</span>
        </div>
      </div>
    );
  }

  if (tasks.length === 0) {
    return (
      <div className="text-center py-5">
        <p className="text-muted">No tasks yet. Create one to get started!</p>
      </div>
    );
  }

  // Helper function to get priority badge class
  const getPriorityBadgeClass = (priority: string) => {
    return `badge badge-priority-${priority} me-2`;
  };

  // Helper function to get priority border class
  const getPriorityBorderClass = (priority: string) => {
    return `priority-${priority}`;
  };

  const handleEditComplete = (updated: Task) => {
    onUpdate(updated);
    setEditingTaskId(null);
    setEditingTask(null);
  };

  const handleEditCancel = () => {
    setEditingTaskId(null);
    setEditingTask(null);
  };

  return (
    <>
      {/* Delete Confirmation Modal */}
      {deletingTaskId && (
        <>
          <div 
            className="modal-backdrop fade show" 
            style={{ backdropFilter: 'blur(4px)', WebkitBackdropFilter: 'blur(4px)' }}
            onClick={handleDeleteCancel}
          ></div>
          
          <div 
            className="modal fade show" 
            style={{ display: 'block' }}
            tabIndex={-1}
            role="dialog"
            aria-labelledby="deleteTaskModalLabel"
            aria-modal="true"
            onClick={(e) => {
              if (e.target === e.currentTarget) {
                handleDeleteCancel();
              }
            }}
          >
            <div 
              className="modal-dialog modal-dialog-centered" 
              onClick={(e) => e.stopPropagation()}
            >
              <div 
                className="modal-content"
                onClick={(e) => e.stopPropagation()}
                style={{ borderRadius: '12px' }}
              >
                <div className="modal-header bg-primary text-white" style={{ borderRadius: '12px 12px 0 0' }}>
                  <h5 className="modal-title" id="deleteTaskModalLabel">
                    <i className="bi bi-exclamation-triangle-fill me-2"></i>Delete Task
                  </h5>
                  <button 
                    type="button" 
                    className="btn-close btn-close-white" 
                    onClick={handleDeleteCancel}
                    aria-label="Close"
                  ></button>
                </div>
                <div className="modal-body">
                  <p className="mb-0">
                    Are you sure you want to delete <strong>"{deletingTaskTitle}"</strong>?
                  </p>
                  <p className="text-muted small mt-2 mb-0">This action cannot be undone.</p>
                </div>
                <div className="modal-footer">
                  <button 
                    type="button" 
                    className="btn btn-outline-secondary"
                    onClick={handleDeleteCancel}
                    disabled={actionLoading === deletingTaskId}
                  >
                    Cancel
                  </button>
                  <button 
                    type="button" 
                    className="btn btn-danger"
                    onClick={handleDeleteConfirm}
                    disabled={actionLoading === deletingTaskId}
                  >
                    {actionLoading === deletingTaskId ? (
                      <>
                        <span className="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>
                        Deleting...
                      </>
                    ) : (
                      <>
                        <i className="bi bi-trash me-1"></i>Delete
                      </>
                    )}
                  </button>
                </div>
              </div>
            </div>
          </div>
        </>
      )}

      {/* Edit Task Modal */}
      {editingTask && (
        <>
          {/* Backdrop with blur - closes modal on click */}
          <div 
            className="modal-backdrop fade show" 
            style={{ backdropFilter: 'blur(4px)', WebkitBackdropFilter: 'blur(4px)' }}
            onClick={handleEditCancel}
          ></div>
          
          {/* Modal container - centered */}
          <div 
            className="modal fade show" 
            style={{ display: 'block' }}
            tabIndex={-1}
            role="dialog"
            aria-labelledby="editTaskModalLabel"
            aria-modal="true"
            onClick={(e) => {
              // Close modal only when clicking directly on the modal container (not on dialog/content)
              if (e.target === e.currentTarget) {
                handleEditCancel();
              }
            }}
          >
            <div 
              className="modal-dialog modal-dialog-centered modal-lg" 
              onClick={(e) => {
                // Prevent clicks on modal-dialog from bubbling up and closing modal
                e.stopPropagation();
              }}
            >
              <div 
                className="modal-content"
                onClick={(e) => {
                  // Prevent clicks on modal-content from bubbling up and closing modal
                  e.stopPropagation();
                }}
              >
                <TaskEditForm
                  task={editingTask}
                  onUpdated={handleEditComplete}
                  onCancel={handleEditCancel}
                />
              </div>
            </div>
          </div>
        </>
      )}

      {/* Desktop: Table View (md and up) */}
      <div className="d-none d-md-block">
        <div className="table-responsive">
          <table className="table table-hover align-middle">
            <thead className="table-light">
              <tr>
                <th scope="col" style={{ width: '40%' }}>Title</th>
                <th scope="col" style={{ width: '15%' }}>Priority</th>
                <th scope="col" style={{ width: '15%' }}>Deadline</th>
                <th scope="col" style={{ width: '10%' }}>Status</th>
                <th scope="col" style={{ width: '20%' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {tasks.map((task, index) => {
                const isEditing = editingTaskId === task.id;
                const isLoading = actionLoading === task.id;

                return (
                  <tr
                    key={task.id}
                    className={`${getPriorityBorderClass(task.priority)} ${task.status === 'done' ? 'table-secondary' : ''} ${isLoading ? 'opacity-75' : ''}`}
                    style={{
                      animationDelay: `${index * 0.05}s`,
                    }}
                  >
                    <td>
                      <div>
                        <strong>{task.title}</strong>
                        {task.description && (
                          <p className="text-muted small mb-0 mt-1">{task.description}</p>
                        )}
                      </div>
                    </td>
                    <td>
                      <span className={getPriorityBadgeClass(task.priority)}>
                        {task.priority}
                      </span>
                    </td>
                    <td>
                      {task.deadline ? (
                        <span className="text-muted">
                          {new Date(task.deadline).toLocaleDateString()}
                        </span>
                      ) : (
                        <span className="text-muted">—</span>
                      )}
                    </td>
                    <td>
                      <span className={`badge ${task.status === 'done' ? 'bg-success' : task.status === 'in_progress' ? 'bg-info' : 'bg-secondary'}`}>
                        {task.status}
                      </span>
                    </td>
                    <td>
                      <div className="btn-group btn-group-sm" role="group">
                        <button
                          className="btn btn-outline-primary"
                          onClick={() => setEditingTaskId(isEditing ? null : task.id)}
                          disabled={actionLoading === task.id}
                          title={isEditing ? 'Close' : 'Edit'}
                        >
                          <i className={`bi ${isEditing ? 'bi-x-lg' : 'bi-pencil'}`}></i>
                        </button>
                        <button
                          className="btn btn-outline-success"
                          onClick={() => handleToggleComplete(task)}
                          disabled={actionLoading === task.id || isEditing}
                          title={task.status === 'done' ? 'Reopen' : 'Complete'}
                        >
                          <i className={`bi ${task.status === 'done' ? 'bi-arrow-counterclockwise' : 'bi-check-lg'}`}></i>
                        </button>
                        <button
                          className="btn btn-outline-danger"
                          onClick={() => handleDeleteClick(task)}
                          disabled={actionLoading === task.id || isEditing}
                          title="Delete"
                        >
                          <i className="bi bi-trash"></i>
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Mobile: Card View (below md) */}
      <div className="d-md-none">
        <div className="row g-3">
          {tasks.map((task, index) => {
            const isEditing = editingTaskId === task.id;
            const isLoading = actionLoading === task.id;

            return (
              <div 
                key={task.id} 
                className="col-12"
                style={{
                  animationDelay: `${index * 0.05}s`,
                }}
              >
                <div className={`card task-card ${getPriorityBorderClass(task.priority)} ${task.status === 'done' ? 'opacity-75' : ''} ${isLoading ? 'opacity-75' : ''}`}>
                  <div className="card-body">
                    <div className="d-flex justify-content-between align-items-start mb-2">
                      <h5 className="card-title mb-0">{task.title}</h5>
                      <span className={getPriorityBadgeClass(task.priority)}>
                        {task.priority}
                      </span>
                    </div>

                    {task.description && (
                      <p className="card-text text-muted small">{task.description}</p>
                    )}

                    <div className="d-flex justify-content-between align-items-center mb-3">
                      <div>
                        {task.deadline ? (
                          <small className="text-muted">
                            <i className="bi bi-calendar3 me-1"></i>
                            {new Date(task.deadline).toLocaleDateString()}
                          </small>
                        ) : (
                          <small className="text-muted">No deadline</small>
                        )}
                      </div>
                      <span className={`badge ${task.status === 'done' ? 'bg-success' : task.status === 'in_progress' ? 'bg-info' : 'bg-secondary'}`}>
                        {task.status}
                      </span>
                    </div>


                    <div className="d-grid gap-2 d-md-flex justify-content-md-end">
                      <button
                        className={`btn btn-sm btn-outline-primary ${isLoading && !isEditing ? 'btn-loading' : ''}`}
                        onClick={() => setEditingTaskId(isEditing ? null : task.id)}
                        disabled={actionLoading === task.id}
                      >
                        <i className={`bi ${isEditing ? 'bi-x-lg' : 'bi-pencil'}`}></i>
                        {isEditing ? ' Close' : ' Edit'}
                      </button>
                      <button
                        className={`btn btn-sm btn-outline-success ${isLoading && !isEditing ? 'btn-loading' : ''}`}
                        onClick={() => handleToggleComplete(task)}
                        disabled={actionLoading === task.id || isEditing}
                      >
                        <i className={`bi ${task.status === 'done' ? 'bi-arrow-counterclockwise' : 'bi-check-lg'}`}></i>
                        {task.status === 'done' ? ' Reopen' : ' Complete'}
                      </button>
                      <button
                        className={`btn btn-sm btn-outline-danger ${isLoading && !isEditing ? 'btn-loading' : ''}`}
                        onClick={() => handleDeleteClick(task)}
                        disabled={actionLoading === task.id || isEditing}
                      >
                        <i className="bi bi-trash"></i> Delete
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </>
  );
}
