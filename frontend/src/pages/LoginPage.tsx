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

  // Already signed in — skip login form.
  if (isAuthenticated) {
    return <Navigate to="/overview" replace />;
  }

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        minHeight: '100vh',
        backgroundColor: '#f5f5f5',
        padding: '2rem',
      }}
    >
      <h1
        style={{
          marginBottom: '2rem',
          fontSize: '1.75rem',
          fontWeight: 700,
          color: '#1a1a2e',
          textAlign: 'center',
        }}
      >
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
