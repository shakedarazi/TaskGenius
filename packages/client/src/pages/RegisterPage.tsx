/**
 * RegisterPage
 * 
 * Purpose: New user registration
 * 
 * Responsibilities:
 * - Display registration form (name, email, password, confirm password)
 * - Validate input (password match, email format)
 * - Call authApi.register() on submit
 * - Handle errors (display to user)
 * - Redirect to TasksPage on success
 * - Link to LoginPage
 * 
 * API: authApi.register()
 * Route: /register
 */

import { useState, type FormEvent } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { authApi } from '@/api';

export function RegisterPage() {
    const navigate = useNavigate();
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [confirmPassword, setConfirmPassword] = useState('');
    const [error, setError] = useState<string | null>(null);
    const [loading, setLoading] = useState(false);

    const handleSubmit = async (e: FormEvent) => {
        e.preventDefault();
        setError(null);

        if (password !== confirmPassword) {
            setError('Passwords do not match');
            return;
        }

        setLoading(true);

        try {
            // Step 1: Register the user (backend returns message only, no token)
            await authApi.register({ username, password });
            
            // Step 2: Automatically login with the same credentials to get token
            await authApi.login({ username, password });
            
            // Step 3: Navigate only after token is stored
            navigate('/tasks');
        }  catch (err: any) {
            console.log('[register] error:', err);
            setError(err?.message || err?.detail || 'Registration failed');
          } finally {
            setLoading(false);
        }
    };

    return (
        <div className="register-page">
            <h1>Create Account</h1>

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
                        minLength={3}
                        maxLength={50}
                        pattern="[a-zA-Z0-9_]+"
                        title="Username must be 3-50 characters, alphanumeric with underscores only"
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
                        minLength={8}
                        disabled={loading}
                    />
                </div>

                <div className="form-group">
                    <label htmlFor="confirmPassword">Confirm Password</label>
                    <input
                        id="confirmPassword"
                        type="password"
                        value={confirmPassword}
                        onChange={(e) => setConfirmPassword(e.target.value)}
                        required
                        disabled={loading}
                    />
                </div>

                <button type="submit" disabled={loading}>
                    {loading ? 'Creating account...' : 'Register'}
                </button>
            </form>

            <p>
                Already have an account? <Link to="/login">Login</Link>
            </p>
        </div>
    );
}
