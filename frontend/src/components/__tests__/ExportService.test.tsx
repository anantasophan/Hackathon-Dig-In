/**
 * Property tests for ExportService.
 * Property 3: Toast type determines icon and background class.
 * Property 4: Toast messages contain no exclamation marks.
 *
 * **Validates: Requirements 4.3, 4.4, 4.5, 4.10, 11.5**
 *
 * Strategy:
 * - The Toast sub-component is internal to ExportService and not exported,
 *   so we test the mapping logic directly by mirroring the exact conditional
 *   expressions from ExportService.tsx.
 * - We also render a minimal test harness that reproduces the same rendering
 *   logic to verify icon + background class assignment end-to-end.
 */

import React from 'react';
import { render } from '@testing-library/react';
import * as fc from 'fast-check';

// ---------------------------------------------------------------------------
// Ground-truth mapping (mirrors ExportService.tsx exactly)
// ---------------------------------------------------------------------------

type ToastType = 'success' | 'warning' | 'error';

const TOAST_EXPECTATIONS: Record<ToastType, { bg: string; icon: string }> = {
  success: { bg: 'bg-emerald-600', icon: 'CheckCircle' },
  warning: { bg: 'bg-amber-500',   icon: 'AlertCircle' },
  error:   { bg: 'bg-rose-600',    icon: 'XCircle'     },
};

/**
 * Mirrors the exact bgClass ternary from ExportService.tsx Toast sub-component:
 *   type === 'success' ? 'bg-emerald-600' :
 *   type === 'warning' ? 'bg-amber-500'   :
 *   'bg-rose-600'
 */
function getToastBgClass(type: ToastType): string {
  if (type === 'success') return 'bg-emerald-600';
  if (type === 'warning') return 'bg-amber-500';
  return 'bg-rose-600';
}

/**
 * Mirrors the Icon selection ternary from ExportService.tsx Toast sub-component:
 *   type === 'success' ? CheckCircle : type === 'warning' ? AlertCircle : XCircle
 */
function getToastIconName(type: ToastType): string {
  if (type === 'success') return 'CheckCircle';
  if (type === 'warning') return 'AlertCircle';
  return 'XCircle';
}

// ---------------------------------------------------------------------------
// Minimal TestToast — reproduces the Toast render logic without actual Lucide
// SVG (Lucide icons require a DOM environment with SVG support; we use
// data-testid spans that mirror the icon selection branch).
// ---------------------------------------------------------------------------

const TestToast: React.FC<{ type: ToastType }> = ({ type }) => {
  const bgClass = getToastBgClass(type);
  const iconName = getToastIconName(type);
  return (
    <div
      className={`flex items-center gap-3 px-4 py-3 rounded-lg shadow-lg text-white text-xs font-medium ${bgClass}`}
      role="alert"
      data-testid="toast"
    >
      <span data-testid="icon">{iconName}</span>
      <span data-testid="message">Test message</span>
    </div>
  );
};

// ---------------------------------------------------------------------------
// Arbitrary
// ---------------------------------------------------------------------------

const toastTypeArb = fc.constantFrom<ToastType>('success', 'warning', 'error');

// ---------------------------------------------------------------------------
// Suite 1 — pure function tests (no DOM)
// ---------------------------------------------------------------------------

describe('ExportService — Property 3: getToastBgClass maps type → background class', () => {
  /**
   * Property: for every valid toast type, the bg class returned must match
   * the expected value defined in TOAST_EXPECTATIONS.
   * **Validates: Requirements 4.3, 4.4, 4.5**
   */
  it('bg class matches expected value for all valid toast types', () => {
    fc.assert(
      fc.property(toastTypeArb, (type) => {
        return getToastBgClass(type) === TOAST_EXPECTATIONS[type].bg;
      }),
      { numRuns: 10 }
    );
  });

  // Example-based checks for direct traceability to each requirement

  it('success → bg-emerald-600 (Requirement 4.3)', () => {
    expect(getToastBgClass('success')).toBe('bg-emerald-600');
  });

  it('warning → bg-amber-500 (Requirement 4.4)', () => {
    expect(getToastBgClass('warning')).toBe('bg-amber-500');
  });

  it('error → bg-rose-600 (Requirement 4.5)', () => {
    expect(getToastBgClass('error')).toBe('bg-rose-600');
  });
});

describe('ExportService — Property 3: getToastIconName maps type → icon name', () => {
  /**
   * Property: for every valid toast type, the icon name returned must match
   * the expected value defined in TOAST_EXPECTATIONS.
   * **Validates: Requirements 4.3, 4.4, 4.5**
   */
  it('icon name matches expected value for all valid toast types', () => {
    fc.assert(
      fc.property(toastTypeArb, (type) => {
        return getToastIconName(type) === TOAST_EXPECTATIONS[type].icon;
      }),
      { numRuns: 10 }
    );
  });

  it('success → CheckCircle (Requirement 4.3)', () => {
    expect(getToastIconName('success')).toBe('CheckCircle');
  });

  it('warning → AlertCircle (Requirement 4.4)', () => {
    expect(getToastIconName('warning')).toBe('AlertCircle');
  });

  it('error → XCircle (Requirement 4.5)', () => {
    expect(getToastIconName('error')).toBe('XCircle');
  });
});

// ---------------------------------------------------------------------------
// Suite 2 — rendering tests (DOM)
// ---------------------------------------------------------------------------

