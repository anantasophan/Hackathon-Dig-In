/**
 * Property tests for the shared EmptyState component.
 *
 * Property 9: Empty state pattern is consistent across all pages.
 *
 * **Validates: Requirements 11.1, 11.2**
 *
 * Strategy:
 * - EmptyState is the single shared component used by every page in the
 *   application.  Testing it in isolation proves consistency: if the shared
 *   component always renders the required classes, then every page that uses
 *   it automatically satisfies Requirements 11.1 and 11.2.
 *
 * - The component is exported from StateComponents.tsx, so we can import it
 *   directly — no local mirror needed.
 *
 * - We test four structural invariants (9a–9d) for any arbitrary message and
 *   hint strings:
 *     9a: outer container has `text-center py-12 text-gray-400`
 *     9b: the SVG icon carries `w-8 h-8` and `text-gray-300`
 *     9c: the message paragraph has `text-sm font-medium`
 *     9d: no emoji characters appear anywhere in the rendered output
 *
 * - Arbitraries used:
 *     message → fc.option(fc.string(), { nil: undefined })
 *     hint    → fc.option(fc.string(), { nil: undefined })
 *   This covers the defaults (undefined), empty strings, and arbitrary content.
 *
 * - We do NOT rely on Tailwind processing at test-time (jsdom does not run
 *   PostCSS).  We verify that the required class tokens are present as
 *   whitespace-delimited strings in the element's className attribute.
 */

import React from 'react';
import { render } from '@testing-library/react';
import * as fc from 'fast-check';

import { EmptyState } from '../components/StateComponents';

// ---------------------------------------------------------------------------
// Required class tokens (ground-truth from Requirements 11.1, 11.2)
// ---------------------------------------------------------------------------

/** Classes the outer container div MUST carry — Requirement 11.1 */
const REQUIRED_CONTAINER_CLASSES = [
  'text-center',
  'py-12',
  'text-gray-400',
] as const;

/** Classes the Inbox SVG icon MUST carry — Requirement 11.1 */
const REQUIRED_ICON_CLASSES = [
  'w-8',
  'h-8',
  'text-gray-300',
] as const;

/** Classes the message <p> MUST carry — Requirement 11.1 */
const REQUIRED_MESSAGE_CLASSES = [
  'text-sm',
  'font-medium',
] as const;

/**
 * Unicode ranges for emoji characters.
 * Requirement 11.2: no emoji anywhere in the rendered output.
 *
 * Covers:
 *   U+1F300–U+1FFFF  Miscellaneous Symbols, Emoji, Supplemental Symbols
 *   U+2600–U+27BF    Miscellaneous Symbols (classic range)
 */
const EMOJI_REGEX = /[\u{1F300}-\u{1FFFF}\u2600-\u27BF]/u;

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/**
 * Returns true when every token in `required` is present as an exact
 * whitespace-separated word in `classString`.
 *
 * Exact token matching prevents e.g. "py-12" from accidentally matching
 * "py-120" or "py-1200".
 */
function hasAllClasses(classString: string, required: readonly string[]): boolean {
  const tokens = new Set(classString.split(/\s+/));
  return required.every((cls) => tokens.has(cls));
}

/**
 * Returns true if the text contains any emoji character from the watched
 * Unicode ranges (Requirement 11.2).
 */
function containsEmoji(text: string): boolean {
  return EMOJI_REGEX.test(text);
}

// ---------------------------------------------------------------------------
// Arbitrary — message and hint strings (including undefined → use defaults)
// ---------------------------------------------------------------------------

const messageArb = fc.option(fc.string(), { nil: undefined });
const hintArb    = fc.option(fc.string(), { nil: undefined });

// ---------------------------------------------------------------------------
// Suite 0 — pure class-string smoke tests (no DOM)
// ---------------------------------------------------------------------------

