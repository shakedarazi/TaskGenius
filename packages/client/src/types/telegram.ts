/**
 * Telegram Types
 * 
 * DTOs for Telegram integration operations.
 */

/**
 * Telegram linking status (matches backend TelegramStatusResponse)
 */
export interface TelegramStatus {
    linked: boolean;
    telegram_username: string | null;
    notifications_enabled: boolean;
}
