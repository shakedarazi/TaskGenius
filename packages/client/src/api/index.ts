/**
 * API Layer - Barrel Export
 * 
 * Central export point for all API modules.
 * Components should import from '@/api' rather than individual files.
 */

export { apiClient } from './client';
export * as authApi from './auth';
export * as tasksApi from './tasks';
export * as chatApi from './chat';
