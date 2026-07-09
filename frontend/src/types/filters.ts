/**
 * filters.ts — Type definitions for the shared FilterPanel component.
 *
 * Defines FilterState, DateRange, and FilterChangeHandler used across
 * all dashboard pages that support campaign filtering.
 *
 * Requirements: 1.3, 1.4, 1.5
 */

/** An inclusive date range represented as ISO yyyy-mm-dd strings. */
export interface DateRange {
  startDate: string; // yyyy-mm-dd
  endDate: string;   // yyyy-mm-dd
}

/**
 * Complete filter state for campaign data queries.
 *
 * Field names mirror the backend domain model:
 *   flagProgram    → flag_program  (product type)
 *   jenisCleads    → jenis_leads   (leads purpose / sub-product, free text)
 *   mediaBlasting  → media_blasting (distribution channel)
 *   wilayah        → wilayah        (region code 1–17)
 */
export interface FilterState {
  dateRange: DateRange;
  /** Selected flag_program values. Valid: "PROGRAM BIAYA ADMIN" | "PROGRAM QRIS" */
  flagProgram: string[];
  /** Selected jenis_leads values — free-text, comma-separated entry by user. */
  jenisCleads: string[];
  /** Selected media_blasting channels. Valid: "wa" | "digisales" | "telesales" | "email" | "push notif" | "sms" */
  mediaBlasting: string[];
  /** Selected wilayah (region) codes 1–17. */
  wilayah: number[];
}

/** Callback type for filter change notifications emitted to parent pages. */
export type FilterChangeHandler = (filters: FilterState) => void;
