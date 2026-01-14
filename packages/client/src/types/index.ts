/**
 * Types Layer - Barrel Export
 * 
 * Shared TypeScript DTOs matching core-api responses.
 * Keep in sync with backend schemas.
 */

export * from './auth';
export * from './task';
export * from './chat';
export * from './telegram';

/**
 * Generic API error response
 */
export interface ApiError {
    code: string;
    message: string;
    details?: Record<string, unknown>;
}

/**
 * Paginated response wrapper
 */
export interface PaginatedResponse<T> {
    items: T[];
    total: number;
    page: number;
    limit: number;
    hasMore: boolean;
}
