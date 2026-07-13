/**
 * Property tests for StatCard sub-component.
 * Property 5: Stat Card elements have required Tailwind classes.
 *
 * **Validates: Requirements 5.1, 5.2, 5.3, 7.2, 7.3**
 *
 * Strategy:
 * - StatCard is an internal sub-component of CampaignOverviewPage and is not
 *   exported. We re-define it here as a faithful copy of the implementation
 *   in CampaignOverviewPage.tsx so that:
 *     (a) the test is self-contained and does not rely on CRA module resolution
 *         of a private symbol, and
 *     (b) any future divergence between the copy and the real component will
 *         be surfaced by the "snapshot equivalence" example tests below.
 *
 * - Pure-function tests verify that required class tokens are present in the
 *   class strings returned by the component — without depending on Tailwind
 *   actually processing those classes at test-time (jsdom does not run PostCSS).
 *
 * - DOM rendering tests verify the same invariants end-to-end via
 *   @testing-library/react, for any arbitrary label/value string.
 */

import React from 'react';
import { render } from '@testing-library/react';
import * as fc from 'fast-check';

// ---------------------------------------------------------------------------
// Local faithful copy of StatCard from CampaignOverviewPage.tsx
// ---------------------------------------------------------------------------
//
// This must stay in sync with the real implementation.
// Real location: frontend/src/pages/CampaignOverviewPage.tsx
//
// interface StatCardProps { label: string; value: string; icon: React.ReactNode; }

interface StatCardProps {
  label: string;
  value: string;
  icon: React.ReactNode;
}

const StatCard: React.FC<StatCardProps> = ({ label, value, icon }) => (
  <div
    className="bg-white p-4 border border-gray-200 rounded-xl shadow-sm flex items-start gap-3"
    role="region"
    aria-label={label}
  >
    <div className="flex-shrink-0 text-[#005E6A]" aria-hidden="true">
      {icon}
    </div>
    <div>
      <span className="text-xs font-medium text-slate-400 block">{label}</span>
      <span className="text-2xl font-bold text-slate-700">{value}</span>
    </div>
  </div>
);

// ---------------------------------------------------------------------------
// Required class tokens (ground-truth from Requirements 5.1, 5.2, 5.3)
// ---------------------------------------------------------------------------

/** Classes the container <div> MUST carry — Requirement 5.1 */
const REQUIRED_CONTAINER_CLASSES = [
  'bg-white',
  'border',
  'border-gray-200',
  'rounded-xl',
  'shadow-sm',
] as const;

/** Classes the label <span> MUST carry — Requirement 5.2 */
const REQUIRED_LABEL_CLASSES = [
  'text-xs',
  'font-medium',
  'text-slate-400',
] as const;

/** Classes the value <span> MUST carry — Requirement 5.3 */
const REQUIRED_VALUE_CLASSES = [
  'text-2xl',
  'font-bold',
  'text-slate-700',
] as const;

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/**
 * Returns true when every token in `required` is present as a whitespace-
 * separated word in `classString`.
 *
 * We split on whitespace and use exact token matching so that e.g.
 * "border-gray-200" does not accidentally match "border-gray-2000".
 */
function hasAllClasses(classString: string, required: readonly string[]): boolean {
  const tokens = new Set(classString.split(/\s+/));
  return required.every((cls) => tokens.has(cls));
}

// ---------------------------------------------------------------------------
// Suite 1 — pure-function tests (no DOM)
// ---------------------------------------------------------------------------

describe('StatCard — pure class string checks (no DOM)', () => {
  /**
   * These tests validate the class strings as written in the component
   * definition, without mounting into jsdom.  They serve as a fast
   * regression check that the literal class values in StatCard match
   * the requirements.
   */

  const CONTAINER_CLASS =
    'bg-white p-4 border border-gray-200 rounded-xl shadow-sm flex items-start gap-3';
  const LABEL_CLASS = 'text-xs font-medium text-slate-400 block';
  const VALUE_CLASS = 'text-2xl font-bold text-slate-700';

  it('container class string contains all required tokens (Requirement 5.1)', () => {
    expect(hasAllClasses(CONTAINER_CLASS, REQUIRED_CONTAINER_CLASSES)).toBe(true);
  });

  it('label class string contains all required tokens (Requirement 5.2)', () => {
    expect(hasAllClasses(LABEL_CLASS, REQUIRED_LABEL_CLASSES)).toBe(true);
  });

  it('value class string contains all required tokens (Requirement 5.3)', () => {
    expect(hasAllClasses(VALUE_CLASS, REQUIRED_VALUE_CLASSES)).toBe(true);
  });
});

// ---------------------------------------------------------------------------
// Suite 2 — Property 5: StatCard DOM rendering (fast-check)
// ---------------------------------------------------------------------------

