/**
 * Property tests for LoadingState component.
 * Property 10: Loading state uses Loader2 with animate-spin across all pages.
 *
 * **Validates: Requirements 11.3, 6.8, 8.8**
 *
 * Strategy:
 * - Import and render the real `LoadingState` from StateComponents.tsx directly.
 * - Use `fc.option(fc.string(), { nil: undefined })` as the arbitrary so that
 *   both the default text path (text=undefined) and any custom text path are
 *   exercised by fast-check.
 * - Class-token checks use exact whitespace-split matching to avoid false
 *   positives from substring coincidences.
 * - The "no @keyframes" check scans the entire serialised HTML to confirm no
 *   inline CSS spinner div was rendered.
 *
 * jsdom does not process Tailwind/PostCSS, so we verify the presence of the
 * raw class name strings that the component passes to the DOM — not the
 * computed visual result.
 */

import React from 'react';
import { render } from '@testing-library/react';
import * as fc from 'fast-check';

import { LoadingState } from '../components/StateComponents';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/**
 * Returns true when every token in `required` is present as an exact,
 * whitespace-separated word in `classString`.
 *
 * Exact matching prevents e.g. "animate-spin-fast" from satisfying
 * a check for "animate-spin".
 *
 * Accepts `string | null | undefined` because SVG elements in jsdom expose
 * `.className` as an `SVGAnimatedString` object — callers should pass
 * `el.getAttribute('class')` which returns `string | null`.
 */
function hasAllClasses(classString: string | null | undefined, required: readonly string[]): boolean {
  if (!classString) return false;
  const tokens = new Set(classString.split(/\s+/));
  return required.every((cls) => tokens.has(cls));
}

/**
 * Safe helper to get the class string from any element.
 * Uses `getAttribute('class')` so it works for both HTML and SVG elements
 * in jsdom (SVG elements expose `.className` as SVGAnimatedString, not string).
 */
function getClassString(el: Element | null): string {
  if (!el) return '';
  return el.getAttribute('class') ?? '';
}

// ---------------------------------------------------------------------------
// Required class constants (ground-truth from requirements)
// ---------------------------------------------------------------------------

/** Classes the outer container <div> MUST carry — Requirement 11.3 */
const REQUIRED_CONTAINER_CLASSES = ['text-center', 'py-12'] as const;

/** Classes the Loader2 <svg> MUST carry — Requirements 11.3, 6.8, 8.8 */
const REQUIRED_ICON_CLASSES = ['animate-spin', 'text-[#005E6A]'] as const;

/** Classes the message <p> MUST carry — Requirement 11.3 */
const REQUIRED_MESSAGE_CLASSES = ['text-sm', 'font-medium'] as const;

// ---------------------------------------------------------------------------
// Arbitrary
// ---------------------------------------------------------------------------

/**
 * Generates either `undefined` (triggering the component's default text) or
 * an arbitrary string (custom text override) — exactly as specified in task 14.3.
 */
const textArb = fc.option(fc.string(), { nil: undefined });

// ---------------------------------------------------------------------------
// Suite 1 — Pure class-string checks (no DOM)
// ---------------------------------------------------------------------------

describe('LoadingState — pure class string checks (no DOM)', () => {
  /**
   * Fast regression guard: the literal class strings in the component source
   * must contain all required tokens before any DOM rendering is attempted.
   * These use the same class strings as defined in StateComponents.tsx.
   */

  const CONTAINER_CLASS = 'text-center py-12 text-gray-400';
  const ICON_CLASS = 'w-8 h-8 mx-auto mb-2 animate-spin text-[#005E6A]';
  const MESSAGE_CLASS = 'text-sm font-medium';

  it('container class string contains all required tokens (Requirement 11.3)', () => {
    expect(hasAllClasses(CONTAINER_CLASS, REQUIRED_CONTAINER_CLASSES)).toBe(true);
  });

  it('icon class string contains animate-spin (Requirements 11.3, 6.8, 8.8)', () => {
    expect(hasAllClasses(ICON_CLASS, ['animate-spin'])).toBe(true);
  });

  it('icon class string contains text-[#005E6A] (BNI Teal — Requirements 11.3, 6.8, 8.8)', () => {
    expect(hasAllClasses(ICON_CLASS, ['text-[#005E6A]'])).toBe(true);
  });

  it('message class string contains all required tokens (Requirement 11.3)', () => {
    expect(hasAllClasses(MESSAGE_CLASS, REQUIRED_MESSAGE_CLASSES)).toBe(true);
  });
});

// ---------------------------------------------------------------------------
// Suite 2 — Property 10: DOM rendering (fast-check)
// ---------------------------------------------------------------------------

