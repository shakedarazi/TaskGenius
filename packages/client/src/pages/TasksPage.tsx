/**
 * TasksPage
 * 
 * Purpose: Main task management view (protected route)
 * 
 * Responsibilities:
 * - Fetch and display task list (TaskList component)
 * - Provide task creation (TaskForm component)
 * - Include chat widget for conversational task creation (ChatWidget)
 * - Handle task status updates (complete, reopen, delete)
 * - Support filtering and search
 * 
 * API: tasksApi.listTasks(), tasksApi.createTask(), etc.
 * Route: /tasks (protected)
 */

import { useState, useEffect } from 'react';
import { tasksApi } from '@/api';
import { TaskList } from '@/components/TaskList';
import { TaskForm } from '@/components/TaskForm';
import { ChatWidget } from '@/components/ChatWidget';
import type { Task, TaskFilters } from '@/types';

export function TasksPage() {
    const [tasks, setTasks] = useState<Task[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [filters, setFilters] = useState<TaskFilters>({});
    const [showForm, setShowForm] = useState(false);

    // Fetch tasks on mount and when filters change
    useEffect(() => {
        loadTasks();
    }, [filters]);

    const loadTasks = async () => {
        setLoading(true);
        setError(null);

        try {
            const response = await tasksApi.listTasks(filters);
            setTasks(response.items);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to load tasks');
        } finally {
            setLoading(false);
        }
    };

    const handleTaskCreated = (task: Task) => {
        setTasks((prev) => [task, ...prev]);
        setShowForm(false);
    };

    const handleTaskUpdated = (updatedTask: Task) => {
        setTasks((prev) =>
            prev.map((t) => (t.id === updatedTask.id ? updatedTask : t))
        );
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
                <TaskForm
                    onSubmit={handleTaskCreated}
                    onCancel={() => setShowForm(false)}
                />
            )}

            <TaskList
                tasks={tasks}
                loading={loading}
                onUpdate={handleTaskUpdated}
                onDelete={handleTaskDeleted}
            />

            {/* Floating chat widget for conversational task creation */}
            <ChatWidget onTaskCreated={handleTaskCreated} />
        </div>
    );
}
