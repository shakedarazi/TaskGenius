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
        // We'll use a modal for unlink confirmation (similar to delete task)
        // For now, keeping confirm but will be replaced with modal
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
            <div className="card mb-4">
                <div className="card-header bg-primary text-white">
                    <h1 className="h3 mb-0">
                        <i className="bi bi-gear-fill me-2"></i>Settings
                    </h1>
                </div>
                <div className="card-body">
                    <section className="settings-section">
                        <div className="d-flex align-items-center mb-4">
                            {/* Telegram Icon SVG */}
                            <svg 
                                width="48" 
                                height="48" 
                                viewBox="0 0 24 24" 
                                fill="none" 
                                xmlns="http://www.w3.org/2000/svg"
                                className="me-3"
                                style={{ flexShrink: 0 }}
                            >
                                <path 
                                    d="M12 0C5.373 0 0 5.373 0 12s5.373 12 12 12 12-5.373 12-12S18.627 0 12 0zm5.894 8.221l-1.97 9.28c-.145.658-.537.818-1.084.508l-3-2.21-1.446 1.394c-.14.18-.357.295-.6.295-.002 0-.003 0-.005 0l.213-3.054 5.56-5.022c.24-.213-.054-.334-.373-.12l-6.87 4.326-2.96-.924c-.64-.203-.658-.64.135-.954l11.566-4.458c.538-.196 1.006.128.832.941z" 
                                    fill="currentColor"
                                />
                            </svg>
                            <div>
                                <h2 className="h4 mb-1">Telegram Integration</h2>
                                <p className="text-muted mb-0">Connect your Telegram account to receive task summaries</p>
                            </div>
                        </div>

                        {error && (
                            <div className="alert alert-danger alert-dismissible fade show" role="alert">
                                {error}
                                <button 
                                    type="button" 
                                    className="btn-close" 
                                    onClick={() => setError(null)} 
                                    aria-label="Close"
                                ></button>
                            </div>
                        )}

                        {loading && !status && (
                            <div className="text-center py-4">
                                <div className="spinner-border text-primary" role="status">
                                    <span className="visually-hidden">Loading...</span>
                                </div>
                            </div>
                        )}

                        {status && (
                            <div className="telegram-status mb-4">
                                <div className="d-flex align-items-center mb-3">
                                    <strong className="me-2">Status:</strong>
                                    {status.linked ? (
                                        <span className="badge bg-success">
                                            <i className="bi bi-check-circle-fill me-1"></i>Linked
                                        </span>
                                    ) : (
                                        <span className="badge bg-secondary">
                                            <i className="bi bi-x-circle me-1"></i>Not linked
                                        </span>
                                    )}
                                </div>

                                {status.linked && status.telegram_username && (
                                    <div className="mb-3">
                                        <strong className="me-2">Telegram Username:</strong>
                                        <span className="text-primary">
                                            <i className="bi bi-at me-1"></i>@{status.telegram_username}
                                        </span>
                                    </div>
                                )}

                                {status.linked && (
                                    <div className="mb-3">
                                        <strong className="me-2">Notifications:</strong>
                                        <span className={status.notifications_enabled ? 'text-success' : 'text-muted'}>
                                            {status.notifications_enabled ? (
                                                <>
                                                    <i className="bi bi-bell-fill me-1"></i>Enabled
                                                </>
                                            ) : (
                                                <>
                                                    <i className="bi bi-bell-slash me-1"></i>Disabled
                                                </>
                                            )}
                                        </span>
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
                                        className="btn btn-primary btn-lg"
                                    >
                                        {loading ? (
                                            <>
                                                <span className="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>
                                                Generating...
                                            </>
                                        ) : (
                                            <>
                                                <i className="bi bi-key-fill me-2"></i>Generate Verification Code
                                            </>
                                        )}
                                    </button>

                                    {linkCode && (
                                        <div className="verification-code-box mt-4 animate-fade-in">
                                            <div className="card border-primary">
                                                <div className="card-header bg-primary text-white">
                                                    <h5 className="mb-0">
                                                        <i className="bi bi-shield-check me-2"></i>Verification Code
                                                    </h5>
                                                </div>
                                                <div className="card-body">
                                                    <p className="mb-3">
                                                        <strong>Send this code to the TASKGENIUS bot on Telegram:</strong>
                                                    </p>
                                                    <div className="code-display bg-light p-3 rounded text-center mb-3" style={{ 
                                                        fontSize: '1.5rem', 
                                                        fontFamily: 'monospace',
                                                        letterSpacing: '0.2em',
                                                        fontWeight: 'bold',
                                                        border: '2px dashed var(--theme-light-blue)'
                                                    }}>
                                                        {linkCode}
                                                    </div>
                                                    {codeCountdown !== null && (
                                                        <div className="text-center mb-3">
                                                            <span className="badge bg-warning text-dark">
                                                                <i className="bi bi-clock me-1"></i>
                                                                Expires in: {formatCountdown(codeCountdown)}
                                                            </span>
                                                        </div>
                                                    )}
                                                    <div className="alert alert-info mb-0">
                                                        <strong><i className="bi bi-info-circle me-2"></i>Instructions:</strong>
                                                        <ol className="mb-0 mt-2">
                                                            <li>Open your Telegram app</li>
                                                            <li>Search for <strong>@TASKGENIUS</strong> bot</li>
                                                            <li>Start a conversation with the bot</li>
                                                            <li>Send the code above as a message</li>
                                                        </ol>
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                    )}
                                </div>
                            ) : (
                                <div className="linked-section">
                                    <button
                                        onClick={handleUnlink}
                                        disabled={loading}
                                        className="btn btn-danger mb-3"
                                    >
                                        {loading ? (
                                            <>
                                                <span className="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>
                                                Unlinking...
                                            </>
                                        ) : (
                                            <>
                                                <i className="bi bi-unlink me-2"></i>Unlink Telegram Account
                                            </>
                                        )}
                                    </button>

                                    <div className="notifications-toggle card">
                                        <div className="card-body">
                                            <div className="form-check form-switch">
                                                <input
                                                    className="form-check-input"
                                                    type="checkbox"
                                                    role="switch"
                                                    id="notificationsToggle"
                                                    checked={status.notifications_enabled}
                                                    onChange={(e) =>
                                                        handleToggleNotifications(e.target.checked)
                                                    }
                                                    disabled={loading}
                                                />
                                                <label className="form-check-label" htmlFor="notificationsToggle">
                                                    <strong>Enable automatic weekly summaries</strong>
                                                </label>
                                            </div>
                                            <p className="text-muted small mt-2 mb-0">
                                                <i className="bi bi-info-circle me-1"></i>
                                                When enabled, you'll receive a weekly task summary every 7 days automatically. 
                                                You can always send a summary manually using the "Send Summary" button on the Tasks page.
                                            </p>
                                        </div>
                                    </div>
                                </div>
                            )}
                        </div>
                    </section>
                </div>
            </div>
        </div>
    );
}
