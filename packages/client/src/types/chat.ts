/**
 * Chat Types
 * 
 * DTOs for chat/conversational operations.
 * Enums should match shared/contracts/enums.json
 */

/**
 * Chat intent enum
 * Must match: shared/contracts/enums.json -> ChatIntent
 */
export type ChatIntent =
    | 'create_task'
    | 'list_tasks'
    | 'complete_task'
    | 'delete_task'
    | 'query_status'
    | 'get_insights'
    | 'unknown';

/**
 * Single chat message
 */
export interface ChatMessage {
    id: string;
    role: 'user' | 'assistant';
    content: string;
    timestamp: string;
    /** Detected intent (for assistant messages) */
    intent?: ChatIntent;
    /** Actions that were executed (for assistant messages) */
    actions?: ChatAction[];
}

/**
 * Action executed as result of chat
 */
export interface ChatAction {
    type: 'task_created' | 'task_updated' | 'task_deleted' | 'tasks_listed';
    /** Related entity ID (e.g., task ID) */
    entityId?: string;
    /** Summary of what was done */
    summary: string;
}

/**
 * Chat request payload
 */
export interface ChatRequest {
    message: string;
    /** Optional context from previous messages */
    context?: string;
}

/**
 * Chat response from core-api
 */
export interface ChatResponse {
    message: ChatMessage;
    /** Any tasks that were affected */
    affectedTasks?: string[];
}

/**
 * Chat history response
 */
export interface ChatHistory {
    messages: ChatMessage[];
    hasMore: boolean;
}
