/**
 * SettingsPage
 * 
 * Purpose: Telegram integration settings
 * 
 * Features:
 * - View current Telegram linking status
 * - Generate verification code to link Telegram account
 * - Unlink Telegram account
 * - Toggle Telegram notifications
 */

import { useState, useEffect, useCallback } from 'react';
import { telegramApi } from '@/api';
import type { TelegramStatus } from '@/types';

export function SettingsPage() {
    const [status, setStatus] = useState<TelegramStatus | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [linkCode, setLinkCode] = useState<string | null>(null);
    const [codeExpiresIn, setCodeExpiresIn] = useState<number | null>(null);
    const [codeCountdown, setCodeCountdown] = useState<number | null>(null);

    // Load status on mount
    useEffect(() => {
        loadStatus();
    }, []);

    // Countdown timer for code expiration
    useEffect(() => {
        if (codeExpiresIn === null) {
            setCodeCountdown(null);
            return;
        }

        const interval = setInterval(() => {
            const remaining = Math.max(0, codeExpiresIn - Math.floor(Date.now() / 1000));
            setCodeCountdown(remaining);
            if (remaining === 0) {
                setCodeExpiresIn(null);
                setLinkCode(null);
            }
        }, 1000);

        return () => clearInterval(interval);
    }, [codeExpiresIn]);

    const loadStatus = useCallback(async () => {
        try {
            setLoading(true);
            setError(null);
            const data = await telegramApi.getTelegramStatus();
            setStatus(data);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to load Telegram status');
        } finally {
            setLoading(false);
        }
    }, []);

    const handleGenerateCode = useCallback(async () => {
        try {
            setLoading(true);
            setError(null);
            const response = await telegramApi.startTelegramLink();
            setLinkCode(response.code);
            const expiresAt = Math.floor(Date.now() / 1000) + response.expires_in_seconds;
            setCodeExpiresIn(expiresAt);
            setCodeCountdown(response.expires_in_seconds);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to generate verification code');
        } finally {
            setLoading(false);
        }
    }, []);

    const handleUnlink = useCallback(async () => {
        if (!confirm('Are you sure you want to unlink your Telegram account?')) {
            return;
        }

        try {
            setLoading(true);
            setError(null);
            await telegramApi.unlinkTelegram();
            await loadStatus();
            setLinkCode(null);
            setCodeExpiresIn(null);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to unlink Telegram account');
        } finally {
            setLoading(false);
        }
    }, [loadStatus]);

    const handleToggleNotifications = useCallback(async (enabled: boolean) => {
        try {
            setLoading(true);
            setError(null);
            const updated = await telegramApi.setTelegramNotifications(enabled);
            setStatus(updated);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to update notification settings');
        } finally {
            setLoading(false);
        }
    }, []);

    const formatCountdown = (seconds: number): string => {
        const mins = Math.floor(seconds / 60);
        const secs = seconds % 60;
        return `${mins}:${secs.toString().padStart(2, '0')}`;
    };

    return (
        <div className="settings-page">
            <h1>Settings</h1>

            <section className="settings-section">
                <h2>Telegram Integration</h2>

                {error && (
                    <div className="error-message" role="alert">
                        {error}
                    </div>
                )}

                {loading && !status && <p>Loading...</p>}

                {status && (
                    <div className="telegram-status">
                        <div className="status-item">
                            <strong>Status:</strong>{' '}
                            {status.linked ? (
                                <span className="status-linked">✓ Linked</span>
                            ) : (
                                <span className="status-unlinked">Not linked</span>
                            )}
                        </div>

                        {status.linked && status.telegram_username && (
                            <div className="status-item">
                                <strong>Telegram Username:</strong> @{status.telegram_username}
                            </div>
                        )}

                        {status.linked && (
                            <div className="status-item">
                                <strong>Notifications:</strong>{' '}
                                {status.notifications_enabled ? 'Enabled' : 'Disabled'}
                            </div>
                        )}
                    </div>
                )}

                <div className="settings-actions">
                    {!status?.linked ? (
                        <div className="link-section">
                            <button
                                onClick={handleGenerateCode}
                                disabled={loading}
                                className="btn btn-primary"
                            >
                                Generate Verification Code
                            </button>

                            {linkCode && (
                                <div className="verification-code-box">
                                    <p>
                                        <strong>Send this code to the Telegram bot:</strong>
                                    </p>
                                    <div className="code-display">{linkCode}</div>
                                    {codeCountdown !== null && (
                                        <p className="code-expiry">
                                            Expires in: {formatCountdown(codeCountdown)}
                                        </p>
                                    )}
                                    <p className="code-instructions">
                                        1. Open your Telegram app
                                        <br />
                                        2. Find the TASKGENIUS bot
                                        <br />
                                        3. Send the code above as a message
                                    </p>
                                </div>
                            )}
                        </div>
                    ) : (
                        <div className="linked-section">
                            <button
                                onClick={handleUnlink}
                                disabled={loading}
                                className="btn btn-danger"
                            >
                                Unlink Telegram Account
                            </button>

                            <div className="notifications-toggle">
                                <label>
                                    <input
                                        type="checkbox"
                                        checked={status.notifications_enabled}
                                        onChange={(e) =>
                                            handleToggleNotifications(e.target.checked)
                                        }
                                        disabled={loading}
                                    />
                                    <span>Enable Telegram notifications</span>
                                </label>
                            </div>
                        </div>
                    )}
                </div>
            </section>
        </div>
    );
}
