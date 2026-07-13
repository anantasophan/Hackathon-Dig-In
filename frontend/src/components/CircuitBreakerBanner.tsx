/**
 * CircuitBreakerBanner.tsx — Warning banner shown when the circuit breaker
 * has tripped due to repeated API failures.
 *
 * Rendered at the top of a page (or section) whenever `isOpen` is true.
 * Provides a "Coba Lagi" button that resets the circuit and allows the user
 * to retry requests.
 *
 * Requirements: 8.5
 */

import React from 'react';
import { AlertTriangle } from 'lucide-react';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface CircuitBreakerBannerProps {
  /** Whether the circuit is currently open (true = show the banner). */
  isOpen: boolean;

  /** Number of consecutive failures that tripped the breaker.
   *  Used in the displayed message.  Default: 5. */
  failureCount?: number;

  /** Callback invoked when the user clicks "Coba Lagi".
   *  Should reset the circuit breaker state and re-fetch data. */
  onReset: () => void;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

/**
 * Banner displayed when the circuit breaker has opened after too many
 * consecutive API failures.
 *
 * Only renders anything when `isOpen` is `true`; returns `null` otherwise.
 *
 * @example
 * ```tsx
 * const { isOpen, reset } = useCircuitBreaker();
 *
 * return (
 *   <>
 *     <CircuitBreakerBanner isOpen={isOpen} onReset={reset} />
 *     <PageContent />
 *   </>
 * );
 * ```
 */
export const CircuitBreakerBanner: React.FC<CircuitBreakerBannerProps> = ({
  isOpen,
  failureCount = 5,
  onReset,
}) => {
  if (!isOpen) {
    return null;
  }

  return (
    <div
      role="alert"
      aria-live="assertive"
      className="flex items-center justify-between gap-4 px-5 py-3.5 mb-4 bg-amber-50 border border-amber-300 rounded-lg text-amber-800 text-sm leading-relaxed"
    >
      <AlertTriangle className="w-5 h-5 flex-shrink-0 text-amber-600" aria-hidden="true" />
      <span className="flex-1">
        Layanan sementara tidak tersedia ({failureCount} kegagalan berturut-turut).
        Harap coba lagi nanti.
      </span>
      <button
        type="button"
        className="flex-shrink-0 whitespace-nowrap px-4 py-1.5 text-sm font-semibold text-white bg-amber-500 hover:bg-amber-600 rounded transition-colors"
        onClick={onReset}
      >
        Coba Lagi
      </button>
    </div>
  );
};