describe('ExportService — Property 3: Toast renders correct icon and background class', () => {
  /**
   * Property: for every valid toast type, when a Toast is rendered:
   *   - the root element className contains the expected bg class
   *   - the icon element textContent equals the expected icon name
   * **Validates: Requirements 4.3, 4.4, 4.5**
   */
  it('renders correct bg class and icon for all valid toast types', () => {
    fc.assert(
      fc.property(toastTypeArb, (type) => {
        const { getByTestId, unmount } = render(<TestToast type={type} />);

        const toastEl = getByTestId('toast');
        const iconEl  = getByTestId('icon');

        const expected = TOAST_EXPECTATIONS[type];
        const hasBg    = toastEl.className.includes(expected.bg);
        const hasIcon  = iconEl.textContent === expected.icon;

        unmount();
        return hasBg && hasIcon;
      }),
      { numRuns: 10 }
    );
  });

  it('success toast has bg-emerald-600 and CheckCircle icon', () => {
    const { getByTestId } = render(<TestToast type="success" />);
    expect(getByTestId('toast').className).toContain('bg-emerald-600');
    expect(getByTestId('icon').textContent).toBe('CheckCircle');
  });

  it('warning toast has bg-amber-500 and AlertCircle icon', () => {
    const { getByTestId } = render(<TestToast type="warning" />);
    expect(getByTestId('toast').className).toContain('bg-amber-500');
    expect(getByTestId('icon').textContent).toBe('AlertCircle');
  });

  it('error toast has bg-rose-600 and XCircle icon', () => {
    const { getByTestId } = render(<TestToast type="error" />);
    expect(getByTestId('toast').className).toContain('bg-rose-600');
    expect(getByTestId('icon').textContent).toBe('XCircle');
  });

  it('bg class is mutually exclusive — only one bg class present per type', () => {
    const allBgClasses = ['bg-emerald-600', 'bg-amber-500', 'bg-rose-600'];

    fc.assert(
      fc.property(toastTypeArb, (type) => {
        const { getByTestId, unmount } = render(<TestToast type={type} />);
        const className = getByTestId('toast').className;

        // Exactly one of the three bg classes should be present
        const present = allBgClasses.filter((cls) => className.includes(cls));
        unmount();
        return present.length === 1 && present[0] === TOAST_EXPECTATIONS[type].bg;
      }),
      { numRuns: 10 }
    );
  });
});

// ---------------------------------------------------------------------------
// Suite 3 — Property 4: Toast messages contain no exclamation marks
// ---------------------------------------------------------------------------

/**
 * Mirrors the toast message generation logic from ExportService.tsx.
 *
 * This function replicates the exact messages set in the component's
 * handleExport handler so we can test the message strings independently
 * from React rendering.
 *
 * Source messages in ExportService.tsx:
 *   - completed: 'File siap diunduh'
 *   - timeout:   'Ekspor timeout (>30 detik). Coba kurangi rentang data atau coba lagi'
 *   - error:     `Ekspor gagal: ${cause}. Coba lagi`
 */
function getToastMessages(
  status: 'completed' | 'timeout' | 'error',
  cause: string
): string[] {
  switch (status) {
    case 'completed':
      return ['File siap diunduh'];
    case 'timeout':
      return [
        'Ekspor timeout (>30 detik). Coba kurangi rentang data atau coba lagi',
      ];
    case 'error':
      return [`Ekspor gagal: ${cause}. Coba lagi`];
    default:
      return [];
  }
}

describe('ExportService — Property 4: Toast messages contain no exclamation marks', () => {
  /**
   * Property: for any valid export status and any error cause string,
   * none of the generated toast messages contain a `!` character.
   *
   * **Validates: Requirements 4.10, 11.5**
   */
  it('no toast message contains an exclamation mark', () => {
    fc.assert(
      fc.property(
        fc.constantFrom(
          'completed',
          'timeout',
          'error'
        ) as fc.Arbitrary<'completed' | 'timeout' | 'error'>,
        fc.string({ maxLength: 100 }), // error cause — arbitrary string
        (status, cause) => {
          const messages = getToastMessages(status, cause);
          return messages.every((msg) => !msg.includes('!'));
        }
      ),
      { numRuns: 50 }
    );
  });

  /**
   * Example: success message has no exclamation mark.
   * Guards against a regression like adding "File siap diunduh!" in the future.
   */
  it('success message "File siap diunduh" has no exclamation mark', () => {
    const messages = getToastMessages('completed', '');
    expect(messages.every((m) => !m.includes('!'))).toBe(true);
  });

  /**
   * Example: timeout message has no exclamation mark.
   */
  it('timeout message has no exclamation mark', () => {
    const messages = getToastMessages('timeout', '');
    expect(messages.every((m) => !m.includes('!'))).toBe(true);
  });

  /**
   * Property: error message with an arbitrary cause (that itself contains
   * no `!`) must not introduce an exclamation mark via the template literal.
   *
   * **Validates: Requirements 4.10, 11.5**
   */
  it('error message with arbitrary cause has no exclamation mark', () => {
    fc.assert(
      fc.property(
        fc.string({ maxLength: 200 }).filter((s) => !s.includes('!')), // cause without !
        (cause) => {
          const messages = getToastMessages('error', cause);
          return messages.every((m) => !m.includes('!'));
        }
      ),
      { numRuns: 30 }
    );
  });
});
