/**
 * TaskForm
 * 
 * Purpose: Create new tasks via form input
 * 
 * Responsibilities:
 * - Display form fields (title, description, priority, due date)
 * - Validate input before submission
 * - Call tasksApi.createTask() on submit
 * - Handle loading and error states
 * - Notify parent component on success
 * 
 * API: tasksApi.createTask()
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
    const [dueDate, setDueDate] = useState('');
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
                dueDate: dueDate || undefined,
            });
            onSubmit(task);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to create task');
        } finally {
            setLoading(false);
        }
    };

    return (
        <form className="task-form" onSubmit={handleSubmit}>
            <h2>New Task</h2>

            {error && <div className="error">{error}</div>}

            <div className="form-group">
                <label htmlFor="title">Title *</label>
                <input
                    id="title"
                    type="text"
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                    required
                    disabled={loading}
                    placeholder="What needs to be done?"
                />
            </div>

            <div className="form-group">
                <label htmlFor="description">Description</label>
                <textarea
                    id="description"
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    disabled={loading}
                    placeholder="Add more details..."
                    rows={3}
                />
            </div>

            <div className="form-row">
                <div className="form-group">
                    <label htmlFor="priority">Priority</label>
                    <select
                        id="priority"
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
                    <label htmlFor="dueDate">Due Date</label>
                    <input
                        id="dueDate"
                        type="date"
                        value={dueDate}
                        onChange={(e) => setDueDate(e.target.value)}
                        disabled={loading}
                    />
                </div>
            </div>

            <div className="form-actions">
                <button type="button" onClick={onCancel} disabled={loading}>
                    Cancel
                </button>
                <button type="submit" disabled={loading}>
                    {loading ? 'Creating...' : 'Create Task'}
                </button>
            </div>
        </form>
    );
}
