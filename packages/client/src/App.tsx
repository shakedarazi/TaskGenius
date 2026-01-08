import { Routes, Route } from 'react-router-dom';
import { AppRoutes } from '@/routes';
import { Layout } from '@/components/Layout';

/**
 * Root application component.
 * Sets up routing and global layout.
 */
function App() {
    return (
        <Layout>
            <AppRoutes />
        </Layout>
    );
}

export default App;
