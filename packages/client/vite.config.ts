import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// https://vite.dev/config/
export default defineConfig({
    plugins: [react()],
    resolve: {
        alias: {
            '@': path.resolve(__dirname, './src'),
            '@/api': path.resolve(__dirname, './src/api'),
            '@/types': path.resolve(__dirname, './src/types'),
            '@/pages': path.resolve(__dirname, './src/pages'),
            '@/components': path.resolve(__dirname, './src/components'),
            '@/routes': path.resolve(__dirname, './src/routes'),
        },
    },
    server: {
        port: 5173,
        proxy: {
            // Proxy API requests to core-api during development
            '/api': {
                target: process.env.VITE_CORE_API_BASE_URL || 'http://localhost:8000',
                changeOrigin: true,
                secure: false,
            },
        },
    },
    build: {
        outDir: 'dist',
        sourcemap: true,
    },
});
