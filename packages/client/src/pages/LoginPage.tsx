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

import { useState, type FormEvent } from "react";
import { useNavigate, Link } from "react-router-dom";
import { authApi } from "@/api";

export function LoginPage() {
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      await authApi.login({ username, password });
      navigate("/tasks");
    } catch (err: any) {
      console.log("[login] error:", err);
      setError(err?.message || err?.detail || "Login failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-page login-page">
      <div className="container">
        <div className="row justify-content-center align-items-center min-vh-100 py-5">
          <div className="col-12 col-md-8 col-lg-6 col-xl-5">
            <div className="card shadow-lg border-0 animate-fade-in">
              <div className="card-header bg-primary text-white text-center py-4" style={{ borderRadius: '12px 12px 0 0' }}>
                <div className="mb-3">
                  <i className="bi bi-box-arrow-in-right" style={{ fontSize: '3rem' }}></i>
                </div>
                <h1 className="h3 mb-0 fw-bold">Login to TASKGENIUS</h1>
                <p className="mb-0 mt-2 opacity-75">Welcome back! Please sign in to continue</p>
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
                      disabled={loading}
                      placeholder="Enter your username"
                    />
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
                      disabled={loading}
                      placeholder="Enter your password"
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
                        Logging in...
                      </>
                    ) : (
                      <>
                        <i className="bi bi-box-arrow-in-right me-2"></i>Login
                      </>
                    )}
                  </button>
                </form>

                <div className="text-center mt-4">
                  <p className="text-muted mb-0">
                    Don't have an account?{' '}
                    <Link to="/register" className="text-primary fw-semibold text-decoration-none">
                      <i className="bi bi-person-plus me-1"></i>Register
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
