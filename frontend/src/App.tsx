import React, { ReactNode } from 'react';
import { Navigate, Route, Routes } from 'react-router-dom';
import { useAuth } from './auth/AuthContext';
import Layout from './components/Layout';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import Verify from './pages/Verify';
import VerificationDetail from './pages/VerificationDetail';
import VerificationsList from './pages/VerificationsList';
import Blacklist from './pages/Blacklist';
import AuditLogs from './pages/AuditLogs';

function Protected({ children }: { children: ReactNode }) {
  const { token } = useAuth();
  return <>{token ? children : <Navigate to="/login" replace />}</>;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route
        path="/"
        element={
          <Protected>
            <Layout />
          </Protected>
        }
      >
        <Route index element={<Dashboard />} />
        <Route path="verify" element={<Verify />} />
        <Route path="verification/:id" element={<VerificationDetail />} />
        <Route path="verifications" element={<VerificationsList />} />
        <Route path="blacklist" element={<Blacklist />} />
        <Route path="audit" element={<AuditLogs />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
