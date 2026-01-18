/**
 * Layout
 * 
 * Purpose: Application shell with navigation and common UI
 * 
 * Responsibilities:
 * - Render header with logo and navigation
 * - Show user info and logout button when authenticated
 * - Wrap page content in consistent container
 * - Render footer
 */

import type { ReactNode } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { isAuthenticated, clearToken } from '@/api/client';
import { ChatWidget } from '@/components/ChatWidget';

interface LayoutProps {
    children: ReactNode;
}

export function Layout({ children }: LayoutProps) {
    const navigate = useNavigate();
    const authenticated = isAuthenticated();

    const handleLogout = () => {
        clearToken();
        navigate('/login');
    };

    return (
        <div className="layout d-flex flex-column min-vh-100">
            <header className="layout-header">
                <nav className="navbar navbar-expand-lg navbar-dark bg-primary">
                    <div className="container">
                        <Link to="/" className="navbar-brand fw-bold">
                            TASKGENIUS
                        </Link>
                        <button 
                            className="navbar-toggler" 
                            type="button" 
                            data-bs-toggle="collapse" 
                            data-bs-target="#navbarNav"
                            aria-controls="navbarNav" 
                            aria-expanded="false" 
                            aria-label="Toggle navigation"
                        >
                            <span className="navbar-toggler-icon"></span>
                        </button>
                        <div className="collapse navbar-collapse" id="navbarNav">
                            <nav className="navbar-nav ms-auto">
                                {authenticated ? (
                                    <>
                                        <Link to="/tasks" className="nav-link">
                                            <i className="bi bi-list-check me-1"></i>Tasks
                                        </Link>
                                        <Link to="/settings" className="nav-link">
                                            <i className="bi bi-gear me-1"></i>Settings
                                        </Link>
                                        <button 
                                            onClick={handleLogout} 
                                            className="btn btn-outline-light btn-sm ms-2"
                                        >
                                            <i className="bi bi-box-arrow-right me-1"></i>Logout
                                        </button>
                                    </>
                                ) : (
                                    <>
                                        <Link to="/login" className="nav-link">
                                            <i className="bi bi-box-arrow-in-right me-1"></i>Login
                                        </Link>
                                        <Link to="/register" className="nav-link">
                                            <i className="bi bi-person-plus me-1"></i>Register
                                        </Link>
                                    </>
                                )}
                            </nav>
                        </div>
                    </div>
                </nav>
            </header>

            <main className="layout-main flex-grow-1 py-4">
                <div className="container">{children}</div>
            </main>

            <footer className="layout-footer bg-light border-top mt-auto py-3">
                <div className="container text-center text-muted">
                    <p className="mb-0">&copy; {new Date().getFullYear()} TASKGENIUS</p>
                </div>
            </footer>

            {authenticated && <ChatWidget />}
        </div>
    );
}
