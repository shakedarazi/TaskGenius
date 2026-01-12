/**
 * Task Types
 * 
 * DTOs for task management operations.
 * Enums should match shared/contracts/enums.json
 */

/**
 * Task status enum
 * Must match: shared/contracts/enums.json -> TaskStatus
 */
export type TaskStatus = 'open' | 'in_progress' | 'done' | 'canceled';
/**
 * Task priority enum
 * Must match: shared/contracts/enums.json -> TaskPriority
 */
export type TaskPriority = 'low' | 'medium' | 'high' | 'urgent';

/**
 * Task entity
 */
export interface Task {
    id: string;
    owner_id: string;
    title: string;
    description?: string;
    status: TaskStatus;
    priority: TaskPriority;
    tags?: string[];
    deadline?: string;
    completed_at?: string;
    created_at: string;
    updated_at: string;
}

/**
 * Create task request payload
 */
export interface CreateTaskRequest {
    title: string;
    description?: string;
    priority?: TaskPriority;
    tags?: string[];
    deadline?: string;
}

/**
 * Update task request payload
 * All fields optional for partial updates
 */
export interface UpdateTaskRequest {
    title?: string;
    description?: string;
    status?: TaskStatus;
    priority?: TaskPriority;
    tags?: string[];
    deadline?: string;
}

/**
 * Task list filters
 */
export interface TaskFilters {
    status?: TaskStatus;
    priority?: TaskPriority;
    search?: string;
    page?: number;
    limit?: number;
}

/**
 * Task list response
 */
export interface TaskListResponse {
    tasks: Task[];
    total: number;
    page: number;
    limit: number;
    hasMore: boolean;
}
