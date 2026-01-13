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


export type UrgencyLevel = 'no_deadline' | 'overdue' | 'due_today' | 'due_soon' | 'not_soon';




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
    deadline?: string | null;
    urgency: UrgencyLevel;
    created_at: string;
    updated_at: string;
    completed_at: string | null;
}

/**
 * Create task request payload
 */
export interface CreateTaskRequest {
    title: string;
    description?: string | null;
    priority?: TaskPriority;
    tags?: string[];
    deadline?: string | null;
}

/**
 * Update task request payload
 * All fields optional for partial updates
 */
export interface UpdateTaskRequest {
    title?: string;
    description?: string | null;
    status?: TaskStatus;
    priority?: TaskPriority;
    tags?: string[] | null;
    deadline?: string | null;
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
    //page: number;
    //limit: number;
    //hasMore: boolean;
}
