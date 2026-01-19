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
    intent?: string;
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
    /** Conversation history for context (list of {role: 'user'|'assistant', content: '...'}) */
    conversation_history?: Array<{ role: 'user' | 'assistant'; content: string }>;
}

export interface Command {
    intent: string;                 // add_task|update_task|delete_task|complete_task|list_tasks|clarify
    confidence: number;             // 0.0-1.0
    fields?: Record<string, any> | null;
    ref?: Record<string, any> | null;
    filter?: Record<string, any> | null;
    ready: boolean;
    missing_fields?: string[] | null;
}

export interface ChatResponse {
    reply: string;
    intent?: string;
    suggestions?: string[];
    command?: Command | null;       // <-- add this
}

/**
 * Chat history response
 */
export interface ChatHistory {
    messages: ChatMessage[];
    hasMore: boolean;
}