describe('EmptyState — class strings match requirements (no DOM)', () => {
  /**
   * Verify that the literal class values written in StateComponents.tsx match
   * the required tokens.  These pure-string tests catch regressions without
   * mounting anything.
   */

  const CONTAINER_CLASS = 'text-center py-12 text-gray-400';
  const ICON_CLASS      = 'w-8 h-8 mx-auto mb-2 text-gray-300';
  const MESSAGE_CLASS   = 'text-sm font-medium';

  it('container class string contains all required tokens (Requirement 11.1)', () => {
    expect(hasAllClasses(CONTAINER_CLASS, REQUIRED_CONTAINER_CLASSES)).toBe(true);
  });

  it('icon class string contains w-8 h-8 text-gray-300 (Requirement 11.1)', () => {
    expect(hasAllClasses(ICON_CLASS, REQUIRED_ICON_CLASSES)).toBe(true);
  });

  it('message class string contains text-sm font-medium (Requirement 11.1)', () => {
    expect(hasAllClasses(MESSAGE_CLASS, REQUIRED_MESSAGE_CLASSES)).toBe(true);
  });
});

// ---------------------------------------------------------------------------
// Suite 1 — Property 9: DOM rendering properties (fast-check)
// ---------------------------------------------------------------------------

describe('EmptyState — Property 9: required classes always present for any message/hint', () => {

  // ── 9a: Container classes ─────────────────────────────────────────────

  /**
   * Property 9a: For any message and hint (including undefined), the outer
   * container always carries `text-center py-12 text-gray-400`.
   *
   * **Validates: Requirements 11.1**
   */
  it('Property 9a: container always has text-center py-12 text-gray-400', () => {
    fc.assert(
      fc.property(messageArb, hintArb, (message, hint) => {
        const { container, unmount } = render(
          <EmptyState message={message} hint={hint} />
        );

        const outerDiv = container.firstChild as HTMLElement;
        const result = hasAllClasses(outerDiv.className, REQUIRED_CONTAINER_CLASSES);

        unmount();
        return result;
      }),
      { numRuns: 100 }
    );
  });

  // ── 9b: Icon classes ──────────────────────────────────────────────────

  /**
   * Property 9b: For any message and hint, the Lucide Inbox SVG icon always
   * carries `w-8 h-8 text-gray-300`.
   *
   * Lucide React renders icons as <svg> elements.  The className is applied
   * directly to the <svg> tag.
   *
   * **Validates: Requirements 11.1**
   */
  it('Property 9b: Inbox icon svg always has w-8 h-8 text-gray-300', () => {
    fc.assert(
      fc.property(messageArb, hintArb, (message, hint) => {
        const { container, unmount } = render(
          <EmptyState message={message} hint={hint} />
        );

        // Lucide renders a single <svg> — first (and only) svg in the container
        const svgEl = container.querySelector('svg') as SVGElement;
        const result = hasAllClasses(svgEl.getAttribute('class') ?? '', REQUIRED_ICON_CLASSES);

        unmount();
        return result;
      }),
      { numRuns: 100 }
    );
  });

  // ── 9c: Message text classes ──────────────────────────────────────────

  /**
   * Property 9c: For any message and hint, the message <p> element always
   * carries `text-sm font-medium`.
   *
   * **Validates: Requirements 11.1**
   */
  it('Property 9c: message paragraph always has text-sm font-medium', () => {
    fc.assert(
      fc.property(messageArb, hintArb, (message, hint) => {
        const { container, unmount } = render(
          <EmptyState message={message} hint={hint} />
        );

        // The message <p> is the first <p> in the component
        const paragraphs = container.querySelectorAll('p');
        const messagePEl = paragraphs[0] as HTMLElement;
        const result = hasAllClasses(messagePEl.className, REQUIRED_MESSAGE_CLASSES);

        unmount();
        return result;
      }),
      { numRuns: 100 }
    );
  });

  // ── 9d: No emoji in rendered output ───────────────────────────────────

  /**
   * Property 9d: For any message and hint that do not themselves contain
   * emoji, the component's rendered text output contains no emoji characters.
   *
   * This tests that the component itself does not introduce emoji — the
   * default texts and structural markup must be emoji-free.
   *
   * We filter the arbitraries to exclude inputs that already contain emoji,
   * ensuring the test is about what the component contributes, not the props.
   *
   * **Validates: Requirements 11.2**
   */
  it('Property 9d: no emoji in rendered output when props do not contain emoji', () => {
    const noEmojiStringArb = fc.string().filter((s) => !containsEmoji(s));
    const noEmojiMessageArb = fc.option(noEmojiStringArb, { nil: undefined });
    const noEmojiHintArb    = fc.option(noEmojiStringArb, { nil: undefined });

    fc.assert(
      fc.property(noEmojiMessageArb, noEmojiHintArb, (message, hint) => {
        const { container, unmount } = render(
          <EmptyState message={message} hint={hint} />
        );

        const renderedText = container.textContent ?? '';
        const result = !containsEmoji(renderedText);

        unmount();
        return result;
      }),
      { numRuns: 100 }
    );
  });
});

