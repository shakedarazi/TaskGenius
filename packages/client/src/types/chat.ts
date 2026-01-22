/**
 * Chat Types
 */

/**
 * Task suggestion from chatbot-service
 */
export interface TaskSuggestion {
    title: string;
    priority: string;
    category?: string | null;
    estimate_bucket?: string | null;
}

/**
 * Chat request payload
 */
export interface ChatRequest {
    message?: string;
    selection?: number;  // 1-based index to add a suggestion
}

/**
 * Chat response from core-api
 */
export interface ChatResponse {
    reply: string;
    suggestions?: TaskSuggestion[];
    added_task?: {
        id: string;
        title: string;
        priority: string;
    } | null;
}

/**
 * Single chat message for UI
 */
export interface ChatMessage {
    id: string;
    role: 'user' | 'assistant';
    content: string;
    timestamp: string;
}

/**
 * Chat history response
 */
export interface ChatHistory {
    messages: ChatMessage[];
    hasMore: boolean;
}
