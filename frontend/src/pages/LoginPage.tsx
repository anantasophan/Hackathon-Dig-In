/**
 * LoginPage — entry point for unauthenticated users.
 *
 * Renders the Cognito Hosted UI via the Amplify Authenticator component.
 * On successful sign-in the user is redirected to /overview.  If the
 * user is already authenticated they are redirected immediately without
 * seeing the login form.
 *
 * Requirements: 7.1, 7.3
 */

import React from 'react';
import { Navigate } from 'react-router-dom';
import { Authenticator } from '@aws-amplify/ui-react';
import '@aws-amplify/ui-react/styles.css';
import { Loader2 } from 'lucide-react';
import { useAuth } from '../hooks/useAuth';

/**
 * Full-page login view using the Amplify Authenticator widget.
 *
 * The Authenticator handles username/password sign-in and the Cognito
 * Hosted UI redirect flow.  Once authenticated the component redirects
 * the user to the main dashboard.
 */
const LoginPage: React.FC = () => {
  const { isAuthenticated, isLoading } = useAuth();

  // Wait until auth state is known before deciding to redirect.
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

  // Already signed in — skip login form.
  if (isAuthenticated) {
    return <Navigate to="/overview" replace />;
  }

  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-slate-50 p-8">
      <h1 className="mb-8 text-2xl font-bold text-slate-800 text-center">
        Campaign Insight Generator
      </h1>

      {/*
       * The Authenticator component renders sign-in / sign-up UI using
       * Cognito.  The `loginMechanisms` prop restricts the UI to
       * username-based login only.  The `hideSignUp` prop prevents new
       * self-service registrations (access is managed by admins).
       */}
      <Authenticator
        loginMechanisms={['username']}
        hideSignUp
      >
        {/* This child render prop is called once authentication succeeds.
            We use a Navigate element to push the user to the overview page. */}
        {() => <Navigate to="/overview" replace />}
      </Authenticator>
    </div>
  );
};

export default LoginPage;
