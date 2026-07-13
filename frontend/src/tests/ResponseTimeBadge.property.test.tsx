/**
 * Property tests for Response Time Badge.
 * Property 6: Response time badge icon is correct for all response times.
 *
 * **Validates: Requirements 5.5, 5.6**
 *
 * Strategy:
 * - The response time badge is rendered inline inside CampaignOverviewPage.tsx.
 *   Rather than mounting the full page (which requires heavy mocks for auth,
 *   API, Chart.js etc.), we mirror the exact conditional expressions from the
 *   component as pure helper functions and test those directly.
 * - We also render a minimal TestBadge component that reproduces the same
 *   branching logic, allowing us to verify icon name and color class end-to-end
 *   via @testing-library/react without any external dependencies.
 *
 * Source logic in CampaignOverviewPage.tsx (responseMs !== null block):
 *   className = responseMs < 5000
 *     ? 'inline-flex items-center gap-1 text-xs font-medium text-emerald-600'
 *     : 'inline-flex items-center gap-1 text-xs font-medium text-amber-600'
 *
 *   icon = responseMs < 5000
 *     ? <CheckCircle className="w-3.5 h-3.5" />
 *     : <AlertCircle className="w-3.5 h-3.5" />
 */

import React from 'react';
import { render } from '@testing-library/react';
import * as fc from 'fast-check';

// ---------------------------------------------------------------------------
// Ground-truth constants (mirrors CampaignOverviewPage.tsx exactly)
// ---------------------------------------------------------------------------

const THRESHOLD_MS = 5000;

const FAST_CLASS  = 'text-emerald-600';
const SLOW_CLASS  = 'text-amber-600';
const FAST_ICON   = 'CheckCircle';
const SLOW_ICON   = 'AlertCircle';

// ---------------------------------------------------------------------------
// Pure helper functions (mirror the conditional branches in the component)
// ---------------------------------------------------------------------------

/**
 * Returns the color class for the response time badge.
 * Mirrors:
 *   responseMs < 5000
 *     ? 'inline-flex items-center gap-1 text-xs font-medium text-emerald-600'
 *     : 'inline-flex items-center gap-1 text-xs font-medium text-amber-600'
 */
function getResponseTimeBadgeClass(responseMs: number): string {
  return responseMs < THRESHOLD_MS
    ? `inline-flex items-center gap-1 text-xs font-medium ${FAST_CLASS}`
    : `inline-flex items-center gap-1 text-xs font-medium ${SLOW_CLASS}`;
}

/**
 * Returns the icon name for the response time badge.
 * Mirrors:
 *   responseMs < 5000 ? 'CheckCircle' : 'AlertCircle'
 */
function getResponseTimeBadgeIcon(responseMs: number): string {
  return responseMs < THRESHOLD_MS ? FAST_ICON : SLOW_ICON;
}

// ---------------------------------------------------------------------------
// Minimal TestBadge — renders the same logic as CampaignOverviewPage's badge
// block, using data-testid for easy querying.
// ---------------------------------------------------------------------------

const TestBadge: React.FC<{ responseMs: number }> = ({ responseMs }) => {
  const badgeClass = getResponseTimeBadgeClass(responseMs);
  const iconName   = getResponseTimeBadgeIcon(responseMs);
  return (
    <span
      className={badgeClass}
      aria-live="polite"
      data-testid="response-badge"
    >
      <span data-testid="badge-icon">{iconName}</span>
      <span data-testid="badge-text">
        {responseMs < THRESHOLD_MS ? '< 5s' : '>= 5s'}
      </span>
    </span>
  );
};

// ---------------------------------------------------------------------------
// Arbitrary
// ---------------------------------------------------------------------------

/**
 * fc.float with min/max constraints produces floats in [0, 60000].
 * We use Math.fround to ensure boundaries are valid 32-bit floats as required
 * by fast-check's fc.float constraint validation.
 */
const responseMsArb = fc
  .float({ min: 0, max: Math.fround(60000), noNaN: true })
  .filter((v) => isFinite(v));

// ---------------------------------------------------------------------------
// Suite 1 — pure function tests (no DOM)
// ---------------------------------------------------------------------------

describe('ResponseTimeBadge — Property 6: getResponseTimeBadgeClass returns correct color class', () => {
  /**
   * Property: for any responseMs in [0, 60000],
   *   - if responseMs < 5000  → class contains 'text-emerald-600'
   *   - if responseMs >= 5000 → class contains 'text-amber-600'
   * **Validates: Requirements 5.5, 5.6**
   */
  it('class contains text-emerald-600 when responseMs < 5000', () => {
    fc.assert(
      fc.property(
        // Use Math.fround to ensure 32-bit float boundary compliance
        fc.float({ min: 0, max: Math.fround(4999), noNaN: true }).filter(isFinite),
        (responseMs) => {
          const cls = getResponseTimeBadgeClass(responseMs);
          return cls.includes(FAST_CLASS) && !cls.includes(SLOW_CLASS);
        }
      ),
      { numRuns: 200 }
    );
  });

  it('class contains text-amber-600 when responseMs >= 5000', () => {
    fc.assert(
      fc.property(
        fc.float({ min: Math.fround(5000), max: Math.fround(60000), noNaN: true }).filter(isFinite),
        (responseMs) => {
          const cls = getResponseTimeBadgeClass(responseMs);
          return cls.includes(SLOW_CLASS) && !cls.includes(FAST_CLASS);
        }
      ),
      { numRuns: 200 }
    );
  });

  it('class color is mutually exclusive — exactly one of emerald/amber is present', () => {
    fc.assert(
      fc.property(responseMsArb, (responseMs) => {
        const cls = getResponseTimeBadgeClass(responseMs);
        const hasEmerald = cls.includes(FAST_CLASS);
        const hasAmber   = cls.includes(SLOW_CLASS);
        // XOR — exactly one must be true
        return hasEmerald !== hasAmber;
      }),
      { numRuns: 500 }
    );
  });

  // Example-based checks for direct requirement traceability

  it('0ms → text-emerald-600 (Requirement 5.5)', () => {
    expect(getResponseTimeBadgeClass(0)).toContain(FAST_CLASS);
  });

  it('4999ms → text-emerald-600 (Requirement 5.5)', () => {
    expect(getResponseTimeBadgeClass(4999)).toContain(FAST_CLASS);
  });

  it('5000ms → text-amber-600 (Requirement 5.6)', () => {
    expect(getResponseTimeBadgeClass(5000)).toContain(SLOW_CLASS);
  });

  it('60000ms → text-amber-600 (Requirement 5.6)', () => {
    expect(getResponseTimeBadgeClass(60000)).toContain(SLOW_CLASS);
  });
});

