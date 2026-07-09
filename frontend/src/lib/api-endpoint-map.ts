/**
 * api-endpoint-map.ts — Dokumentasi pemetaan endpoint frontend → Lambda handler.
 *
 * File ini berfungsi sebagai "single source of truth" yang mendokumentasikan
 * setiap panggilan API dari frontend, path-nya di API Gateway, dan Lambda
 * handler yang menanganinya di backend.
 *
 * Tujuan:
 *  - Memudahkan audit saat deployment (pastikan semua route tersambung).
 *  - Referensi cepat saat debugging request/response cycle.
 *  - Verifikasi bahwa path di api.ts sesuai dengan CDK api_stack.py.
 *
 * Requirements: 7.1, 7.2
 */

/** Deskripsi satu pemetaan endpoint. */
export interface EndpointMapping {
  /** Nama fungsi di api.ts */
  frontendMethod: string;
  /** HTTP verb */
  httpMethod: 'GET' | 'POST';
  /** Path relatif terhadap API Gateway base URL */
  path: string;
  /** File Lambda handler yang menangani request ini */
  lambdaHandler: string;
  /** Apakah endpoint ini dilindungi Cognito JWT authorizer */
  requiresAuth: boolean;
  /** Catatan tambahan */
  notes?: string;
}

/**
 * Pemetaan lengkap 8 endpoint Campaign Insight Generator.
 *
 * Diverifikasi terhadap:
 *  - frontend/src/services/api.ts  (path & HTTP method)
 *  - backend/infrastructure/stacks/api_stack.py  (CDK route tree)
 *  - backend/lambdas/<name>/handler.py  (Lambda handler)
 *
 * Last verified: Task 13.1
 */
export const API_ENDPOINT_MAP: readonly EndpointMapping[] = [
  {
    frontendMethod: 'getCampaignOverview',
    httpMethod: 'GET',
    path: '/api/campaigns/overview',
    lambdaHandler: 'backend/lambdas/campaign_overview/handler.py → lambda_handler',
    requiresAuth: true,
    notes: 'Query params: start_date, end_date, flag_program[], media_blasting[], wilayah[], jenis_leads[]',
  },
  {
    frontendMethod: 'compareCampaigns',
    httpMethod: 'POST',
    path: '/api/campaigns/comparison',
    lambdaHandler: 'backend/lambdas/campaign_comparison/handler.py → lambda_handler',
    requiresAuth: true,
    notes: 'Body: { campaign_ids: string[2-5], group_by?: "flag_program"|"wilayah"|"media_blasting" }',
  },
  {
    frontendMethod: 'getTimeAnalysis',
    httpMethod: 'GET',
    path: '/api/campaigns/time-analysis/{id}',
    lambdaHandler: 'backend/lambdas/time_analysis/handler.py → lambda_handler',
    requiresAuth: true,
    notes: 'Path param: id (campaignId). Optional query: channel (media_blasting), region (wilayah code 1-17)',
  },
  {
    frontendMethod: 'getRegionalPerformance',
    httpMethod: 'GET',
    path: '/api/campaigns/regional/{id}',
    lambdaHandler: 'backend/lambdas/regional_performance/handler.py → lambda_handler',
    requiresAuth: true,
    notes: 'Path param: id (campaignId). Optional query: flag_program',
  },
  {
    frontendMethod: 'getCustomerCriteria',
    httpMethod: 'GET',
    path: '/api/campaigns/customer-criteria/{id}',
    lambdaHandler: 'backend/lambdas/customer_criteria/handler.py → lambda_handler',
    requiresAuth: true,
    notes: 'Path param: id (campaignId). Returns demographic & financial distributions (PII stripped)',
  },
  {
    frontendMethod: 'getSimilarCampaigns',
    httpMethod: 'POST',
    path: '/api/campaigns/similar',
    lambdaHandler: 'backend/lambdas/similar_campaign/handler.py → lambda_handler',
    requiresAuth: true,
    notes: 'Body: { reference_campaign_id, dimensions: ("media_blasting"|"jenis_leads"|"flag_program")[], limit?: number }',
  },
  {
    frontendMethod: 'exportData',
    httpMethod: 'POST',
    path: '/api/export',
    lambdaHandler: 'backend/lambdas/export_service/handler.py → lambda_handler',
    requiresAuth: true,
    notes: 'Body: { page, format: "pdf"|"excel"|"csv", filters }. Response: { download_url, status }',
  },
  {
    frontendMethod: 'getSession',
    httpMethod: 'GET',
    path: '/api/auth/session',
    lambdaHandler: '(Cognito — tidak ada Lambda terpisah)',
    requiresAuth: true,
    notes:
      'Endpoint ini diimplementasikan sebagai panggilan fetchAuthSession() dari AWS Amplify, ' +
      'bukan route API Gateway. Token di-validate client-side via Cognito SDK.',
  },
] as const;

/**
 * Base URL API Gateway yang digunakan oleh api.ts.
 * Dibaca dari environment variable REACT_APP_API_GATEWAY_URL.
 *
 * Format: https://<id>.execute-api.<region>.amazonaws.com/<stage>
 * Contoh: https://abc123.execute-api.ap-southeast-1.amazonaws.com/prod
 */
export const API_BASE_URL = process.env['REACT_APP_API_GATEWAY_URL'] ?? '';
