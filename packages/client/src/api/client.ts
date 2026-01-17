/**
 * API Client - HTTP Layer
 * 
 * Typed HTTP client wrapper for communicating with core-api.
 * Handles authentication, error handling, and request/response serialization.
 * 
 * IMPORTANT: All requests go to core-api ONLY.
 * Never communicate directly with chatbot-service or MongoDB.
 */

import type { ApiError } from '@/types';

// Base URL from environment, fallback to relative path for Vite proxy
const BASE_URL = import.meta.env.VITE_CORE_API_BASE_URL || '';
const API_PREFIX = '';


/**
 * Storage keys for auth tokens
 */
const TOKEN_KEY = 'taskgenius_token';

/**
 * Get stored auth token
 */
export function getToken(): string | null {
    return localStorage.getItem(TOKEN_KEY);
}

/**
 * Store auth token
 */
export function setToken(token: string): void {
    localStorage.setItem(TOKEN_KEY, token);
}

/**
 * Remove auth token
 */
export function clearToken(): void {
    localStorage.removeItem(TOKEN_KEY);
    // Also clear chat history on logout
    localStorage.removeItem('taskgenius_chat_history');
}

/**
 * Check if user is authenticated
 */
export function isAuthenticated(): boolean {
    return getToken() !== null;
}

/**
 * Build request headers with auth token if available
 */
function buildHeaders(customHeaders?: HeadersInit): Headers {
    const headers = new Headers(customHeaders);

    if (!headers.has('Content-Type')) {
        headers.set('Content-Type', 'application/json');
    }

    const token = getToken();
    if (token) {
        headers.set('Authorization', `Bearer ${token}`);
    }

    return headers;
}

/**
 * Handle API response and extract JSON or throw error
 */
async function handleResponse<T>(response: Response): Promise<T> {
    if (!response.ok) {
        let error: ApiError;

        try {
            error = await response.json();
        } catch {
            error = {
                code: 'unknown_error',
                message: response.statusText || 'An unknown error occurred',
            };
        }

        // Handle 401 by clearing token
        if (response.status === 401) {
            clearToken();
        }

        throw error;
    }

    // Handle empty responses (204 No Content)
    if (response.status === 204) {
        return undefined as T;
    }

    return response.json();
}

/**
 * Generic API request function
 */
async function request<T>(
    method: string,
    endpoint: string,
    body?: unknown,
    customHeaders?: HeadersInit,
    signal?: AbortSignal
): Promise<T> {
    const url = `${BASE_URL}${API_PREFIX}${endpoint}`;

    const options: RequestInit = {
        method,
        headers: buildHeaders(customHeaders),
        signal,
    };

    if (body !== undefined) {
        options.body = JSON.stringify(body);
    }

    const response = await fetch(url, options);
    return handleResponse<T>(response);
}

/**
 * Typed API client with HTTP method shortcuts
 */
export const apiClient = {
    get: <T>(endpoint: string, signal?: AbortSignal) => 
        request<T>('GET', endpoint, undefined, undefined, signal),

    post: <T>(endpoint: string, body?: unknown, signal?: AbortSignal) =>
        request<T>('POST', endpoint, body, undefined, signal),

    put: <T>(endpoint: string, body?: unknown, signal?: AbortSignal) =>
        request<T>('PUT', endpoint, body, undefined, signal),

    patch: <T>(endpoint: string, body?: unknown, signal?: AbortSignal) =>
        request<T>('PATCH', endpoint, body, undefined, signal),

    delete: <T>(endpoint: string, signal?: AbortSignal) => 
        request<T>('DELETE', endpoint, undefined, undefined, signal),
};
