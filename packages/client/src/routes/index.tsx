/**
 * AppRoutes
 * 
 * Main routing configuration for the application.
 */

import { Routes, Route, Navigate } from 'react-router-dom';
import { LoginPage } from '@/pages/LoginPage';
import { RegisterPage } from '@/pages/RegisterPage';
import { TasksPage } from '@/pages/TasksPage';
import { ProtectedRoute } from './ProtectedRoute';

export function AppRoutes() {
    return (
        <Routes>
            {/* Public routes */}
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />

            {/* Protected routes */}
            <Route
                path="/tasks"
                element={
                    <ProtectedRoute>
                        <TasksPage />
                    </ProtectedRoute>
                }
            />

            {/* Default redirect */}
            <Route path="/" element={<Navigate to="/tasks" replace />} />

            {/* 404 fallback */}
            <Route path="*" element={<Navigate to="/tasks" replace />} />
        </Routes>
    );
}
