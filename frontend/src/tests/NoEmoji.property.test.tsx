/**
 * Property tests for the "No Emoji" invariant across shared state components.
 *
 * Property 2: No emoji in any rendered component output (all components)
 *
 * **Validates: Requirements 2.11, 3.8, 4.8, 5 (all pages), 11.2**
 *
 * Strategy:
 * - Full page components (CampaignOverviewPage, etc.) require heavy mocking
 *   of the `api` service, Chart.js, and react-router-dom — out of scope here.
 * - The shared state components (EmptyState, LoadingState, ErrorState) from
 *   StateComponents.tsx are self-contained with zero external dependencies,
 *   making them ideal targets to prove the invariant holds for any prop input.
 * - We render each component with property-based inputs (arbitrary strings)
 *   and assert that no emoji code points appear in the rendered textContent.
 *
 * Emoji detection:
 *   Unicode ranges U+1F300–U+1FFFF (Misc Symbols & Pictographs, Emoticons, etc.)
 *   and U+2600–U+27BF (Misc Symbols, Dingbats) are treated as emoji.
 *   The regex uses the `u` flag so that surrogate pairs are matched correctly.
 */

import React from 'react';
import { render } from '@testing-library/react';
import * as fc from 'fast-check';

import {
  EmptyState,
  LoadingState,
  ErrorState,
} from '../components/StateComponents';

// ---------------------------------------------------------------------------
// Emoji detection
// ---------------------------------------------------------------------------

/**
 * Regex that matches any character in the two main emoji Unicode ranges.
 * The `u` flag is REQUIRED so that code points above U+FFFF are matched
 * as single characters and not as surrogate pairs.
 */
const EMOJI_REGEX = /[\u{1F300}-\u{1FFFF}\u{2600}-\u{27BF}]/u;

/** Returns true when `text` contains at least one emoji character. */
function hasEmoji(text: string): boolean {
  return EMOJI_REGEX.test(text);
}

// ---------------------------------------------------------------------------
// Shared arbitraries
// ---------------------------------------------------------------------------

/**
 * Optional string: either an arbitrary string or undefined.
 * Mirrors the optional props on EmptyState (message, hint).
 */
const optionalStringArb = fc.option(fc.string(), { nil: undefined });

// ---------------------------------------------------------------------------
// Suite 1 — hasEmoji helper self-tests
// ---------------------------------------------------------------------------
// Verify that the detection helper itself is correctly calibrated before
// relying on it for the main property assertions.

describe('hasEmoji helper', () => {
  it('detects emoji characters in the two covered Unicode ranges', () => {
    // Range U+1F300–U+1FFFF: Misc Symbols & Pictographs, Emoticons, etc.
    expect(hasEmoji('Hello 🌍')).toBe(true);    // U+1F30D — Misc Symbols & Pictographs
    expect(hasEmoji('📥 download')).toBe(true); // U+1F4E5 — in range
    expect(hasEmoji('🔍 search')).toBe(true);   // U+1F50D — in range
    expect(hasEmoji('👥 users')).toBe(true);    // U+1F465 — in range

    // Range U+2600–U+27BF: Misc Symbols, Dingbats
    expect(hasEmoji('☀️ sun')).toBe(true);      // U+2600 — exactly at lower bound
    expect(hasEmoji('⚠️ warn')).toBe(true);     // U+26A0 — in range
    expect(hasEmoji('✈ plane')).toBe(true);     // U+2708 — in range

    // NOTE: ✅ (U+2705) and ⏳ (U+23F3) are outside both covered ranges,
    // so they are NOT detected by this regex. The regex covers the two ranges
    // explicitly called out in the design doc.
  });

  it('does NOT flag normal Latin/Indonesian text as emoji', () => {
    expect(hasEmoji('Tidak ada data tersedia')).toBe(false);
    expect(hasEmoji('Memuat data')).toBe(false);
    expect(hasEmoji('Terjadi kesalahan')).toBe(false);
    expect(hasEmoji('Silakan sesuaikan filter untuk menampilkan data')).toBe(false);
    expect(hasEmoji('')).toBe(false);
    expect(hasEmoji('Hello World!')).toBe(false);
  });

  it('does NOT flag SVG-rendered Lucide icon text content (empty strings)', () => {
    // Lucide icons render SVG elements; textContent of the SVG is empty.
    expect(hasEmoji('')).toBe(false);
  });
});

// ---------------------------------------------------------------------------
// Suite 2 — Property 2: EmptyState renders no emoji
// ---------------------------------------------------------------------------

