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
  TaskFilters,
} from '@/types';

type ExtraListFilters = {
  include_closed?: boolean;
  completed_since?: string; // ISO string
};

type ListFilters = TaskFilters & ExtraListFilters;

function normalizeTask(raw: any): Task {
  return {
    id: raw.id ?? raw._id,
    owner_id: raw.user_id ?? raw.owner_id,

    title: raw.title,
    description: raw.description ?? undefined,

    status: raw.status, // 'open' | 'in_progress' | 'done' | 'canceled'
    priority: raw.priority,

    tags: raw.tags ?? undefined,

    // Derived urgency from backend
    urgency: raw.urgency,

    // backend uses "deadline"
    deadline: raw.deadline ?? undefined,

    completed_at: raw.completed_at ?? undefined,
    created_at: raw.created_at,
    updated_at: raw.updated_at,
  };
}

function normalizeTaskListResponse(raw: any): TaskListResponse {
  return {
    tasks: (raw.tasks ?? []).map(normalizeTask),
    total: raw.total ?? 0,
  };
}

function buildListEndpoint(filters?: ListFilters): string {
  const params = new URLSearchParams();

  // Existing typed filters (some may not be supported by backend; safe to send anyway only if backend ignores)
  if (filters?.status) params.set('status', filters.status);
  if (filters?.priority) params.set('priority', filters.priority);
  if (filters?.search) params.set('search', filters.search);
  if (filters?.page) params.set('page', String(filters.page));
  if (filters?.limit) params.set('limit', String(filters.limit));

  // Extra backend filters
  if (filters?.include_closed === true) params.set('include_closed', 'true');
  if (filters?.completed_since) params.set('completed_since', filters.completed_since);

  const query = params.toString();
  return query ? `/tasks?${query}` : '/tasks';
}

/**
 * Fetch tasks for the current user
 */
export async function listTasks(filters?: ListFilters): Promise<TaskListResponse> {
  const endpoint = buildListEndpoint(filters);
  const raw = await apiClient.get<any>(endpoint);
  return normalizeTaskListResponse(raw);
}

/**
 * Get a single task by ID
 */
export async function getTask(taskId: string): Promise<Task> {
  const raw = await apiClient.get<any>(`/tasks/${taskId}`);
  return normalizeTask(raw);
}

/**
 * Create a new task
 */
export async function createTask(data: CreateTaskRequest): Promise<Task> {
  const payload = {
    title: data.title,
    description: data.description,
    priority: data.priority,
    tags: data.tags,
    deadline: data.deadline,
  };

  const raw = await apiClient.post<any>('/tasks', payload);
  return normalizeTask(raw);
}

/**
 * Update an existing task
 */
export async function updateTask(taskId: string, data: UpdateTaskRequest): Promise<Task> {
  const payload = {
    ...data,
    deadline: data.deadline,
  };

  const raw = await apiClient.patch<any>(`/tasks/${taskId}`, payload);
  return normalizeTask(raw);
}

/**
 * Delete a task
 */
export async function deleteTask(taskId: string): Promise<void> {
  await apiClient.delete<void>(`/tasks/${taskId}`);
}

/**
 * Mark a task as complete: status -> 'done' (kept in DB)
 */
export async function completeTask(taskId: string): Promise<Task> {
  const raw = await apiClient.patch<any>(`/tasks/${taskId}`, { status: 'done' });
  return normalizeTask(raw);
}

/**
 * Reopen a completed task: status -> 'open'
 */
export async function reopenTask(taskId: string): Promise<Task> {
  const raw = await apiClient.patch<any>(`/tasks/${taskId}`, { status: 'open' });
  return normalizeTask(raw);
}
