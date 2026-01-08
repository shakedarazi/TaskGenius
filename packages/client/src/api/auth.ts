/**
 * Auth API Module
 * 
 * Handles authentication operations: login, register, logout, session management.
 * All requests go through core-api.
 */

import { apiClient, setToken, clearToken } from './client';
import type {
    LoginRequest,
    LoginResponse,
    RegisterRequest,
    RegisterResponse,
    User
} from '@/types';

/**
 * Login with email and password
 * Stores token on success
 */
export async function login(credentials: LoginRequest): Promise<LoginResponse> {
    const response = await apiClient.post<LoginResponse>('/auth/login', credentials);
    setToken(response.token);
    return response;
}

/**
 * Register a new user account
 * Stores token on success
 */
export async function register(data: RegisterRequest): Promise<RegisterResponse> {
    const response = await apiClient.post<RegisterResponse>('/auth/register', data);
    setToken(response.token);
    return response;
}

/**
 * Logout current user
 * Clears stored token
 */
export async function logout(): Promise<void> {
    try {
        await apiClient.post('/auth/logout');
    } finally {
        // Always clear token, even if request fails
        clearToken();
    }
}

/**
 * Get current authenticated user
 */
export async function getMe(): Promise<User> {
    return apiClient.get<User>('/auth/me');
}

/**
 * Refresh auth token
 */
export async function refreshToken(): Promise<LoginResponse> {
    const response = await apiClient.post<LoginResponse>('/auth/refresh');
    setToken(response.token);
    return response;
}
