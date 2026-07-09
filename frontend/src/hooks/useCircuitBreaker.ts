/**
 * useCircuitBreaker.ts — React hook for the circuit-breaker pattern.
 *
 * Tracks consecutive API failures.  After `threshold` consecutive failures
 * the circuit "opens" (isOpen = true), signalling to the UI that requests
 * should be suspended and the user should be informed.  A single success
 * call (or an explicit `reset`) closes the circuit and resets the counter.
 *
 * Requirements: 8.5
 */

import { useState, useCallback } from 'react';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface CircuitBreakerState {
  /** True when the circuit breaker has tripped (too many consecutive failures). */
  isOpen: boolean;

  /** Record one failure.  Opens the circuit if the threshold is reached. */
  recordFailure: () => void;

  /** Record one success.  Closes the circuit and resets the failure counter. */
  recordSuccess: () => void;

  /** Force-close the circuit and reset the failure counter. */
  reset: () => void;
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

/**
 * Circuit-breaker hook.
 *
 * @param threshold - Number of consecutive failures before the circuit opens.
 *                    Default: 5.
 * @returns Object with circuit state and control functions.
 *
 * @example
 * ```tsx
 * const { isOpen, recordFailure, recordSuccess, reset } = useCircuitBreaker();
 *
 * async function fetchData() {
 *   try {
 *     const data = await api.getCampaignOverview(params);
 *     recordSuccess();
 *     return data;
 *   } catch (err) {
 *     recordFailure();
 *     throw err;
 *   }
 * }
 * ```
 */
export function useCircuitBreaker(threshold = 5): CircuitBreakerState {
  const [consecutiveFailures, setConsecutiveFailures] = useState<number>(0);
  const [isOpen, setIsOpen] = useState<boolean>(false);

  const recordFailure = useCallback(() => {
    setConsecutiveFailures((prev) => {
      const next = prev + 1;
      if (next >= threshold) {
        setIsOpen(true);
      }
      return next;
    });
  }, [threshold]);

  const recordSuccess = useCallback(() => {
    setConsecutiveFailures(0);
    setIsOpen(false);
  }, []);

  const reset = useCallback(() => {
    setConsecutiveFailures(0);
    setIsOpen(false);
  }, []);

  return { isOpen, recordFailure, recordSuccess, reset };
}
