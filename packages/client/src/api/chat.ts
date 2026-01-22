/**
 * Chat API Module
 * 
 * Handles chat/conversational interactions.
 * Messages are sent to core-api, which orchestrates with chatbot-service internally.
 */

import { apiClient } from './client';
import type { ChatResponse } from '@/types';

/**
 * Send a chat message to get suggestions
 */
export async function sendMessage(message: string): Promise<ChatResponse> {
    return apiClient.post<ChatResponse>('/chat', { message });
}

/**
 * Add a task by selecting a suggestion number
 */
export async function selectSuggestion(selection: number): Promise<ChatResponse> {
    return apiClient.post<ChatResponse>('/chat', { selection });
}
