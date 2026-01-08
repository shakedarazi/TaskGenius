/**
 * Auth Types
 * 
 * DTOs for authentication operations.
 */

/**
 * User entity
 */
export interface User {
    id: string;
    email: string;
    name: string;
    createdAt: string;
    updatedAt: string;
}

/**
 * Login request payload
 */
export interface LoginRequest {
    email: string;
    password: string;
}

/**
 * Login response with token
 */
export interface LoginResponse {
    user: User;
    token: string;
    expiresAt: string;
}

/**
 * Register request payload
 */
export interface RegisterRequest {
    email: string;
    password: string;
    name: string;
}

/**
 * Register response (same as login)
 */
export type RegisterResponse = LoginResponse;