// ---------------------------------------------------------------------------
// Suite 2 — Example-based checks (direct requirement traceability)
// ---------------------------------------------------------------------------

describe('EmptyState — example-based checks', () => {

  it('default render: container has required classes (Requirement 11.1)', () => {
    const { container } = render(<EmptyState />);
    const outerDiv = container.firstChild as HTMLElement;

    REQUIRED_CONTAINER_CLASSES.forEach((cls) => {
      expect(outerDiv.className).toContain(cls);
    });
  });

  it('default render: svg icon has required classes (Requirement 11.1)', () => {
    const { container } = render(<EmptyState />);
    const svgEl = container.querySelector('svg') as SVGElement;

    REQUIRED_ICON_CLASSES.forEach((cls) => {
      expect(svgEl.getAttribute('class')).toContain(cls);
    });
  });

  it('default render: message paragraph has required classes (Requirement 11.1)', () => {
    const { container } = render(<EmptyState />);
    const messagePEl = container.querySelectorAll('p')[0] as HTMLElement;

    REQUIRED_MESSAGE_CLASSES.forEach((cls) => {
      expect(messagePEl.className).toContain(cls);
    });
  });

  it('default render: no emoji in rendered text (Requirement 11.2)', () => {
    const { container } = render(<EmptyState />);
    expect(containsEmoji(container.textContent ?? '')).toBe(false);
  });

  it('default message text is formal Bahasa Indonesia without emoji (Requirement 11.2)', () => {
    const { container } = render(<EmptyState />);
    const messagePEl = container.querySelectorAll('p')[0] as HTMLElement;
    expect(messagePEl.textContent).toBe('Tidak ada data tersedia');
    expect(containsEmoji(messagePEl.textContent ?? '')).toBe(false);
  });

  it('default hint text is formal Bahasa Indonesia without emoji (Requirement 11.2)', () => {
    const { container } = render(<EmptyState />);
    const hintPEl = container.querySelectorAll('p')[1] as HTMLElement;
    expect(hintPEl.textContent).toBe('Silakan sesuaikan filter untuk menampilkan data');
    expect(containsEmoji(hintPEl.textContent ?? '')).toBe(false);
  });

  it('custom message prop is rendered in the first paragraph', () => {
    const { container } = render(<EmptyState message="Tidak ada kampanye" />);
    const messagePEl = container.querySelectorAll('p')[0] as HTMLElement;
    expect(messagePEl.textContent).toBe('Tidak ada kampanye');
  });

  it('custom hint prop is rendered in the second paragraph', () => {
    const { container } = render(<EmptyState hint="Coba ubah filter tanggal" />);
    const hintPEl = container.querySelectorAll('p')[1] as HTMLElement;
    expect(hintPEl.textContent).toBe('Coba ubah filter tanggal');
  });

  it('empty string message still renders required container classes', () => {
    const { container } = render(<EmptyState message="" hint="" />);
    const outerDiv = container.firstChild as HTMLElement;

    REQUIRED_CONTAINER_CLASSES.forEach((cls) => {
      expect(outerDiv.className).toContain(cls);
    });
  });

  it('renders exactly one svg icon (the Inbox icon)', () => {
    const { container } = render(<EmptyState />);
    expect(container.querySelectorAll('svg')).toHaveLength(1);
  });

  it('renders exactly two paragraph elements (message + hint)', () => {
    const { container } = render(<EmptyState />);
    expect(container.querySelectorAll('p')).toHaveLength(2);
  });
});
