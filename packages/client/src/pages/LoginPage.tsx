/**
 * LoginPage
 * 
 * Purpose: User authentication via email/password
 * 
 * Responsibilities:
 * - Display login form (email, password)
 * - Validate input before submission
 * - Call authApi.login() on submit
 * - Handle errors (display to user)
 * - Redirect to TasksPage on success
 * - Link to RegisterPage
 * 
 * API: authApi.login()
 * Route: /login
 */

import { useState, type FormEvent } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { authApi } from '@/api';

export function LoginPage() {
    const navigate = useNavigate();
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState<string | null>(null);
    const [loading, setLoading] = useState(false);

    const handleSubmit = async (e: FormEvent) => {
        e.preventDefault();
        setError(null);
        setLoading(true);

        try {
            await authApi.login({ username, password });
            navigate('/tasks');
        }  catch (err: any) {
            console.log('[register] error:', err);
            setError(err?.message || err?.detail || 'Registration failed');
          } finally {
            setLoading(false);
        }
    };

    return (
        <div className="login-page">
            <h1>Login to TASKGENIUS</h1>

            <form onSubmit={handleSubmit}>
                {error && <div className="error">{error}</div>}

                <div className="form-group">
                    <label htmlFor="username">Username</label>
                    <input
                        id="username"
                        type="text"
                        value={username}
                        onChange={(e) => setUsername(e.target.value)}
                        required
                        disabled={loading}
                    />
                </div>

                <div className="form-group">
                    <label htmlFor="password">Password</label>
                    <input
                        id="password"
                        type="password"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        required
                        disabled={loading}
                    />
                </div>

                <button type="submit" disabled={loading}>
                    {loading ? 'Logging in...' : 'Login'}
                </button>
            </form>

            <p>
                Don't have an account? <Link to="/register">Register</Link>
            </p>
        </div>
    );
}
