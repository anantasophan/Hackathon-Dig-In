/**
 * retryService.ts — Exponential backoff retry utility.
 *
 * Provides a `withRetry` wrapper that transparently retries transient
 * failures (HTTP 408 timeout and 503 service unavailable) with exponential
 * backoff delays (1 s → 2 s → 4 s), up to a configurable maximum number of
 * attempts.
 *
 * Non-retryable errors (400 bad request, 401 unauthorised, 429 rate-limited,
 * 500 internal server error) are rethrown immediately without consuming any
 * retry budget.
 *
 * Requirements: 8.4, 8.5
 */

import { ApiTimeoutError, ApiServiceUnavailableError } from './api';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

/**
 * Configuration options for `withRetry`.
 */
export interface RetryOptions {
  /** Maximum number of retry attempts (not counting the initial call).
   *  Default: 3 — yields delays of 1 s, 2 s, 4 s. */
  maxAttempts?: number;

  /** Base delay in milliseconds for the first retry.
   *  Each subsequent delay doubles: baseDelayMs, 2×, 4×, …
   *  Default: 1000 ms. */
  baseDelayMs?: number;

  /**
   * Optional callback invoked before each retry.
   *
   * @param attempt - 1-based attempt index that is about to be executed
   *                  (so the callback fires after the first failure with
   *                  `attempt = 2` for the first retry).
   * @param error   - The error that triggered this retry.
   * @param delayMs - The delay that will be observed before the retry.
   */
  onRetry?: (attempt: number, error: Error, delayMs: number) => void;
}

// ---------------------------------------------------------------------------
// Implementation
// ---------------------------------------------------------------------------

/**
 * Returns `true` if `error` is a transient error that should be retried.
 *
 * Only `ApiTimeoutError` (HTTP 408) and `ApiServiceUnavailableError`
 * (HTTP 503) are considered retryable.  All other error types are treated as
 * permanent failures.
 */
function isRetryable(error: unknown): error is Error {
  return (
    error instanceof ApiTimeoutError ||
    error instanceof ApiServiceUnavailableError
  );
}

/**
 * Returns a Promise that resolves after `ms` milliseconds.
 */
function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/**
 * Execute `fn` with automatic exponential-backoff retries on transient
 * failures.
 *
 * Retry schedule (default options):
 * - Attempt 1 (initial): immediate
 * - Attempt 2 (1st retry): wait 1 000 ms
 * - Attempt 3 (2nd retry): wait 2 000 ms
 * - Attempt 4 (3rd retry): wait 4 000 ms
 * - Give up and rethrow the last error.
 *
 * Non-retryable errors are rethrown immediately without delay.
 *
 * @param fn      - Async factory that performs the API call.
 * @param options - Optional retry configuration (see `RetryOptions`).
 * @returns       - Resolves with the result of `fn` on success.
 * @throws        - The last encountered error after exhausting all attempts,
 *                  or an immediately-rethrown non-retryable error.
 *
 * @example
 * ```typescript
 * const data = await withRetry(() => api.getCampaignOverview(params));
 * ```
 */
export async function withRetry<T>(
  fn: () => Promise<T>,
  options: RetryOptions = {},
): Promise<T> {
  const {
    maxAttempts = 3,
    baseDelayMs = 1_000,
    onRetry,
  } = options;

  let lastError: Error = new Error('Unknown error');

  for (let attempt = 1; attempt <= maxAttempts + 1; attempt++) {
    try {
      return await fn();
    } catch (error) {
      if (!(error instanceof Error)) {
        // Non-Error thrown values — rethrow immediately.
        throw error;
      }

      lastError = error;

      // Non-retryable: propagate without consuming retry budget.
      if (!isRetryable(error)) {
        throw error;
      }

      // Exhausted all retry attempts — rethrow last error.
      if (attempt === maxAttempts + 1) {
        throw error;
      }

      // Calculate delay for this retry:
      // attempt=1 (initial call failed) → wait baseDelayMs × 2^0 = 1 000 ms
      // attempt=2 (1st retry failed)   → wait baseDelayMs × 2^1 = 2 000 ms
      // attempt=3 (2nd retry failed)   → wait baseDelayMs × 2^2 = 4 000 ms
      const delayMs = baseDelayMs * Math.pow(2, attempt - 1);

      if (onRetry !== undefined) {
        onRetry(attempt + 1, error, delayMs);
      }

      await sleep(delayMs);
    }
  }

  // This line is unreachable, but TypeScript needs it for exhaustiveness.
  throw lastError;
}