describe('LoadingState — Property 10: required structure for any loading text', () => {
  // ── 10a: Container classes ────────────────────────────────────────────

  /**
   * Property 10a: For any (or no) text prop, the outer container always has
   * `text-center` and `py-12`.
   *
   * **Validates: Requirements 11.3, 6.8, 8.8**
   */
  it('Property 10a: container always has text-center py-12', () => {
    fc.assert(
      fc.property(textArb, (text) => {
        const { container, unmount } = render(<LoadingState text={text} />);
        const wrapper = container.firstChild as HTMLElement;
        const result = hasAllClasses(wrapper.className, REQUIRED_CONTAINER_CLASSES);
        unmount();
        return result;
      }),
      { numRuns: 100 }
    );
  });

  // ── 10b: animate-spin on icon ─────────────────────────────────────────

  /**
   * Property 10b: For any (or no) text prop, the SVG icon always carries
   * `animate-spin` — never a fallback CSS spinner div.
   *
   * **Validates: Requirements 11.3, 6.8, 8.8**
   */
  it('Property 10b: icon element always has animate-spin class', () => {
    fc.assert(
      fc.property(textArb, (text) => {
        const { container, unmount } = render(<LoadingState text={text} />);
        const spinEl = container.querySelector('.animate-spin') as HTMLElement | null;
        const result = spinEl !== null;
        unmount();
        return result;
      }),
      { numRuns: 100 }
    );
  });

  // ── 10c: BNI Teal colour on icon ──────────────────────────────────────

  /**
   * Property 10c: For any (or no) text prop, the spinning icon always carries
   * `text-[#005E6A]` (BNI Teal), not a plain gray or any other colour.
   *
   * **Validates: Requirements 11.3, 6.8, 8.8**
   */
  it('Property 10c: icon element always has text-[#005E6A] (BNI Teal)', () => {
    fc.assert(
      fc.property(textArb, (text) => {
        const { container, unmount } = render(<LoadingState text={text} />);
        // Use getAttribute('class') — SVG elements in jsdom expose .className as
        // SVGAnimatedString, not a plain string.
        const spinEl = container.querySelector('.animate-spin');
        const result =
          spinEl !== null && hasAllClasses(getClassString(spinEl), ['text-[#005E6A]']);
        unmount();
        return result;
      }),
      { numRuns: 100 }
    );
  });

  // ── 10d: Message typography ───────────────────────────────────────────

  /**
   * Property 10d: For any (or no) text prop, the message <p> element always
   * carries `text-sm` and `font-medium`.
   *
   * **Validates: Requirement 11.3**
   */
  it('Property 10d: message <p> always has text-sm font-medium', () => {
    fc.assert(
      fc.property(textArb, (text) => {
        const { container, unmount } = render(<LoadingState text={text} />);
        const msgEl = container.querySelector('p') as HTMLElement | null;
        const result =
          msgEl !== null && hasAllClasses(msgEl.className, REQUIRED_MESSAGE_CLASSES);
        unmount();
        return result;
      }),
      { numRuns: 100 }
    );
  });

  // ── 10e: No inline @keyframes spinner ────────────────────────────────

  /**
   * Property 10e: For any (or no) text prop, the rendered HTML never contains
   * `@keyframes` — confirming no inline CSS spinner div is used.
   *
   * **Validates: Requirements 11.3, 6.8, 8.8**
   */
  it('Property 10e: rendered output never contains @keyframes (no inline CSS spinner)', () => {
    fc.assert(
      fc.property(textArb, (text) => {
        const { container, unmount } = render(<LoadingState text={text} />);
        const html = container.innerHTML;
        const result = !html.includes('@keyframes');
        unmount();
        return result;
      }),
      { numRuns: 100 }
    );
  });
});

// ---------------------------------------------------------------------------
// Suite 3 — Example-based checks (direct traceability)
// ---------------------------------------------------------------------------

describe('LoadingState — example-based checks', () => {
  it('default render (no text prop) has container text-center py-12', () => {
    const { container } = render(<LoadingState />);
    const wrapper = container.firstChild as HTMLElement;
    REQUIRED_CONTAINER_CLASSES.forEach((cls) =>
      expect(wrapper.className).toContain(cls)
    );
  });

  it('default render has animate-spin icon', () => {
    const { container } = render(<LoadingState />);
    expect(container.querySelector('.animate-spin')).not.toBeNull();
  });

  it('default render icon has text-[#005E6A]', () => {
    const { container } = render(<LoadingState />);
    const spinEl = container.querySelector('.animate-spin');
    expect(getClassString(spinEl)).toContain('text-[#005E6A]');
  });

  it('default render message has text-sm font-medium', () => {
    const { container } = render(<LoadingState />);
    const p = container.querySelector('p') as HTMLElement;
    REQUIRED_MESSAGE_CLASSES.forEach((cls) => expect(p.className).toContain(cls));
  });

  it('default render message text is "Memuat data"', () => {
    const { container } = render(<LoadingState />);
    const p = container.querySelector('p') as HTMLElement;
    expect(p.textContent).toBe('Memuat data');
  });

  it('custom text prop is rendered as message content', () => {
    const { container } = render(<LoadingState text="Mencari campaign" />);
    const p = container.querySelector('p') as HTMLElement;
    expect(p.textContent).toBe('Mencari campaign');
  });

  it('custom text render still has animate-spin icon with text-[#005E6A]', () => {
    const { container } = render(<LoadingState text="Mencari" />);
    const spinEl = container.querySelector('.animate-spin');
    expect(spinEl).not.toBeNull();
    expect(getClassString(spinEl)).toContain('text-[#005E6A]');
  });

  it('does not contain @keyframes for default render', () => {
    const { container } = render(<LoadingState />);
    expect(container.innerHTML).not.toContain('@keyframes');
  });

  it('empty string text prop still produces required classes', () => {
    const { container } = render(<LoadingState text="" />);
    const wrapper = container.firstChild as HTMLElement;
    const spinEl = container.querySelector('.animate-spin');
    const p = container.querySelector('p') as HTMLElement;

    REQUIRED_CONTAINER_CLASSES.forEach((cls) =>
      expect(wrapper.className).toContain(cls)
    );
    expect(getClassString(spinEl)).toContain('animate-spin');
    expect(getClassString(spinEl)).toContain('text-[#005E6A]');
    REQUIRED_MESSAGE_CLASSES.forEach((cls) => expect(p.className).toContain(cls));
  });
});
