/**
 * Chat API Module
 * 
 * Handles chat/conversational interactions.
 * Messages are sent to core-api, which orchestrates with chatbot-service internally.
 * 
 * IMPORTANT: 
 * - Client sends messages to core-api ONLY
 * - chatbot-service is advisory only (provides intent/entity extraction)
 * - core-api executes any resulting task mutations
 * - Client NEVER communicates directly with chatbot-service
 */

import { apiClient } from './client';
import type {
    ChatMessage,
    ChatRequest,
    ChatResponse,
    ChatHistory
} from '@/types';

/**
 * Send a chat message
 * 
 * Flow:
 * 1. Client -> core-api: Send message
 * 2. core-api -> chatbot-service: Get intent/entities (internal)
 * 3. core-api: Execute any actions (task creation, etc.)
 * 4. core-api -> Client: Return response with results
 */
export async function sendMessage(request: ChatRequest): Promise<ChatResponse> {
    return apiClient.post<ChatResponse>('/chat', request);
}

/**
 * Get chat history for the current user
 */
export async function getHistory(limit?: number): Promise<ChatHistory> {
    const endpoint = limit ? `/chat/history?limit=${limit}` : '/chat/history';
    return apiClient.get<ChatHistory>(endpoint);
}

/**
 * Clear chat history
 */
export async function clearHistory(): Promise<void> {
    return apiClient.delete<void>('/chat/history');
}
