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
// Styles (inline to avoid an external CSS dependency)
// ---------------------------------------------------------------------------

const bannerStyle: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'space-between',
  gap: '1rem',
  padding: '0.875rem 1.25rem',
  backgroundColor: '#fff3cd',
  border: '1px solid #ffc107',
  borderRadius: '6px',
  color: '#664d03',
  fontSize: '0.9375rem',
  lineHeight: '1.5',
  marginBottom: '1rem',
};

const iconStyle: React.CSSProperties = {
  fontSize: '1.25rem',
  flexShrink: 0,
};

const messageStyle: React.CSSProperties = {
  flex: 1,
};

const retryButtonStyle: React.CSSProperties = {
  padding: '0.375rem 1rem',
  fontSize: '0.875rem',
  fontWeight: 600,
  color: '#fff',
  backgroundColor: '#f0a500',
  border: 'none',
  borderRadius: '4px',
  cursor: 'pointer',
  whiteSpace: 'nowrap',
  flexShrink: 0,
};

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
      style={bannerStyle}
    >
      <span style={iconStyle} aria-hidden="true">⚠️</span>
      <span style={messageStyle}>
        Layanan sementara tidak tersedia ({failureCount} kegagalan berturut-turut).
        Harap coba lagi nanti.
      </span>
      <button
        type="button"
        style={retryButtonStyle}
        onClick={onReset}
        onMouseOver={(e) => {
          (e.currentTarget as HTMLButtonElement).style.backgroundColor = '#d4920a';
        }}
        onMouseOut={(e) => {
          (e.currentTarget as HTMLButtonElement).style.backgroundColor = '#f0a500';
        }}
      >
        Coba Lagi
      </button>
    </div>
  );
};
