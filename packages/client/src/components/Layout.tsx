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
        <div className="layout">
            <header className="layout-header">
                <div className="container">
                    <Link to="/" className="logo">
                        TASKGENIUS
                    </Link>

                    <nav className="nav">
                        {authenticated ? (
                            <>
                                <Link to="/tasks">Tasks</Link>
                                <button onClick={handleLogout} className="logout-btn">
                                    Logout
                                </button>
                            </>
                        ) : (
                            <>
                                <Link to="/login">Login</Link>
                                <Link to="/register">Register</Link>
                            </>
                        )}
                    </nav>
                </div>
            </header>

            <main className="layout-main">
                <div className="container">{children}</div>
            </main>

            <footer className="layout-footer">
                <div className="container">
                    <p>&copy; {new Date().getFullYear()} TASKGENIUS</p>
                </div>
            </footer>
        </div>
    );
}
