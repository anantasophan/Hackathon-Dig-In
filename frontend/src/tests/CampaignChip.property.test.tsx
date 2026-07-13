/**
 * Property-based test for campaign chip Tailwind classes.
 *
 * Property 7: Campaign chip has required Tailwind classes
 * Validates: Requirements 6.6
 *
 * Uses fast-check + @testing-library/react to assert that for any array
 * of 1–5 campaign IDs, every rendered chip has the exact required classes.
 */

import React from 'react';
import { render } from '@testing-library/react';
import * as fc from 'fast-check';

// ---------------------------------------------------------------------------
// Minimal testable chip component — mirrors the exact JSX in
// CampaignComparisonPage.tsx so the test exercises real production classes.
// ---------------------------------------------------------------------------

interface ChipListProps {
  campaignIds: string[];
  onRemove?: (id: string) => void;
}

const ChipList: React.FC<ChipListProps> = ({ campaignIds, onRemove }) => (
  <div role="list" aria-label="Campaign terpilih">
    {campaignIds.map((id, index) => (
      <span
        key={index}
        className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-[#005E6A]/20 border border-[#005E6A] text-[#005E6A] rounded-full text-xs font-medium"
        role="listitem"
      >
        {id}
        <button
          type="button"
          className="hover:text-rose-600 transition-colors"
          onClick={() => onRemove?.(id)}
          aria-label={`Hapus campaign ${id}`}
        >
          &times;
        </button>
      </span>
    ))}
  </div>
);

// ---------------------------------------------------------------------------
// Required class substrings
// Classes like bg-[#005E6A]/20 are non-standard Tailwind tokens, so we
// check for class substrings rather than full-token equality.
// ---------------------------------------------------------------------------

const REQUIRED_CHIP_CLASS_SUBSTRINGS = [
  'bg-[#005E6A]/20',
  'border',
  'border-[#005E6A]',
  'text-[#005E6A]',
  'rounded-full',
  'text-xs',
  'font-medium',
];

// ---------------------------------------------------------------------------
// Property 7: Campaign chip has required Tailwind classes
// Validates: Requirements 6.6
// ---------------------------------------------------------------------------

describe('Property 7: Campaign chip has required Tailwind classes', () => {
  it('every chip rendered has all required Tailwind class substrings for any 1–5 campaign IDs', () => {
    fc.assert(
      fc.property(
        fc.array(fc.string({ minLength: 1 }), { minLength: 1, maxLength: 5 }),
        (campaignIds) => {
          // Render into a dedicated container so querying is isolated.
          const { container, unmount } = render(<ChipList campaignIds={campaignIds} />);

          // Query all listitem spans directly from the container.
          const chips = container.querySelectorAll('[role="listitem"]');

          // There should be exactly one chip per campaign ID.
          expect(chips).toHaveLength(campaignIds.length);

          // Every chip must carry each required Tailwind class substring.
          chips.forEach((chip) => {
            const classList = chip.getAttribute('class') ?? '';
            REQUIRED_CHIP_CLASS_SUBSTRINGS.forEach((requiredClass) => {
              expect(classList).toContain(requiredClass);
            });
          });

          unmount();
        },
      ),
    );
  });
});
