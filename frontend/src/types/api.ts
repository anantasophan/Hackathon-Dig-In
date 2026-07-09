/**
 * api.ts — TypeScript interfaces for all Campaign Insight Generator
 * request and response types.
 *
 * Field names match the Python backend dataclasses in backend/shared/models.py
 * exactly — use snake_case as-is since the API serialises Python dataclasses
 * directly.
 *
 * Requirements: 7.1, 7.2
 */

// ---------------------------------------------------------------------------
// Shared / core
// ---------------------------------------------------------------------------

/**
 * An active filter that was applied to produce a response.
 * Maps to backend `ActiveFilter` dataclass.
 */
export interface ActiveFilter {
  field: string;
  values: string[];
}

// ---------------------------------------------------------------------------
// Campaign Overview
// ---------------------------------------------------------------------------

/** Maps to backend `CampaignOverviewRequest`. */
export interface CampaignOverviewRequest {
  start_date: string;                       // yyyy-mm-dd
  end_date: string;                         // yyyy-mm-dd
  flag_program?: string[];                  // Optional — "PROGRAM BIAYA ADMIN" | "PROGRAM QRIS"
  media_blasting?: string[];                // Optional — "wa" | "digisales" | etc.
  wilayah?: number[];                       // Optional — region codes 1–17
  jenis_leads?: string[];                   // Optional — leads purpose
}

/** A single point in the overview trend sparkline. Maps to `TrendDataPoint`. */
export interface TrendDataPoint {
  period_start: string;                     // yyyy-mm-dd
  period_end: string;                       // yyyy-mm-dd
  take_up_rate: number;                     // percentage 0–100
  total_leads: number;
  total_take_up: number;
}

/** Maps to backend `CampaignOverviewResponse`. */
export interface CampaignOverviewResponse {
  total_leads: number;
  total_take_up: number;
  take_up_rate: number;                     // percentage 0–100
  total_campaigns: number;
  trend: TrendDataPoint[];
  filters: ActiveFilter[];
}

// ---------------------------------------------------------------------------
// Campaign Comparison
// ---------------------------------------------------------------------------

/** Maps to backend `CampaignComparisonRequest`. */
export interface CampaignComparisonRequest {
  campaign_ids: string[];                   // 2–5 campaign IDs
  group_by?: 'flag_program' | 'wilayah' | 'media_blasting';
}

/** Per-campaign metrics row. Maps to backend `CampaignMetric`. */
export interface CampaignMetric {
  campaign_id: string;
  campaign_name: string;
  flag_program: string;
  total_leads: number;
  total_take_up: number;
  take_up_rate: number;                     // percentage 0–100
  total_transaction_value: number;
  duration_days: number;
}

/** Maps to backend `CampaignComparisonResponse`. */
export interface CampaignComparisonResponse {
  campaigns: CampaignMetric[];
  /** Chart.js-compatible data structure for frontend rendering. */
  comparison_chart: Record<string, unknown>;
}

// ---------------------------------------------------------------------------
// Time Analysis
// ---------------------------------------------------------------------------

/** A single bucket in the time-to-take-up histogram. */
export interface TimeHistogramBucket {
  range_start: number;                      // days (inclusive)
  range_end: number;                        // days (exclusive)
  count: number;
  percentage: number;                       // percentage 0–100
}

/** Descriptive statistics for time-to-take-up days. */
export interface TimeAnalysisStats {
  min_days: number;
  max_days: number;
  mean_days: number;
  median_days: number;
  total_take_up: number;
}

/** Response for GET /api/campaigns/time-analysis/{id}. */
export interface TimeAnalysisResponse {
  campaign_id: string;
  campaign_name: string;
  histogram: TimeHistogramBucket[];
  stats: TimeAnalysisStats;
  /** Optional breakdown by channel (media_blasting) when channel param provided. */
  channel_breakdown?: Record<string, TimeAnalysisStats>;
  /** Optional breakdown by region (wilayah) when region param provided. */
  regional_breakdown?: Record<string, TimeAnalysisStats>;
}

