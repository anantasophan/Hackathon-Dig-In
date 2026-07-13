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
import { Loader2 } from 'lucide-react';
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
        className="flex justify-center items-center min-h-screen"
      >
        <Loader2 className="w-10 h-10 animate-spin text-[#005E6A]" />
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return <>{children}</>;
};

export default AuthGuard;