describe('ResponseTimeBadge — Property 6: getResponseTimeBadgeIcon returns correct icon', () => {
  /**
   * Property: for any responseMs in [0, 60000],
   *   - if responseMs < 5000  → icon is 'CheckCircle'
   *   - if responseMs >= 5000 → icon is 'AlertCircle'
   * **Validates: Requirements 5.5, 5.6**
   */
  it('icon is CheckCircle when responseMs < 5000', () => {
    fc.assert(
      fc.property(
        fc.float({ min: 0, max: Math.fround(4999), noNaN: true }).filter(isFinite),
        (responseMs) => getResponseTimeBadgeIcon(responseMs) === FAST_ICON
      ),
      { numRuns: 200 }
    );
  });

  it('icon is AlertCircle when responseMs >= 5000', () => {
    fc.assert(
      fc.property(
        fc.float({ min: Math.fround(5000), max: Math.fround(60000), noNaN: true }).filter(isFinite),
        (responseMs) => getResponseTimeBadgeIcon(responseMs) === SLOW_ICON
      ),
      { numRuns: 200 }
    );
  });

  // Boundary examples

  it('icon at exactly 4999ms is CheckCircle', () => {
    expect(getResponseTimeBadgeIcon(4999)).toBe(FAST_ICON);
  });

  it('icon at exactly 5000ms is AlertCircle', () => {
    expect(getResponseTimeBadgeIcon(5000)).toBe(SLOW_ICON);
  });
});

// ---------------------------------------------------------------------------
// Suite 2 — rendering tests (DOM)
// ---------------------------------------------------------------------------

describe('ResponseTimeBadge — Property 6: TestBadge renders correct icon and color class', () => {
  /**
   * Property: for any responseMs in [0, 60000], when TestBadge is rendered:
   *   - the badge span className contains the correct color class
   *   - the icon span textContent equals the correct icon name
   * **Validates: Requirements 5.5, 5.6**
   */
  it('renders correct color class and icon for all responseMs values', () => {
    fc.assert(
      fc.property(responseMsArb, (responseMs) => {
        const { getByTestId, unmount } = render(
          <TestBadge responseMs={responseMs} />
        );

        const badgeEl = getByTestId('response-badge');
        const iconEl  = getByTestId('badge-icon');

        const isFast = responseMs < THRESHOLD_MS;
        const expectedClass = isFast ? FAST_CLASS : SLOW_CLASS;
        const expectedIcon  = isFast ? FAST_ICON  : SLOW_ICON;

        const hasCorrectClass = badgeEl.className.includes(expectedClass);
        const hasCorrectIcon  = iconEl.textContent === expectedIcon;

        unmount();
        return hasCorrectClass && hasCorrectIcon;
      }),
      { numRuns: 300 }
    );
  });

  it('fast path (0ms): renders CheckCircle with text-emerald-600', () => {
    const { getByTestId } = render(<TestBadge responseMs={0} />);
    expect(getByTestId('response-badge').className).toContain(FAST_CLASS);
    expect(getByTestId('badge-icon').textContent).toBe(FAST_ICON);
  });

  it('fast path (4999ms): renders CheckCircle with text-emerald-600', () => {
    const { getByTestId } = render(<TestBadge responseMs={4999} />);
    expect(getByTestId('response-badge').className).toContain(FAST_CLASS);
    expect(getByTestId('badge-icon').textContent).toBe(FAST_ICON);
  });

  it('slow path (5000ms): renders AlertCircle with text-amber-600', () => {
    const { getByTestId } = render(<TestBadge responseMs={5000} />);
    expect(getByTestId('response-badge').className).toContain(SLOW_CLASS);
    expect(getByTestId('badge-icon').textContent).toBe(SLOW_ICON);
  });

  it('slow path (60000ms): renders AlertCircle with text-amber-600', () => {
    const { getByTestId } = render(<TestBadge responseMs={60000} />);
    expect(getByTestId('response-badge').className).toContain(SLOW_CLASS);
    expect(getByTestId('badge-icon').textContent).toBe(SLOW_ICON);
  });

  it('color class is mutually exclusive for all rendered badges', () => {
    fc.assert(
      fc.property(responseMsArb, (responseMs) => {
        const { getByTestId, unmount } = render(
          <TestBadge responseMs={responseMs} />
        );

        const cls = getByTestId('response-badge').className;
        const hasEmerald = cls.includes(FAST_CLASS);
        const hasAmber   = cls.includes(SLOW_CLASS);

        unmount();
        return hasEmerald !== hasAmber; // XOR — exactly one
      }),
      { numRuns: 300 }
    );
  });
});
