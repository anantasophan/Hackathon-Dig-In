/**
 * DashboardLayout — Property-Based Tests
 *
 * Tests menggunakan fast-check + @testing-library/react untuk memverifikasi
 * properti-properti universal pada komponen DashboardLayout.
 *
 * Validates: Requirements 2.7, 2.8, 2.11
 */

import React from 'react';
import { render } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import * as fc from 'fast-check';
import DashboardLayout from '../DashboardLayout';

// ── Property 1: Active nav exclusivity ───────────────────────────
// Validates: Requirements 2.7, 2.8
describe('DashboardLayout — Property 1: Active nav item has exclusive active classes', () => {
  it('exactly one nav item has bg-[#005E6A] for any valid route', () => {
    fc.assert(
      fc.property(
        fc.constantFrom(
          '/overview',
          '/comparison',
          '/time-analysis',
          '/regional',
          '/customer-criteria',
          '/similar-campaigns'
        ),
        (route) => {
          const { container, unmount } = render(
            <MemoryRouter initialEntries={[route]}>
              <DashboardLayout>
                <div>test content</div>
              </DashboardLayout>
            </MemoryRouter>
          );

          // Find all nav link spans — active ones carry bg-[#005E6A]
          const navSpans = container.querySelectorAll('nav span');
          const activeItems = Array.from(navSpans).filter((el) =>
            el.className.includes('bg-[#005E6A]')
          );

          unmount();

          // Exactly one nav item should be active
          return activeItems.length === 1;
        }
      ),
      { numRuns: 6 } // one run per route is sufficient for constantFrom
    );
  });

  it('active nav item has text-white and font-semibold', () => {
    fc.assert(
      fc.property(
        fc.constantFrom(
          '/overview',
          '/comparison',
          '/time-analysis',
          '/regional',
          '/customer-criteria',
          '/similar-campaigns'
        ),
        (route) => {
          const { container, unmount } = render(
            <MemoryRouter initialEntries={[route]}>
              <DashboardLayout>
                <div>test content</div>
              </DashboardLayout>
            </MemoryRouter>
          );

          const navSpans = container.querySelectorAll('nav span');
          const activeItem = Array.from(navSpans).find((el) =>
            el.className.includes('bg-[#005E6A]')
          );

          unmount();

          if (!activeItem) return false;
          return (
            activeItem.className.includes('text-white') &&
            activeItem.className.includes('font-semibold')
          );
        }
      ),
      { numRuns: 6 }
    );
  });
});

// ── Property 2: No emoji in rendered output ───────────────────────
// Validates: Requirements 2.11
describe('DashboardLayout — Property 2: No emoji in rendered output', () => {
  // Emoji unicode ranges to check
  const EMOJI_REGEX = /[\u{1F300}-\u{1FFFF}\u{2600}-\u{27BF}]/u;

  it('renders no emoji for any username and route combination', () => {
    fc.assert(
      fc.property(
        fc.string({ maxLength: 50 }), // username
        fc.constantFrom(
          '/overview',
          '/comparison',
          '/time-analysis',
          '/regional',
          '/customer-criteria',
          '/similar-campaigns'
        ),
        (username, route) => {
          const { container, unmount } = render(
            <MemoryRouter initialEntries={[route]}>
              <DashboardLayout username={username}>
                <div>test content</div>
              </DashboardLayout>
            </MemoryRouter>
          );

          const textContent = container.textContent ?? '';
          const hasEmoji = EMOJI_REGEX.test(textContent);

          unmount();
          return !hasEmoji;
        }
      ),
      { numRuns: 20 }
    );
  });
});
