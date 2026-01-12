/**
 * Auth Types
 * 
 * DTOs for authentication operations.
 */

/**
 * User entity (matches backend UserResponse)
 */
export interface User {
    id: string;
    username: string;
    created_at: string;
}

/**
 * Login request payload (matches backend UserLoginRequest)
 */
export interface LoginRequest {
    username: string;
    password: string;
}

/**
 * Login response (matches backend TokenResponse)
 */
export interface LoginResponse {
    access_token: string;
    token_type: string;
}

/**
 * Register request payload (matches backend UserRegisterRequest)
 */
export interface RegisterRequest {
    username: string;
    password: string;
}

/**
 * Register response (matches backend MessageResponse)
 */
export interface RegisterResponse {
    message: string;
}
