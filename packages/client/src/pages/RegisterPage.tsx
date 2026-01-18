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
        <div className="auth-page register-page">
            <div className="container">
                <div className="row justify-content-center align-items-center min-vh-100 py-5">
                    <div className="col-12 col-md-8 col-lg-6 col-xl-5">
                        <div className="card shadow-lg border-0 animate-fade-in">
                            <div className="card-header bg-primary text-white text-center py-4" style={{ borderRadius: '12px 12px 0 0' }}>
                                <div className="mb-3">
                                    <i className="bi bi-person-plus-fill" style={{ fontSize: '3rem' }}></i>
                                </div>
                                <h1 className="h3 mb-0 fw-bold">Create Account</h1>
                                <p className="mb-0 mt-2 opacity-75">Join TASKGENIUS and start managing your tasks</p>
                            </div>
                            <div className="card-body p-4 p-md-5">
                                <form onSubmit={handleSubmit}>
                                    {error && (
                                        <div className="alert alert-danger alert-dismissible fade show" role="alert">
                                            <i className="bi bi-exclamation-triangle-fill me-2"></i>
                                            {error}
                                            <button 
                                                type="button" 
                                                className="btn-close" 
                                                onClick={() => setError(null)} 
                                                aria-label="Close"
                                            ></button>
                                        </div>
                                    )}

                                    <div className="mb-4">
                                        <label htmlFor="username" className="form-label fw-semibold">
                                            <i className="bi bi-person-fill me-2 text-primary"></i>Username
                                        </label>
                                        <input
                                            id="username"
                                            type="text"
                                            className="form-control form-control-lg"
                                            value={username}
                                            onChange={(e) => setUsername(e.target.value)}
                                            required
                                            minLength={3}
                                            maxLength={50}
                                            pattern="[a-zA-Z0-9_]+"
                                            title="Username must be 3-50 characters, alphanumeric with underscores only"
                                            disabled={loading}
                                            placeholder="Choose a username (3-50 characters)"
                                        />
                                        <small className="text-muted">Alphanumeric characters and underscores only</small>
                                    </div>

                                    <div className="mb-4">
                                        <label htmlFor="password" className="form-label fw-semibold">
                                            <i className="bi bi-lock-fill me-2 text-primary"></i>Password
                                        </label>
                                        <input
                                            id="password"
                                            type="password"
                                            className="form-control form-control-lg"
                                            value={password}
                                            onChange={(e) => setPassword(e.target.value)}
                                            required
                                            minLength={8}
                                            disabled={loading}
                                            placeholder="Enter your password (min. 8 characters)"
                                        />
                                        <small className="text-muted">Must be at least 8 characters long</small>
                                    </div>

                                    <div className="mb-4">
                                        <label htmlFor="confirmPassword" className="form-label fw-semibold">
                                            <i className="bi bi-lock-fill me-2 text-primary"></i>Confirm Password
                                        </label>
                                        <input
                                            id="confirmPassword"
                                            type="password"
                                            className="form-control form-control-lg"
                                            value={confirmPassword}
                                            onChange={(e) => setConfirmPassword(e.target.value)}
                                            required
                                            disabled={loading}
                                            placeholder="Confirm your password"
                                        />
                                    </div>

                                    <button 
                                        type="submit" 
                                        className="btn btn-primary btn-lg w-100 mb-3"
                                        disabled={loading}
                                    >
                                        {loading ? (
                                            <>
                                                <span className="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>
                                                Creating account...
                                            </>
                                        ) : (
                                            <>
                                                <i className="bi bi-person-plus me-2"></i>Register
                                            </>
                                        )}
                                    </button>
                                </form>

                                <div className="text-center mt-4">
                                    <p className="text-muted mb-0">
                                        Already have an account?{' '}
                                        <Link to="/login" className="text-primary fw-semibold text-decoration-none">
                                            <i className="bi bi-box-arrow-in-right me-1"></i>Login
                                        </Link>
                                    </p>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
