import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import { AuthProvider } from './hooks/useAuth';
import { SystemsProvider } from './hooks/useSystems';
import { ProtectedRoute } from './components/ProtectedRoute';
import { Layout } from './components/Layout';
import { Login } from './pages/Login';
import { Dashboard } from './pages/Dashboard';
import { Systems } from './pages/Systems';
import { Alerts } from './pages/Alerts';
import { Reports } from './pages/Reports';
import { Trends } from './pages/Trends';
import { SearchResults } from './pages/SearchResults';

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route
            element={
              <ProtectedRoute>
                <SystemsProvider>
                  <Layout />
                </SystemsProvider>
              </ProtectedRoute>
            }
          >
            <Route path="/" element={<Dashboard />} />
            <Route path="/systems" element={<Systems />} />
            <Route path="/alerts" element={<Alerts />} />
            <Route path="/reports" element={<Reports />} />
            <Route path="/trends" element={<Trends />} />
            <Route path="/trends/:systemId" element={<Trends />} />
            <Route path="/search" element={<SearchResults />} />
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}
