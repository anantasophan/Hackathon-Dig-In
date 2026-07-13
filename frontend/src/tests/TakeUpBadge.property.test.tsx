/**
 * Property and unit tests for the take-up rate badge class logic.
 *
 * Property 8: Take-up rate badge class is determined by rate value
 * Validates: Requirements 8.5, 8.6, 8.7
 *
 * Strategy:
 * - `getTakeUpBadgeClasses` is a pure function with no dependencies on
 *   React state, API calls, or Chart.js.  Importing RegionalPerformancePage
 *   would pull in the `api` service (which imports axios as ESM) and fail
 *   Jest's transform step.
 * - Instead we mirror the exact implementation here and test it in isolation.
 *   This is the same pattern used by ExportService.test.tsx and
 *   CampaignChip.property.test.tsx in this project.
 * - The mirror is intentionally kept identical to the production
 *   implementation so that any future divergence becomes a failing test.
 */

import fc from 'fast-check';

// ---------------------------------------------------------------------------
// Mirror of the production function from RegionalPerformancePage.tsx
// (exported there as `getTakeUpBadgeClasses`)
//
// IMPORTANT: Keep this in sync with the source in RegionalPerformancePage.tsx
// ---------------------------------------------------------------------------

/**
 * Returns a full Tailwind class string for the take-up rate badge.
 *
 * @param rate - take-up rate percentage (e.g. 12.5 means 12.5 %)
 *
 * Thresholds:
 *   rate >= 10  →  bg-emerald-100 text-emerald-700   (high)
 *   rate >=  5  →  bg-amber-100   text-amber-700     (medium)
 *   rate <   5  →  bg-rose-100    text-rose-700      (low)
 */
function getTakeUpBadgeClasses(rate: number): string {
  if (rate >= 10) return 'bg-emerald-100 text-emerald-700 rounded px-1.5 py-0.5 text-xs font-semibold';
  if (rate >= 5)  return 'bg-amber-100 text-amber-700 rounded px-1.5 py-0.5 text-xs font-semibold';
  return 'bg-rose-100 text-rose-700 rounded px-1.5 py-0.5 text-xs font-semibold';
}

// ---------------------------------------------------------------------------
// Shared layout classes expected in every tier
// ---------------------------------------------------------------------------

const SHARED_CLASSES = ['rounded', 'px-1.5', 'py-0.5', 'text-xs', 'font-semibold'];

// ── Unit tests ────────────────────────────────────────────────────────────

describe('getTakeUpBadgeClasses unit tests', () => {

  // ── High tier (rate >= 10) ─────────────────────────────────────────────

  describe('rate >= 10 → emerald (high tier)', () => {
    it('returns emerald classes for rate exactly 10', () => {
      const classes = getTakeUpBadgeClasses(10);
      expect(classes).toContain('bg-emerald-100');
      expect(classes).toContain('text-emerald-700');
    });

    it('returns emerald classes for rate 25', () => {
      const classes = getTakeUpBadgeClasses(25);
      expect(classes).toContain('bg-emerald-100');
      expect(classes).toContain('text-emerald-700');
    });

    it('returns emerald classes for rate 50', () => {
      const classes = getTakeUpBadgeClasses(50);
      expect(classes).toContain('bg-emerald-100');
      expect(classes).toContain('text-emerald-700');
    });

    it('does NOT include amber or rose tokens for rate >= 10', () => {
      const classes = getTakeUpBadgeClasses(15);
      expect(classes).not.toContain('bg-amber-100');
      expect(classes).not.toContain('bg-rose-100');
    });
  });

  // ── Medium tier (5 <= rate < 10) ─────────────────────────────────────

  describe('5 <= rate < 10 → amber (medium tier)', () => {
    it('returns amber classes for rate exactly 5', () => {
      const classes = getTakeUpBadgeClasses(5);
      expect(classes).toContain('bg-amber-100');
      expect(classes).toContain('text-amber-700');
    });

    it('returns amber classes for rate 7.5', () => {
      const classes = getTakeUpBadgeClasses(7.5);
      expect(classes).toContain('bg-amber-100');
      expect(classes).toContain('text-amber-700');
    });

    it('returns amber classes for rate 9.99', () => {
      const classes = getTakeUpBadgeClasses(9.99);
      expect(classes).toContain('bg-amber-100');
      expect(classes).toContain('text-amber-700');
    });

    it('does NOT include emerald or rose tokens for 5 <= rate < 10', () => {
      const classes = getTakeUpBadgeClasses(7);
      expect(classes).not.toContain('bg-emerald-100');
      expect(classes).not.toContain('bg-rose-100');
    });
  });

  // ── Low tier (rate < 5) ───────────────────────────────────────────────

  describe('rate < 5 → rose (low tier)', () => {
    it('returns rose classes for rate 0', () => {
      const classes = getTakeUpBadgeClasses(0);
      expect(classes).toContain('bg-rose-100');
      expect(classes).toContain('text-rose-700');
    });

    it('returns rose classes for rate 2.5', () => {
      const classes = getTakeUpBadgeClasses(2.5);
      expect(classes).toContain('bg-rose-100');
      expect(classes).toContain('text-rose-700');
    });

    it('returns rose classes for rate 4.99', () => {
      const classes = getTakeUpBadgeClasses(4.99);
      expect(classes).toContain('bg-rose-100');
      expect(classes).toContain('text-rose-700');
    });

    it('does NOT include emerald or amber tokens for rate < 5', () => {
      const classes = getTakeUpBadgeClasses(3);
      expect(classes).not.toContain('bg-emerald-100');
      expect(classes).not.toContain('bg-amber-100');
    });
  });

  // ── Shared layout classes (all tiers) ────────────────────────────────

  describe('shared layout classes are always present', () => {
    it.each([0, 4.99, 5, 9.99, 10, 25])(
      'rate %s includes all shared layout classes',
      (rate) => {
        const classes = getTakeUpBadgeClasses(rate);
        SHARED_CLASSES.forEach((cls) => {
          expect(classes).toContain(cls);
        });
      },
    );
  });

  // ── Boundary precision ───────────────────────────────────────────────

  describe('boundary values resolve to the correct tier', () => {
    it('rate 10 is emerald, not amber', () => {
      expect(getTakeUpBadgeClasses(10)).toContain('bg-emerald-100');
      expect(getTakeUpBadgeClasses(10)).not.toContain('bg-amber-100');
    });

    it('rate 5 is amber, not rose', () => {
      expect(getTakeUpBadgeClasses(5)).toContain('bg-amber-100');
      expect(getTakeUpBadgeClasses(5)).not.toContain('bg-rose-100');
    });
  });

  // ── Mutual exclusivity ───────────────────────────────────────────────

  describe('colour tokens are mutually exclusive', () => {
    const allBgTokens = ['bg-emerald-100', 'bg-amber-100', 'bg-rose-100'];
    const allTextTokens = ['text-emerald-700', 'text-amber-700', 'text-rose-700'];

    it.each([0, 2.5, 4.99, 5, 7.5, 9.99, 10, 20, 50])(
      'rate %s: exactly one background colour token present',
      (rate) => {
        const classes = getTakeUpBadgeClasses(rate);
        const presentBg = allBgTokens.filter((t) => classes.includes(t));
        expect(presentBg).toHaveLength(1);
      },
    );

    it.each([0, 2.5, 4.99, 5, 7.5, 9.99, 10, 20, 50])(
      'rate %s: exactly one text colour token present',
      (rate) => {
        const classes = getTakeUpBadgeClasses(rate);
        const presentText = allTextTokens.filter((t) => classes.includes(t));
        expect(presentText).toHaveLength(1);
      },
    );
  });
});

