/**
 * FilterPanel — shared collapsible filter panel for all dashboard pages.
 *
 * Provides period date range, flag_program (product), jenis_leads (sub-product),
 * media_blasting (channel), and wilayah (region) filters.  Emits the current
 * FilterState to the parent via the `onFilterChange` callback when the user
 * presses Apply or Reset.
 *
 * Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8
 */

import React, { useState, useCallback } from 'react';
import { ChevronDown, ChevronUp } from 'lucide-react';
import { FilterState, FilterChangeHandler } from '../types/filters';

// ── Constants ────────────────────────────────────────────────────

/** All flag_program values actually present in the current dataset (C001-C009). */
const FLAG_PROGRAM_OPTIONS: string[] = [
  'PROGRAM QRIS',
  'PROGRAM BIAYA ADMIN',
  'PROGRAM TAPENAS',
  'PROGRAM LIFEGOALS',
];

/** All media_blasting values actually present in the current dataset. */
const MEDIA_BLASTING_OPTIONS: string[] = [
  'wa',
  'telesales',
  'email',
  'digisales',
];

/**
 * All jenis_leads values actually present in the current dataset.
 * Free-text entry was replaced with a fixed checkbox list because the
 * backend match is case-insensitive but still exact — letting users type
 * arbitrary text made it easy to enter values that silently matched
 * nothing (e.g. "Migrasi" alone does not match "MIGRASI BAU").
 */
const JENIS_LEADS_OPTIONS: string[] = [
  'MIGRASI BAU',
  'MIGRASI BAU 2',
  'MIGRASI - TAMBAH 87K',
  'MIGRASI - CASHOUT',
  'MIGRASI - BO',
  'Balrun - Affluent',
  'Balrun- Payroll',
  'Balrun- BO',
  'Lifegoals - Balrun Payroll',
  'Akuisisi',
  'Migrasi',
  'Retensi',
];

/** Region codes 1–17, displayed as "Wilayah N". */
const WILAYAH_OPTIONS: number[] = Array.from({ length: 17 }, (_, i) => i + 1);

// ── Helpers ──────────────────────────────────────────────────────

/** Returns an ISO yyyy-mm-dd string for a given Date object. */
function toISODate(date: Date): string {
  return date.toISOString().slice(0, 10);
}

/** Computes the default filter state: 3 months ago → today. */
function buildDefaultFilters(): FilterState {
  const today = new Date();
  const threeMonthsAgo = new Date(today);
  threeMonthsAgo.setMonth(threeMonthsAgo.getMonth() - 3);

  return {
    dateRange: {
      startDate: toISODate(threeMonthsAgo),
      endDate: toISODate(today),
    },
    flagProgram: [],
    jenisCleads: [],
    mediaBlasting: [],
    wilayah: [],
  };
}

/** Merges optional partial initial filters over the computed defaults. */
function resolveInitialFilters(
  initial: Partial<FilterState> | undefined
): FilterState {
  const defaults = buildDefaultFilters();
  if (!initial) return defaults;
  return {
    dateRange: initial.dateRange ?? defaults.dateRange,
    flagProgram: initial.flagProgram ?? defaults.flagProgram,
    jenisCleads: initial.jenisCleads ?? defaults.jenisCleads,
    mediaBlasting: initial.mediaBlasting ?? defaults.mediaBlasting,
    wilayah: initial.wilayah ?? defaults.wilayah,
  };
}

// ── Types ────────────────────────────────────────────────────────

interface FilterPanelProps {
  /** Called when the user clicks Apply or Reset. */
  onFilterChange: FilterChangeHandler;
  /** Optional partial initial filter values; defaults are computed for missing fields. */
  initialFilters?: Partial<FilterState>;
}

// ── Sub-components ────────────────────────────────────────────────

interface CheckboxGroupProps<T extends string | number> {
  legend: string;
  options: T[];
  selected: T[];
  getLabel: (value: T) => string;
  getId: (value: T) => string;
  onChange: (value: T, checked: boolean) => void;
}

function CheckboxGroup<T extends string | number>({
  legend,
  options,
  selected,
  getLabel,
  getId,
  onChange,
}: CheckboxGroupProps<T>): React.ReactElement {
  return (
    <fieldset className="space-y-2">
      <legend className="text-xs font-bold uppercase tracking-wider text-gray-600 mb-2">
        {legend}
      </legend>
      <div className="grid grid-cols-2 gap-1.5">
        {options.map((opt) => {
          const id = getId(opt);
          const checked = (selected as (string | number)[]).includes(opt);
          return (
            <label key={id} htmlFor={id} className="flex items-center gap-2 text-xs text-gray-700 cursor-pointer">
              <input
                type="checkbox"
                id={id}
                className="rounded border-gray-300 text-[#005E6A] focus:ring-[#005E6A]"
                checked={checked}
                onChange={(e) => onChange(opt, e.target.checked)}
              />
              {getLabel(opt)}
            </label>
          );
        })}
      </div>
    </fieldset>
  );
}

// ── Main component ────────────────────────────────────────────────

