/**
 * FilterPanel — shared collapsible filter panel for all dashboard pages.
 *
 * Provides period date range, flag_program (product), jenis_leads (sub-product),
 * media_blasting (channel), and wilayah (region) filters.  Emits the current
 * FilterState to the parent via the `onFilterChange` callback when the user
 * presses Apply or Reset.
 *
 * Requirements: 1.3, 1.4, 1.5
 */

import React, { useState, useCallback } from 'react';
import { FilterState, FilterChangeHandler } from '../types/filters';
import './FilterPanel.css';

// ── Constants ────────────────────────────────────────────────────

const FLAG_PROGRAM_OPTIONS: string[] = [
  'PROGRAM BIAYA ADMIN',
  'PROGRAM QRIS',
];

const MEDIA_BLASTING_OPTIONS: string[] = [
  'wa',
  'digisales',
  'telesales',
  'email',
  'push notif',
  'sms',
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
    <fieldset className="filter-panel__fieldset">
      <legend className="filter-panel__legend">{legend}</legend>
      <div className="filter-panel__checkbox-grid">
        {options.map((opt) => {
          const id = getId(opt);
          const checked = (selected as (string | number)[]).includes(opt);
          return (
            <label key={id} htmlFor={id} className="filter-panel__checkbox-label">
              <input
                type="checkbox"
                id={id}
                className="filter-panel__checkbox"
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

  /** Parses the jenis_leads text input (comma-separated) into a string array. */
  const handleJenisCleadsChange = useCallback(
    (raw: string) => {
      const parsed = raw
        .split(',')
        .map((s) => s.trim())
        .filter((s) => s.length > 0);
      setFilters((prev) => ({ ...prev, jenisCleads: parsed }));
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

  // ── Derived display values ───────────────────────────────────

  /** Re-joins jenisCleads array for the controlled text input. */
  const jenisCleadsText = filters.jenisCleads.join(', ');

  // ── Render ───────────────────────────────────────────────────

  return (
    <aside className="filter-panel" aria-label="Filter Panel">
      {/* ── Header ─────────────────────────────────────────── */}
      <div className="filter-panel__header">
        <span className="filter-panel__title">Filter</span>
        <button
          type="button"
          className="filter-panel__toggle"
          aria-expanded={!isCollapsed}
          aria-controls="filter-panel-body"
          onClick={() => setIsCollapsed((c) => !c)}
        >
          {isCollapsed ? '▼ Expand' : '▲ Collapse'}
        </button>
      </div>

      {/* ── Body ───────────────────────────────────────────── */}
      {!isCollapsed && (
        <div id="filter-panel-body" className="filter-panel__body">

          {/* Period */}
          <fieldset className="filter-panel__fieldset">
            <legend className="filter-panel__legend">Periode</legend>
            <div className="filter-panel__date-row">
              <label
                htmlFor="filter-start-date"
                className="filter-panel__date-label"
              >
                Dari
              </label>
              <input
                type="date"
                id="filter-start-date"
                className="filter-panel__date-input"
                value={filters.dateRange.startDate}
                max={filters.dateRange.endDate}
                onChange={(e) => handleDateChange('startDate', e.target.value)}
              />
            </div>
            <div className="filter-panel__date-row">
              <label
                htmlFor="filter-end-date"
                className="filter-panel__date-label"
              >
                Sampai
              </label>
              <input
                type="date"
                id="filter-end-date"
                className="filter-panel__date-input"
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
          <fieldset className="filter-panel__fieldset">
            <legend className="filter-panel__legend">Jenis Leads (Sub-Produk)</legend>
            <label
              htmlFor="filter-jenis-leads"
              className="filter-panel__text-label"
            >
              Masukkan nilai, pisahkan dengan koma
            </label>
            <input
              type="text"
              id="filter-jenis-leads"
              className="filter-panel__text-input"
              placeholder="Contoh: Migrasi, Baru, Reaktivasi"
              value={jenisCleadsText}
              onChange={(e) => handleJenisCleadsChange(e.target.value)}
            />
          </fieldset>

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
          <div className="filter-panel__actions">
            <button
              type="button"
              className="filter-panel__btn filter-panel__btn--reset"
              onClick={handleReset}
            >
              Reset
            </button>
            <button
              type="button"
              className="filter-panel__btn filter-panel__btn--apply"
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
