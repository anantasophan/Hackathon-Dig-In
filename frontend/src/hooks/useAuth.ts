/**
 * Custom hook for Cognito authentication state management.
 *
 * Provides the current user, their role extracted from JWT custom
 * claims, loading state, and a sign-out helper.  Also enforces the
 * 8-hour session expiry policy by polling every minute.
 *
 * Requirements: 7.1, 7.2, 7.3
 */

import { useState, useEffect, useCallback } from 'react';
import {
  fetchAuthSession,
  signOut as amplifySignOut,
  getCurrentUser,
} from 'aws-amplify/auth';

// ── Types ──────────────────────────────────────────────────────────────────

export type UserRole = 'divisi_bisnis' | 'divisi_data' | null;

export interface AuthUser {
  username: string;
  userId: string;
}

export interface AuthState {
  user: AuthUser | null;
  role: UserRole;
  isAuthenticated: boolean;
  isLoading: boolean;
  signOut: () => Promise<void>;
}

// ── Constants ──────────────────────────────────────────────────────────────

/** 8 hours in seconds — matches Requirement 7.2 */
const SESSION_DURATION_SECONDS = 28_800;

/** Interval between expiry checks (1 minute in ms) */
const EXPIRY_CHECK_INTERVAL_MS = 60_000;

// ── Helpers ────────────────────────────────────────────────────────────────

/**
 * Extract the application role from Cognito JWT claims.
 *
 * The Cognito user pool is configured with a custom attribute
 * `custom:role` whose value is either "divisi_bisnis" or "divisi_data".
 * Any other value (including absent) returns null.
 */
function extractRole(claims: Record<string, unknown>): UserRole {
  const raw = claims['custom:role'];
  if (raw === 'divisi_bisnis' || raw === 'divisi_data') {
    return raw;
  }
  return null;
}

/**
 * Determine whether the current session has exceeded the 8-hour limit.
 *
 * `auth_time` in the JWT is a Unix epoch timestamp (seconds) recording
 * when the user authenticated.  Returns true when the session is expired.
 */
function isSessionExpired(claims: Record<string, unknown>): boolean {
  const authTime = claims['auth_time'];
  if (typeof authTime !== 'number') {
    // Cannot determine; treat as not expired to avoid false logouts.
    return false;
  }
  const nowSeconds = Date.now() / 1000;
  return nowSeconds - authTime > SESSION_DURATION_SECONDS;
}

// ── Local dev bypass ──────────────────────────────────────────────────────

/** True when running against the local FastAPI dev server (no Cognito). */
const IS_LOCAL_DEV =
  (process.env['REACT_APP_API_GATEWAY_URL'] ?? '').includes('localhost');

// ── Hook ───────────────────────────────────────────────────────────────────

/**
 * Hook that surfaces authentication state and enforces session expiry.
 *
 * In local-dev mode (REACT_APP_API_GATEWAY_URL points to localhost) the hook
 * immediately returns a mock authenticated user so Cognito is never called.
 *
 * @returns {AuthState} Current auth state plus a sign-out function.
 */
export function useAuth(): AuthState {
  const [user, setUser] = useState<AuthUser | null>(
    IS_LOCAL_DEV ? { username: 'local-dev', userId: 'local-dev' } : null,
  );
  const [role, setRole] = useState<UserRole>(
    IS_LOCAL_DEV ? 'divisi_bisnis' : null,
  );
  const [isAuthenticated, setIsAuthenticated] = useState(IS_LOCAL_DEV);
  const [isLoading, setIsLoading] = useState(!IS_LOCAL_DEV);

  // ── Sign-out ─────────────────────────────────────────────────────────────

  const signOut = useCallback(async (): Promise<void> => {
    try {
      await amplifySignOut();
    } finally {
      setUser(null);
      setRole(null);
      setIsAuthenticated(false);
    }
  }, []);

  // ── Load / refresh auth state ─────────────────────────────────────────────

  const loadAuthState = useCallback(async (): Promise<void> => {
    // In local dev mode auth is already set via useState defaults — skip Cognito.
    if (IS_LOCAL_DEV) return;

    try {
      // getCurrentUser throws if there is no active session.
      const currentUser = await getCurrentUser();

      const session = await fetchAuthSession();
      const idToken = session.tokens?.idToken;

      if (idToken === undefined) {
        // Tokens absent — treat as unauthenticated.
        setUser(null);
        setRole(null);
        setIsAuthenticated(false);
        return;
      }

      const claims = idToken.payload as Record<string, unknown>;

      // Enforce session expiry (Requirement 7.2).
      if (isSessionExpired(claims)) {
        await signOut();
        return;
      }

      setUser({
        username: currentUser.username,
        userId: currentUser.userId,
      });
      setRole(extractRole(claims));
      setIsAuthenticated(true);
    } catch {
      // No active session or tokens expired.
      setUser(null);
      setRole(null);
      setIsAuthenticated(false);
    } finally {
      setIsLoading(false);
    }
  }, [signOut]);

  // ── Bootstrap + expiry polling ────────────────────────────────────────────

  useEffect(() => {
    // Initial load.
    loadAuthState();

    // Poll every minute to catch session expiry mid-session.
    const intervalId = setInterval(() => {
      loadAuthState();
    }, EXPIRY_CHECK_INTERVAL_MS);

    return () => {
      clearInterval(intervalId);
    };
  }, [loadAuthState]);

  return { user, role, isAuthenticated, isLoading, signOut };
}