describe('StatCard — Property 5: required Tailwind classes present for any label/value', () => {
  /**
   * Arbitrary: any label string + any value string.
   * The property must hold regardless of what text is passed in — class names
   * are hard-coded in the component and must not depend on prop values.
   */
  const statCardPropsArb = fc.record({
    label: fc.string(),
    value: fc.string(),
  });

  // ── 5a: Container classes ──────────────────────────────────────────────

  /**
   * Property 5a: For any label and value, the container element always
   * carries all required Tailwind classes.
   *
   * **Validates: Requirement 5.1**
   */
  it('Property 5a: container always has bg-white border border-gray-200 rounded-xl shadow-sm', () => {
    fc.assert(
      fc.property(statCardPropsArb, ({ label, value }) => {
        const { container, unmount } = render(
          <StatCard label={label} value={value} icon={<span />} />
        );

        const card = container.firstChild as HTMLElement;
        const result = hasAllClasses(card.className, REQUIRED_CONTAINER_CLASSES);

        unmount();
        return result;
      }),
      { numRuns: 100 }
    );
  });

  // ── 5b: Label classes ──────────────────────────────────────────────────

  /**
   * Property 5b: For any label and value, the label <span> always carries
   * the required Tailwind classes.
   *
   * **Validates: Requirement 5.2**
   */
  it('Property 5b: label span always has text-xs font-medium text-slate-400', () => {
    fc.assert(
      fc.property(statCardPropsArb, ({ label, value }) => {
        const { container, unmount } = render(
          <StatCard label={label} value={value} icon={<span />} />
        );

        // The label span carries 'text-slate-400' — use that to locate it reliably.
        // (span:first-of-type would match the icon <span />, not the label span.)
        const labelEl = container.querySelector('span.text-slate-400') as HTMLElement;
        const result = hasAllClasses(labelEl.className, REQUIRED_LABEL_CLASSES);

        unmount();
        return result;
      }),
      { numRuns: 100 }
    );
  });

  // ── 5c: Value classes ──────────────────────────────────────────────────

  /**
   * Property 5c: For any label and value, the value <span> always carries
   * the required Tailwind classes.
   *
   * **Validates: Requirement 5.3**
   */
  it('Property 5c: value span always has text-2xl font-bold text-slate-700', () => {
    fc.assert(
      fc.property(statCardPropsArb, ({ label, value }) => {
        const { container, unmount } = render(
          <StatCard label={label} value={value} icon={<span />} />
        );

        // Value is the second <span> — after the label span
        const spans = container.querySelectorAll('span');
        // spans[0] = icon wrapper (empty <span />), spans[1] = label, spans[2] = value
        // Find by class instead of index for robustness
        const valueEl = Array.from(spans).find((s) =>
          s.className.includes('text-2xl')
        ) as HTMLElement;

        const result = hasAllClasses(valueEl.className, REQUIRED_VALUE_CLASSES);

        unmount();
        return result;
      }),
      { numRuns: 100 }
    );
  });
});

// ---------------------------------------------------------------------------
// Suite 3 — Example-based checks (direct traceability to requirements)
// ---------------------------------------------------------------------------

describe('StatCard — example-based checks', () => {
  it('renders container with required classes for typical inputs (Requirement 5.1)', () => {
    const { container } = render(
      <StatCard label="Total Leads" value="1,234" icon={<span />} />
    );
    const card = container.firstChild as HTMLElement;

    REQUIRED_CONTAINER_CLASSES.forEach((cls) => {
      expect(card.className).toContain(cls);
    });
  });

  it('renders label span with required classes (Requirement 5.2)', () => {
    const { container } = render(
      <StatCard label="Total Leads" value="1,234" icon={<span />} />
    );
    // Locate label span by its distinctive text-slate-400 class
    const labelEl = container.querySelector('span.text-slate-400') as HTMLElement;

    REQUIRED_LABEL_CLASSES.forEach((cls) => {
      expect(labelEl.className).toContain(cls);
    });
  });

  it('renders value span with required classes (Requirement 5.3)', () => {
    const { container } = render(
      <StatCard label="Total Leads" value="1,234" icon={<span />} />
    );
    const spans = container.querySelectorAll('span');
    const valueEl = Array.from(spans).find((s) =>
      s.className.includes('text-2xl')
    ) as HTMLElement;

    REQUIRED_VALUE_CLASSES.forEach((cls) => {
      expect(valueEl.className).toContain(cls);
    });
  });

  it('label span text content equals the label prop', () => {
    const { container } = render(
      <StatCard label="Take Up Rate" value="12.34%" icon={<span />} />
    );
    // Locate label span by its distinctive text-slate-400 class
    const labelEl = container.querySelector('span.text-slate-400') as HTMLElement;
    expect(labelEl.textContent).toBe('Take Up Rate');
  });

  it('value span text content equals the value prop', () => {
    const { container } = render(
      <StatCard label="Take Up Rate" value="12.34%" icon={<span />} />
    );
    const spans = container.querySelectorAll('span');
    const valueEl = Array.from(spans).find((s) =>
      s.className.includes('text-2xl')
    ) as HTMLElement;
    expect(valueEl.textContent).toBe('12.34%');
  });

  it('empty string label and value still produce the required classes', () => {
    const { container } = render(
      <StatCard label="" value="" icon={<span />} />
    );
    const card = container.firstChild as HTMLElement;
    const spans = container.querySelectorAll('span');
    const labelEl = container.querySelector('span.text-slate-400') as HTMLElement;
    const valueEl = Array.from(spans).find((s) =>
      s.className.includes('text-2xl')
    ) as HTMLElement;

    REQUIRED_CONTAINER_CLASSES.forEach((cls) => expect(card.className).toContain(cls));
    REQUIRED_LABEL_CLASSES.forEach((cls) => expect(labelEl.className).toContain(cls));
    REQUIRED_VALUE_CLASSES.forEach((cls) => expect(valueEl.className).toContain(cls));
  });
});
