/**
 * Tasks API Module
 * 
 * Handles task CRUD operations.
 * All mutations go through core-api which writes to MongoDB.
 * 
 * IMPORTANT: core-api is the ONLY executor of task mutations.
 */

import { apiClient } from './client';
import type {
    Task,
    CreateTaskRequest,
    UpdateTaskRequest,
    TaskListResponse,
    TaskFilters
} from '@/types';

/**
 * Fetch all tasks for the current user
 * Supports optional filtering and pagination
 */
export async function listTasks(filters?: TaskFilters): Promise<TaskListResponse> {
    const params = new URLSearchParams();

    if (filters?.status) params.set('status', filters.status);
    if (filters?.priority) params.set('priority', filters.priority);
    if (filters?.search) params.set('search', filters.search);
    if (filters?.page) params.set('page', String(filters.page));
    if (filters?.limit) params.set('limit', String(filters.limit));

    const query = params.toString();
    const endpoint = query ? `/tasks?${query}` : '/tasks';

    return apiClient.get<TaskListResponse>(endpoint);
}

/**
 * Get a single task by ID
 */
export async function getTask(taskId: string): Promise<Task> {
    return apiClient.get<Task>(`/tasks/${taskId}`);
}

/**
 * Create a new task
 */
export async function createTask(data: CreateTaskRequest): Promise<Task> {
    return apiClient.post<Task>('/tasks', data);
}

/**
 * Update an existing task
 */
export async function updateTask(taskId: string, data: UpdateTaskRequest): Promise<Task> {
    return apiClient.patch<Task>(`/tasks/${taskId}`, data);
}

/**
 * Delete a task
 */
export async function deleteTask(taskId: string): Promise<void> {
    return apiClient.delete<void>(`/tasks/${taskId}`);
}

/**
 * Mark a task as complete
 */
export async function completeTask(taskId: string): Promise<Task> {
    return apiClient.patch<Task>(`/tasks/${taskId}`, { status: 'completed' });
}

/**
 * Reopen a completed task
 */
export async function reopenTask(taskId: string): Promise<Task> {
    return apiClient.patch<Task>(`/tasks/${taskId}`, { status: 'pending' });
}