// ---------------------------------------------------------------------------
// Regional Performance
// ---------------------------------------------------------------------------

/** Per-region metrics for a single period. */
export interface RegionMetric {
  wilayah: number;                          // region code 1–17
  region_name: string;
  total_leads: number;
  total_take_up: number;
  take_up_rate: number;                     // percentage 0–100
  avg_transaction_value: number;
}

/** One week of regional trend data. */
export interface RegionalTrendPoint {
  week_start: string;                       // yyyy-mm-dd
  wilayah: number;
  take_up_rate: number;
}

/** Response for GET /api/campaigns/regional/{id}. */
export interface RegionalPerformanceResponse {
  campaign_id: string;
  campaign_name: string;
  /** Regions sorted by take_up_rate descending (Property 7). */
  regions: RegionMetric[];
  /** 8-week trend per region for sparklines. */
  trend: RegionalTrendPoint[];
  flag_program?: string;
}

// ---------------------------------------------------------------------------
// Customer Criteria
// ---------------------------------------------------------------------------

/** A single group in a percentage distribution breakdown. */
export interface DistributionItem {
  label: string;
  count: number;
  percentage: number;                       // percentage 0–100; all groups sum to 100 ±0.01
  take_up_count: number;
  take_up_percentage: number;              // take-up rate for this group
}

/** Distribution breakdown for one customer attribute. */
export interface AttributeDistribution {
  attribute: string;                        // e.g. "customer_segment", "age_group"
  /** Whether data is available for this attribute. */
  available: boolean;
  items: DistributionItem[];
  /** Human-readable reason when available is false. */
  unavailable_reason: string | null;
}

/** Response for GET /api/campaigns/customer-criteria/{id}. */
export interface CustomerCriteriaResponse {
  campaign_id: string;
  campaign_name?: string;
  /** One distribution per customer attribute (segment, age group, etc.). */
  distributions: AttributeDistribution[];
  available_attributes?: string[];
  unavailable_attributes?: string[];
  /** Present when some attributes have no data. */
  partial_data_message?: string;
}

// ---------------------------------------------------------------------------
// Similar Campaigns
// ---------------------------------------------------------------------------

/** Maps to backend `SimilarCampaignRequest`. */
export interface SimilarCampaignRequest {
  reference_campaign_id: string;
  dimensions: Array<'media_blasting' | 'jenis_leads' | 'flag_program'>;
  limit?: number;                           // default 20, max 20
}

/** Maps to backend `SimilarCampaignResult`. */
export interface SimilarCampaignResult {
  campaign_id: string;
  campaign_name: string;
  matching_dimensions: string[];
  dimension_count: number;
  similarity_score: number;                 // 0.0–1.0
  take_up_rate: number;                     // percentage 0–100
  total_leads: number;
  total_take_up: number;
}

/** Maps to backend `SimilarCampaignResponse`. */
export interface SimilarCampaignResponse {
  similar_campaigns: SimilarCampaignResult[];
}

// ---------------------------------------------------------------------------
// Export
// ---------------------------------------------------------------------------

/** Maps to backend `ExportRequest`. */
export interface ExportRequest {
  page: string;
  format: 'pdf' | 'excel' | 'csv';
  filters: ActiveFilter[];
  time_range_start: string;                 // yyyy-mm-dd
  time_range_end: string;                   // yyyy-mm-dd
}

/** Maps to backend `ExportResponse`. */
export interface ExportResponse {
  status: 'completed' | 'timeout' | 'error';
  download_url?: string;
  error_message?: string;
}

// ---------------------------------------------------------------------------
// Auth / Session
// ---------------------------------------------------------------------------

/** Response for GET /api/auth/session. */
export interface SessionResponse {
  user_id: string;
  username: string;
  role: 'divisi_bisnis' | 'divisi_data';
  session_id: string;
  /** ISO 8601 login timestamp. */
  login_timestamp: string;
  /** Epoch seconds — login_timestamp + 28,800 s (8 hours). */
  expiry_timestamp: number;
}