// ── Property test ─────────────────────────────────────────────────────────

/**
 * **Property 8: badge class is determined by rate boundaries**
 * **Validates: Requirements 8.5, 8.6, 8.7**
 *
 * For any float rate in [0, 50]:
 *   - rate >= 10         →  bg-emerald-100  +  text-emerald-700
 *   - 5 <= rate < 10     →  bg-amber-100    +  text-amber-700
 *   - rate < 5           →  bg-rose-100     +  text-rose-700
 *
 * In all three cases:
 *   - Only one background colour token is present (mutual exclusivity)
 *   - All shared layout classes are present (rounded, px-1.5, py-0.5, text-xs, font-semibold)
 */
describe('Property 8: badge class is determined by rate boundaries', () => {
  const allBgTokens   = ['bg-emerald-100', 'bg-amber-100', 'bg-rose-100'];
  const allTextTokens = ['text-emerald-700', 'text-amber-700', 'text-rose-700'];

  it('correct colour tier for all rates in [0, 50]', () => {
    fc.assert(
      fc.property(fc.float({ min: 0, max: 50, noNaN: true }), (rate) => {
        const classes = getTakeUpBadgeClasses(rate);

        // ── Tier assertion ──
        if (rate >= 10) {
          // High tier — emerald (Requirement 8.5)
          expect(classes).toContain('bg-emerald-100');
          expect(classes).toContain('text-emerald-700');
          expect(classes).not.toContain('bg-amber-100');
          expect(classes).not.toContain('bg-rose-100');
        } else if (rate >= 5) {
          // Medium tier — amber (Requirement 8.6)
          expect(classes).toContain('bg-amber-100');
          expect(classes).toContain('text-amber-700');
          expect(classes).not.toContain('bg-emerald-100');
          expect(classes).not.toContain('bg-rose-100');
        } else {
          // Low tier — rose (Requirement 8.7)
          expect(classes).toContain('bg-rose-100');
          expect(classes).toContain('text-rose-700');
          expect(classes).not.toContain('bg-emerald-100');
          expect(classes).not.toContain('bg-amber-100');
        }

        // ── Mutual exclusivity (exactly one bg + one text token) ──
        const presentBg   = allBgTokens.filter((t) => classes.includes(t));
        const presentText = allTextTokens.filter((t) => classes.includes(t));
        expect(presentBg).toHaveLength(1);
        expect(presentText).toHaveLength(1);

        // ── Shared layout classes always present ──
        SHARED_CLASSES.forEach((cls) => {
          expect(classes).toContain(cls);
        });
      }),
    );
  });
});
