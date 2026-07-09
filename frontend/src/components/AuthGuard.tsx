/**
 * AuthGuard component — route protection wrapper.
 *
 * Renders children only when the current user is authenticated.
 * Redirects unauthenticated visitors to /login and shows a loading
 * spinner while the auth state is being resolved.
 *
 * Requirements: 7.1, 7.2, 7.3
 */

import React from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';

interface AuthGuardProps {
  children: React.ReactNode;
}

/**
 * Wrap any route element with `<AuthGuard>` to require authentication.
 *
 * @example
 * <Route path="/overview" element={<AuthGuard><OverviewPage /></AuthGuard>} />
 */
const AuthGuard: React.FC<AuthGuardProps> = ({ children }) => {
  const { isAuthenticated, isLoading } = useAuth();

  // While Amplify is resolving the session, show a neutral spinner so
  // the user does not see an unwanted redirect flash.
  if (isLoading) {
    return (
      <div
        role="status"
        aria-label="Loading"
        style={{
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          minHeight: '100vh',
        }}
      >
        <div
          style={{
            width: 40,
            height: 40,
            border: '4px solid #e0e0e0',
            borderTopColor: '#1976d2',
            borderRadius: '50%',
            animation: 'spin 0.8s linear infinite',
          }}
        />
        <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return <>{children}</>;
};

export default AuthGuard;