const FilterPanel: React.FC<FilterPanelProps> = ({
  onFilterChange,
  initialFilters,
}) => {
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [filters, setFilters] = useState<FilterState>(() =>
    resolveInitialFilters(initialFilters)
  );

  // ── Handlers ─────────────────────────────────────────────────

  const handleDateChange = useCallback(
    (field: 'startDate' | 'endDate', value: string) => {
      setFilters((prev) => ({
        ...prev,
        dateRange: { ...prev.dateRange, [field]: value },
      }));
    },
    []
  );

  const handleFlagProgramChange = useCallback(
    (value: string, checked: boolean) => {
      setFilters((prev) => ({
        ...prev,
        flagProgram: checked
          ? [...prev.flagProgram, value]
          : prev.flagProgram.filter((v) => v !== value),
      }));
    },
    []
  );

  const handleMediaBlastingChange = useCallback(
    (value: string, checked: boolean) => {
      setFilters((prev) => ({
        ...prev,
        mediaBlasting: checked
          ? [...prev.mediaBlasting, value]
          : prev.mediaBlasting.filter((v) => v !== value),
      }));
    },
    []
  );

  const handleWilayahChange = useCallback(
    (value: number, checked: boolean) => {
      setFilters((prev) => ({
        ...prev,
        wilayah: checked
          ? [...prev.wilayah, value]
          : prev.wilayah.filter((v) => v !== value),
      }));
    },
    []
  );

  const handleJenisCleadsChange = useCallback(
    (value: string, checked: boolean) => {
      setFilters((prev) => ({
        ...prev,
        jenisCleads: checked
          ? [...prev.jenisCleads, value]
          : prev.jenisCleads.filter((v) => v !== value),
      }));
    },
    []
  );

  const handleApply = useCallback(() => {
    onFilterChange(filters);
  }, [filters, onFilterChange]);

  const handleReset = useCallback(() => {
    const defaultFilters = buildDefaultFilters();
    setFilters(defaultFilters);
    onFilterChange(defaultFilters);
  }, [onFilterChange]);

  // ── Render ───────────────────────────────────────────────────

  return (
    <aside className="bg-white border border-gray-200 rounded-xl shadow-sm" aria-label="Filter Panel">
      {/* ── Header ─────────────────────────────────────────── */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100">
        <span className="text-xs font-bold uppercase tracking-wider text-gray-600">Filter</span>
        <button
          type="button"
          className="flex items-center gap-1 text-xs text-gray-500 hover:text-gray-700"
          aria-expanded={!isCollapsed}
          aria-controls="filter-panel-body"
          onClick={() => setIsCollapsed((c) => !c)}
        >
          {isCollapsed ? (
            <><ChevronDown className="w-4 h-4" /><span>Expand</span></>
          ) : (
            <><ChevronUp className="w-4 h-4" /><span>Collapse</span></>
          )}
        </button>
      </div>

      {/* ── Body ───────────────────────────────────────────── */}
      {!isCollapsed && (
        <div id="filter-panel-body" className="p-4 space-y-4">

          {/* Period */}
          <fieldset className="space-y-2">
            <legend className="text-xs font-bold uppercase tracking-wider text-gray-600 mb-2">Periode</legend>
            <div className="flex flex-col gap-1">
              <label
                htmlFor="filter-start-date"
                className="text-xs text-gray-600 font-medium"
              >
                Dari
              </label>
              <input
                type="date"
                id="filter-start-date"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#005E6A] bg-white text-xs"
                value={filters.dateRange.startDate}
                max={filters.dateRange.endDate}
                onChange={(e) => handleDateChange('startDate', e.target.value)}
              />
            </div>
            <div className="flex flex-col gap-1">
              <label
                htmlFor="filter-end-date"
                className="text-xs text-gray-600 font-medium"
              >
                Sampai
              </label>
              <input
                type="date"
                id="filter-end-date"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#005E6A] bg-white text-xs"
                value={filters.dateRange.endDate}
                min={filters.dateRange.startDate}
                onChange={(e) => handleDateChange('endDate', e.target.value)}
              />
            </div>
          </fieldset>

          {/* Flag Program */}
          <CheckboxGroup<string>
            legend="Flag Program (Produk)"
            options={FLAG_PROGRAM_OPTIONS}
            selected={filters.flagProgram}
            getLabel={(v) => v}
            getId={(v) => `filter-fp-${v.replace(/\s+/g, '-').toLowerCase()}`}
            onChange={handleFlagProgramChange}
          />

          {/* Jenis Leads */}
          <CheckboxGroup<string>
            legend="Jenis Leads (Sub-Produk)"
            options={JENIS_LEADS_OPTIONS}
            selected={filters.jenisCleads}
            getLabel={(v) => v}
            getId={(v) => `filter-jl-${v.replace(/\s+/g, '-').toLowerCase()}`}
            onChange={handleJenisCleadsChange}
          />

          {/* Media Blasting */}
          <CheckboxGroup<string>
            legend="Media Blasting (Channel)"
            options={MEDIA_BLASTING_OPTIONS}
            selected={filters.mediaBlasting}
            getLabel={(v) => v}
            getId={(v) => `filter-mb-${v.replace(/\s+/g, '-').toLowerCase()}`}
            onChange={handleMediaBlastingChange}
          />

          {/* Wilayah */}
          <CheckboxGroup<number>
            legend="Wilayah (Region)"
            options={WILAYAH_OPTIONS}
            selected={filters.wilayah}
            getLabel={(v) => `Wilayah ${v}`}
            getId={(v) => `filter-wil-${v}`}
            onChange={handleWilayahChange}
          />

          {/* Action buttons */}
          <div className="flex gap-2 pt-2">
            <button
              type="button"
              className="flex-1 px-4 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 font-semibold rounded-lg text-xs transition-colors"
              onClick={handleReset}
            >
              Reset
            </button>
            <button
              type="button"
              className="flex-1 px-4 py-2 bg-[#005E6A] hover:bg-[#004852] text-white font-semibold rounded-lg text-xs transition-colors"
              onClick={handleApply}
            >
              Apply
            </button>
          </div>
        </div>
      )}
    </aside>
  );
};

export default FilterPanel;
