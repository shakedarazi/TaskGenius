/**
 * Telegram API
 * 
 * API functions for Telegram integration:
 * - Link/unlink Telegram account
 * - Get linking status
 * - Toggle notifications
 */

import { apiClient } from './client';
import type { TelegramStatus } from '@/types';

/**
 * Get current Telegram linking status for the authenticated user.
 */
export async function getTelegramStatus(): Promise<TelegramStatus> {
    return apiClient.get<TelegramStatus>('/telegram/status');
}

/**
 * Start Telegram linking flow.
 * Returns a verification code that the user must send to the Telegram bot.
 */
export async function startTelegramLink(): Promise<{ code: string; expires_in_seconds: number }> {
    return apiClient.post<{ code: string; expires_in_seconds: number }>('/telegram/link/start');
}

/**
 * Unlink Telegram account from the authenticated user.
 */
export async function unlinkTelegram(): Promise<void> {
    await apiClient.post('/telegram/unlink');
}

/**
 * Enable or disable Telegram notifications for the authenticated user.
 */
export async function setTelegramNotifications(enabled: boolean): Promise<TelegramStatus> {
    return apiClient.patch<TelegramStatus>('/telegram/notifications', { enabled });
}

/**
 * Send weekly summary to Telegram for the authenticated user (on-demand).
 * Requires that the user has already linked their Telegram account.
 */
export async function sendWeeklySummary(): Promise<{ sent: boolean; message?: string }> {
    return apiClient.post<{ sent: boolean; message?: string }>('/telegram/summary/send');
}
