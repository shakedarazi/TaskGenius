/**
 * ProtectedRoute
 * 
 * Purpose: Guard routes that require authentication
 * 
 * Responsibilities:
 * - Check if user is authenticated
 * - Redirect to login if not authenticated
 * - Render children if authenticated
 * - Optionally check for specific roles/permissions
 */

import { Navigate, useLocation } from 'react-router-dom';
import { isAuthenticated } from '@/api/client';
import type { ReactNode } from 'react';

interface ProtectedRouteProps {
    children: ReactNode;
    /** Optional: redirect path when not authenticated */
    redirectTo?: string;
}

export function ProtectedRoute({
    children,
    redirectTo = '/login',
}: ProtectedRouteProps) {
    const location = useLocation();

    if (!isAuthenticated()) {
        // Redirect to login, preserving the intended destination
        return <Navigate to={redirectTo} state={{ from: location }} replace />;
    }

    return <>{children}</>;
}