describe('Property 2: No emoji in EmptyState for any message/hint', () => {
  /**
   * **Property 2a: EmptyState with arbitrary message and hint strings never
   * produces emoji in its rendered text content.**
   *
   * **Validates: Requirements 11.2**
   */
  it('renders no emoji for any message and hint combination', () => {
    fc.assert(
      fc.property(optionalStringArb, optionalStringArb, (message, hint) => {
        const { container, unmount } = render(
          <EmptyState message={message} hint={hint} />
        );

        const text = container.textContent ?? '';
        const result = !hasEmoji(text);

        unmount();
        return result;
      }),
      { numRuns: 200 }
    );
  });

  it('renders no emoji with default props (no message, no hint)', () => {
    const { container } = render(<EmptyState />);
    expect(hasEmoji(container.textContent ?? '')).toBe(false);
  });

  it('renders no emoji with explicit default-text props', () => {
    const { container } = render(
      <EmptyState
        message="Tidak ada data tersedia"
        hint="Silakan sesuaikan filter untuk menampilkan data"
      />
    );
    expect(hasEmoji(container.textContent ?? '')).toBe(false);
  });

  it('renders no emoji when message and hint are empty strings', () => {
    const { container } = render(<EmptyState message="" hint="" />);
    expect(hasEmoji(container.textContent ?? '')).toBe(false);
  });
});

// ---------------------------------------------------------------------------
// Suite 3 — Property 2: LoadingState renders no emoji
// ---------------------------------------------------------------------------

describe('Property 2: No emoji in LoadingState for any text', () => {
  /**
   * **Property 2b: LoadingState with an arbitrary `text` prop never produces
   * emoji in its rendered text content.**
   *
   * **Validates: Requirements 11.2, 11.3**
   */
  it('renders no emoji for any text prop value', () => {
    fc.assert(
      fc.property(optionalStringArb, (text) => {
        const { container, unmount } = render(
          <LoadingState text={text} />
        );

        const renderedText = container.textContent ?? '';
        const result = !hasEmoji(renderedText);

        unmount();
        return result;
      }),
      { numRuns: 200 }
    );
  });

  it('renders no emoji with default props (no text)', () => {
    const { container } = render(<LoadingState />);
    expect(hasEmoji(container.textContent ?? '')).toBe(false);
  });

  it('renders no emoji with the standard loading text', () => {
    const { container } = render(<LoadingState text="Memuat data" />);
    expect(hasEmoji(container.textContent ?? '')).toBe(false);
  });

  it('renders no emoji when text is an empty string', () => {
    const { container } = render(<LoadingState text="" />);
    expect(hasEmoji(container.textContent ?? '')).toBe(false);
  });
});

// ---------------------------------------------------------------------------
// Suite 4 — Property 2: ErrorState renders no emoji
// ---------------------------------------------------------------------------

describe('Property 2: No emoji in ErrorState for any message', () => {
  /**
   * **Property 2c: ErrorState with an arbitrary `message` prop never produces
   * emoji in its rendered text content.**
   *
   * **Validates: Requirements 11.2, 11.4**
   */
  it('renders no emoji for any message string', () => {
    fc.assert(
      fc.property(fc.string(), (message) => {
        const { container, unmount } = render(
          <ErrorState message={message} />
        );

        const text = container.textContent ?? '';
        const result = !hasEmoji(text);

        unmount();
        return result;
      }),
      { numRuns: 200 }
    );
  });

  it('renders no emoji with a typical error message', () => {
    const { container } = render(
      <ErrorState message="Terjadi kesalahan saat memuat data." />
    );
    expect(hasEmoji(container.textContent ?? '')).toBe(false);
  });

  it('renders no emoji when message is an empty string', () => {
    const { container } = render(<ErrorState message="" />);
    expect(hasEmoji(container.textContent ?? '')).toBe(false);
  });

  it('renders no emoji for the fixed heading "Terjadi kesalahan"', () => {
    const { container } = render(<ErrorState message="any error" />);
    // The component always renders "Terjadi kesalahan" as a heading — verify no emoji there
    const heading = container.querySelector('p.text-rose-600');
    expect(heading).not.toBeNull();
    expect(hasEmoji(heading?.textContent ?? '')).toBe(false);
  });
});

// ---------------------------------------------------------------------------
// Suite 5 — Cross-component: all three components together
// ---------------------------------------------------------------------------

describe('Property 2: No emoji across all shared state components', () => {
  /**
   * Render all three components simultaneously and assert none introduce emoji.
   * This guards against a scenario where one component is fine in isolation
   * but a combination triggers an unexpected code path.
   */
  it('renders no emoji from any of the three components when rendered together', () => {
    fc.assert(
      fc.property(
        optionalStringArb,                  // EmptyState.message
        optionalStringArb,                  // EmptyState.hint
        optionalStringArb,                  // LoadingState.text
        fc.string(),                        // ErrorState.message
        (emptyMsg, emptyHint, loadText, errMsg) => {
          const { container: c1, unmount: u1 } = render(
            <EmptyState message={emptyMsg} hint={emptyHint} />
          );
          const { container: c2, unmount: u2 } = render(
            <LoadingState text={loadText} />
          );
          const { container: c3, unmount: u3 } = render(
            <ErrorState message={errMsg} />
          );

          const combined =
            (c1.textContent ?? '') +
            (c2.textContent ?? '') +
            (c3.textContent ?? '');

          const result = !hasEmoji(combined);

          u1(); u2(); u3();
          return result;
        }
      ),
      { numRuns: 100 }
    );
  });
});
