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
export type TaskStatus = 'pending' | 'in_progress' | 'completed' | 'cancelled';

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
    userId: string;
    title: string;
    description?: string;
    status: TaskStatus;
    priority: TaskPriority;
    tags?: string[];
    dueDate?: string;
    completedAt?: string;
    createdAt: string;
    updatedAt: string;
}

/**
 * Create task request payload
 */
export interface CreateTaskRequest {
    title: string;
    description?: string;
    priority?: TaskPriority;
    tags?: string[];
    dueDate?: string;
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
    dueDate?: string;
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
    items: Task[];
    total: number;
    page: number;
    limit: number;
    hasMore: boolean;
}
