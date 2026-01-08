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
    const [name, setName] = useState('');
    const [email, setEmail] = useState('');
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
            await authApi.register({ name, email, password });
            navigate('/tasks');
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Registration failed');
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
                    <label htmlFor="name">Name</label>
                    <input
                        id="name"
                        type="text"
                        value={name}
                        onChange={(e) => setName(e.target.value)}
                        required
                        disabled={loading}
                    />
                </div>

                <div className="form-group">
                    <label htmlFor="email">Email</label>
                    <input
                        id="email"
                        type="email"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
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
