/**
 * api.ts — Axios-based API service for the Campaign Insight Generator.
 *
 * Provides:
 *  - An Axios instance that attaches the Cognito JWT id-token to every
 *    outbound request via a request interceptor.
 *  - A response interceptor that maps HTTP error codes to typed Error
 *    subclasses so callers can branch on error kind without inspecting
 *    raw HTTP status codes.
 *  - Named API functions for all eight backend endpoints.
 *
 * Requirements: 7.1, 7.2
 */

import axios, { AxiosError, AxiosInstance } from 'axios';
import { fetchAuthSession } from 'aws-amplify/auth';

import type {
  CampaignOverviewRequest,
  CampaignOverviewResponse,
  CampaignComparisonRequest,
  CampaignComparisonResponse,
  TimeAnalysisResponse,
  RegionalPerformanceResponse,
  CustomerCriteriaResponse,
  SimilarCampaignRequest,
  SimilarCampaignResponse,
  ExportRequest,
  ExportResponse,
  SessionResponse,
} from '../types/api';

// ---------------------------------------------------------------------------
// Configuration
// ---------------------------------------------------------------------------

/**
 * Base URL for the API Gateway.  Must be set via REACT_APP_API_GATEWAY_URL
 * in the environment (e.g. .env.production).
 */
const BASE_URL = process.env['REACT_APP_API_GATEWAY_URL'] ?? '';

/**
 * Client-side timeout: 35 000 ms — slightly above the backend's 30-second
 * Athena query timeout so the backend always responds before the client
 * cancels, ensuring the 408 response is surfaced rather than swallowed.
 */
const CLIENT_TIMEOUT_MS = 35_000;

// ---------------------------------------------------------------------------
// Typed error classes
// ---------------------------------------------------------------------------

/**
 * Thrown when the backend returns 408 (query timeout).
 * The caller should offer a "Retry" action to the user.
 */
export class ApiTimeoutError extends Error {
  constructor(message = 'Query timed out — please try again.') {
    super(message);
    this.name = 'ApiTimeoutError';
  }
}

/**
 * Thrown when the backend returns 429 (rate limited).
 * `retryAfter` is the number of seconds to wait before retrying,
 * taken from the `Retry-After` response header (default 60 s).
 */
export class ApiRateLimitError extends Error {
  constructor(
    public readonly retryAfter: number,
    message = 'Too many requests — please wait before retrying.',
  ) {
    super(message);
    this.name = 'ApiRateLimitError';
  }
}

/**
 * Thrown when the backend returns 401 (session expired or missing).
 * The caller should redirect the user to the login page.
 */
export class ApiAuthError extends Error {
  constructor(message = 'Session expired — please sign in again.') {
    super(message);
    this.name = 'ApiAuthError';
  }
}

/**
 * Thrown when the backend or an upstream dependency returns 503
 * (Service Unavailable — temporary overload or maintenance).
 * The caller may retry with exponential backoff; see `withRetry` in
 * retryService.ts.
 */
export class ApiServiceUnavailableError extends Error {
  constructor(message = 'Service temporarily unavailable — please try again later.') {
    super(message);
    this.name = 'ApiServiceUnavailableError';
  }
}

// ---------------------------------------------------------------------------
// Axios instance
// ---------------------------------------------------------------------------

const apiClient: AxiosInstance = axios.create({
  baseURL: BASE_URL,
  timeout: CLIENT_TIMEOUT_MS,
  headers: {
    'Content-Type': 'application/json',
  },
});

// ---------------------------------------------------------------------------
// Request interceptor — attach Cognito id-token
// ---------------------------------------------------------------------------

apiClient.interceptors.request.use(async (config) => {
  try {
    const session = await fetchAuthSession();
    const token = session.tokens?.idToken?.toString();
    if (token !== undefined && token !== '') {
      config.headers.Authorization = `Bearer ${token}`;
    }
  } catch {
    // If we cannot fetch the session, proceed without a token — the backend
    // will return 401 and the response interceptor will throw ApiAuthError.
  }
  return config;
});

// ---------------------------------------------------------------------------
// Response interceptor — map HTTP errors to typed errors
// ---------------------------------------------------------------------------

apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    const status = error.response?.status;

    if (status === 401) {
      throw new ApiAuthError();
    }

    if (status === 408) {
      throw new ApiTimeoutError();
    }

    if (status === 429) {
      const retryAfterHeader = error.response?.headers['retry-after'];
      const retryAfter = retryAfterHeader !== undefined
        ? Number(retryAfterHeader)
        : 60;
      throw new ApiRateLimitError(isNaN(retryAfter) ? 60 : retryAfter);
    }

    if (status === 503) {
      throw new ApiServiceUnavailableError();
    }

    // Re-throw all other Axios errors unchanged so callers can inspect them.
    throw error;
  },
);

// ---------------------------------------------------------------------------
// API methods
// ---------------------------------------------------------------------------

export const api = {
  /**
   * Fetch aggregated campaign overview metrics for a date range and optional
   * filters.
   *
   * GET /api/campaigns/overview
   */
  getCampaignOverview(
    params: CampaignOverviewRequest,
  ): Promise<CampaignOverviewResponse> {
    return apiClient
      .get<CampaignOverviewResponse>('/api/campaigns/overview', { params })
      .then((res) => res.data);
  },

  /**
   * Compare 2–5 campaigns side-by-side.
   *
   * POST /api/campaigns/comparison
   */
  compareCampaigns(
    body: CampaignComparisonRequest,
  ): Promise<CampaignComparisonResponse> {
    return apiClient
      .post<CampaignComparisonResponse>('/api/campaigns/comparison', body)
      .then((res) => res.data);
  },

  /**
   * Retrieve time-to-take-up histogram and statistics for a campaign.
   *
   * GET /api/campaigns/time-analysis/{id}
   *
   * @param campaignId - Unique campaign identifier.
   * @param channel    - Optional media_blasting value to slice by channel.
   * @param region     - Optional wilayah code (string) to slice by region.
   */
  getTimeAnalysis(
    campaignId: string,
    channel?: string,
    region?: string,
  ): Promise<TimeAnalysisResponse> {
    const params: Record<string, string> = {};
    if (channel !== undefined && channel !== '') params['channel'] = channel;
    if (region !== undefined && region !== '') params['region'] = region;

    return apiClient
      .get<TimeAnalysisResponse>(
        `/api/campaigns/time-analysis/${encodeURIComponent(campaignId)}`,
        { params },
      )
      .then((res) => res.data);
  },

  /**
   * Retrieve regional performance breakdown for a campaign.
   *
   * GET /api/campaigns/regional/{id}
   *
   * @param campaignId  - Unique campaign identifier.
   * @param flagProgram - Optional flag_program filter.
   */
  getRegionalPerformance(
    campaignId: string,
    flagProgram?: string,
  ): Promise<RegionalPerformanceResponse> {
    const params: Record<string, string> = {};
    if (flagProgram !== undefined && flagProgram !== '') {
      params['flag_program'] = flagProgram;
    }

    return apiClient
      .get<RegionalPerformanceResponse>(
        `/api/campaigns/regional/${encodeURIComponent(campaignId)}`,
        { params },
      )
      .then((res) => res.data);
  },

  /**
   * Retrieve customer criteria (demographic/financial) distributions for a
   * campaign.
   *
   * GET /api/campaigns/customer-criteria/{id}
   */
  getCustomerCriteria(
    campaignId: string,
  ): Promise<CustomerCriteriaResponse> {
    return apiClient
      .get<CustomerCriteriaResponse>(
        `/api/campaigns/customer-criteria/${encodeURIComponent(campaignId)}`,
      )
      .then((res) => res.data);
  },

  /**
   * Find campaigns similar to a reference campaign across specified
   * dimensions.
   *
   * POST /api/campaigns/similar
   */
  getSimilarCampaigns(
    body: SimilarCampaignRequest,
  ): Promise<SimilarCampaignResponse> {
    return apiClient
      .post<SimilarCampaignResponse>('/api/campaigns/similar', body)
      .then((res) => res.data);
  },

  /**
   * Request export generation for a dashboard page.
   *
   * POST /api/export
   *
   * On success the response contains a pre-signed `download_url`.
   * A `status` of `"timeout"` indicates the 30-second server-side limit was
   * reached; the caller should offer a retry.
   */
  exportData(body: ExportRequest): Promise<ExportResponse> {
    return apiClient
      .post<ExportResponse>('/api/export', body)
      .then((res) => res.data);
  },

  /**
   * Validate the current session and retrieve the authenticated user's
   * profile and role.
   *
   * GET /api/auth/session
   */
  getSession(): Promise<SessionResponse> {
    return apiClient
      .get<SessionResponse>('/api/auth/session')
      .then((res) => res.data);
  },
};
