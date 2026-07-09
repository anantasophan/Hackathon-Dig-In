# Implementation Plan: Campaign Insight Generator

## Overview

This plan implements the Campaign Insight Generator as a serverless analytics dashboard on AWS. The monorepo is split into `frontend/` (React.js TypeScript on Amplify) and `backend/` (Python Lambda functions, CDK infrastructure, Glue ETL jobs, and tests). Implementation proceeds bottom-up: shared backend logic first, then Lambda handlers, ETL, infrastructure, frontend, and finally integration wiring.

## Tasks

- [x] 1. Set up project structure and shared backend modules
  - [x] 1.1 Initialize backend project structure and dependencies
    - Create `backend/` directory with `pyproject.toml`, `requirements.txt`, `requirements-dev.txt`
    - Add dependencies: `boto3`, `pyathena`, `pydantic` (runtime); `pytest`, `hypothesis`, `moto[all]`, `pytest-cov`, `pytest-mock` (dev)
    - Create directory structure: `lambdas/`, `shared/`, `infrastructure/`, `tests/unit/`, `tests/property/`, `tests/integration/`, `glue_jobs/`
    - _Requirements: 7.1, 7.2, 7.4_

  - [x] 1.2 Implement shared data models (`backend/shared/models.py`)
    - Define Python dataclasses: `CampaignOverviewRequest`, `CampaignOverviewResponse`, `TrendDataPoint`, `ActiveFilter`
    - Define: `CampaignComparisonRequest`, `CampaignComparisonResponse`, `CampaignMetric`
    - Define: `SimilarCampaignRequest`, `SimilarCampaignResponse`, `SimilarCampaignResult`
    - Define: `ExportRequest`, `ExportResponse`
    - Add validation logic (e.g., campaign selection count 2-5, date range validation)
    - _Requirements: 2.3, 2.5, 1.1, 6.1_



    

  - [x] 1.3 Implement shared calculations module (`backend/shared/calculations.py`)
    - `calculate_take_up_rate(total_leads, total_take_up) -> float` — returns percentage (0-100)
    - `compute_time_to_take_up(distribution_date, take_up_date) -> int` — calendar days
    - `compute_statistics(values: list[int]) -> dict` — min, max, mean, median
    - `compute_distribution_percentages(groups: dict[str, int]) -> dict[str, float]` — sum to 100%
    - `select_granularity(start_date, end_date) -> str` — "weekly" if ≤90 days, "monthly" otherwise
    - _Requirements: 1.1, 1.7, 3.1, 3.2, 4.1, 5.1, 5.2, 5.3, 5.4_

  - [x] 1.4 Implement shared filter module (`backend/shared/filters.py`)
    - `apply_filters(dataset, filters: list[ActiveFilter]) -> list` — AND logic intersection
    - `validate_filters(filters: list[ActiveFilter]) -> bool` — check filter field names and values
    - Support filter fields: product, sub_product, channel, region, period
    - _Requirements: 1.3, 1.4, 1.5, 3.3, 3.4, 4.4, 6.2_

  - [x] 1.5 Implement PII filter module (`backend/shared/pii_filter.py`)
    - `strip_pii(data: dict) -> dict` — removes fields: nama_lengkap, nomor_rekening, nomor_identitas, alamat_lengkap
    - `has_pii(data: dict) -> bool` — checks if PII fields exist
    - Apply to all API responses regardless of user role
    - _Requirements: 7.5, 7.6_

  - [x] 1.6 Implement Athena query helper (`backend/shared/athena_client.py`)
    - `AthenaClient` class wrapping boto3 Athena client
    - `execute_query(sql: str, params: dict) -> list[dict]` — parameterized query execution
    - `build_campaign_overview_query(request: CampaignOverviewRequest) -> str`
    - `build_comparison_query(campaign_ids: list[str]) -> str`
    - `build_regional_query(campaign_id: str) -> str`
    - `build_time_analysis_query(campaign_id: str) -> str`
    - `build_customer_criteria_query(campaign_id: str) -> str`
    - Query timeout handling (30-second limit)
    - _Requirements: 1.2, 2.1, 3.1, 4.1, 5.1_

- [x] 2. Implement core calculation logic and property tests
  - [x] 2.1 Implement sorting utility (`backend/shared/sorting.py`)
    - `sort_by_attribute(items: list[dict], attribute: str, ascending: bool) -> list[dict]`
    - `sort_similar_campaigns(campaigns: list[SimilarCampaignResult]) -> list` — by dimension_count desc, take_up_rate desc tiebreaker
    - `sort_regional_performance(regions: list[dict]) -> list` — by take_up_rate descending
    - _Requirements: 2.4, 4.2, 6.1_

  - [x]* 2.2 Write property test: Take-Up Rate Calculation (Property 1)
    - **Property 1: Take-Up Rate Calculation Correctness**
    - Generate random total_leads (1–1,000,000) and total_take_up (0–total_leads)
    - Verify: rate == (total_take_up / total_leads) × 100 within ±0.0001
    - **Validates: Requirements 1.1, 4.1, 5.4**

  - [x]* 2.3 Write property test: Filter Correctness (Property 2)
    - **Property 2: Filter Correctness**
    - Generate lists of campaign dicts with random field values; apply single filter
    - Verify: all items in result match filter value, no non-matching items present
    - **Validates: Requirements 1.3, 1.4, 3.3, 3.4, 4.4, 6.2**

  - [x]* 2.4 Write property test: Combined Filters AND Logic (Property 3)
    - **Property 3: Combined Filters Use AND Logic**
    - Generate campaign lists and 2+ filters; verify result equals intersection of individual filters
    - **Validates: Requirements 1.5**

  - [x]* 2.5 Write property test: Time-Series Granularity Selection (Property 4)
    - **Property 4: Time-Series Granularity Selection**
    - Generate random date ranges; verify ≤90 days → weekly, >90 days → monthly
    - **Validates: Requirements 1.7**

  - [x]* 2.6 Write property test: Campaign Selection Validation (Property 5)
    - **Property 5: Campaign Selection Validation**
    - Generate random campaign count (0-10); verify accept 2-5, reject others with ValidationError
    - **Validates: Requirements 2.3, 2.5**

  - [x]* 2.7 Write property test: Comparison Completeness (Property 6)
    - **Property 6: Comparison Completeness**
    - Generate 2-5 campaign metric dicts; verify all 5 metrics present for each campaign
    - **Validates: Requirements 2.1**

  - [x]* 2.8 Write property test: Sorting Correctness (Property 7)
    - **Property 7: Sorting Correctness**
    - Generate lists of floats/dicts; verify ascending/descending ordering invariant
    - **Validates: Requirements 2.4, 4.2**

  - [x]* 2.9 Write property test: Time-to-Take-Up Calculation (Property 8)
    - **Property 8: Time-to-Take-Up Calculation**
    - Generate random date pairs; verify days = (take_up_date - distribution_date).days
    - **Validates: Requirements 3.1**

  - [x]* 2.10 Write property test: Statistical Computation (Property 9)
    - **Property 9: Statistical Computation Correctness**
    - Generate non-empty integer lists; verify min ≤ median ≤ max, mean = sum/count
    - **Validates: Requirements 3.2**

  - [x]* 2.11 Write property test: Distribution Percentages Sum to 100% (Property 10)
    - **Property 10: Distribution Percentages Sum to 100%**
    - Generate grouped data; verify sum of percentages == 100% (±0.01%)
    - **Validates: Requirements 5.1, 5.2, 5.3**

  - [x]* 2.12 Write property test: Similar Campaign Ranking (Property 11)
    - **Property 11: Similar Campaign Ranking**
    - Generate list of similar campaign results; verify ≤20 items, sorted by dimension_count desc, tiebreak by take_up_rate desc
    - **Validates: Requirements 6.1**

  - [x]* 2.13 Write property test: PII Never Exposed (Property 14)
    - **Property 14: PII Never Exposed**
    - Generate dicts with random PII fields; verify strip_pii removes all PII
    - **Validates: Requirements 7.5, 7.6**

- [x] 3. Checkpoint - Verify shared modules and property tests
  - Ensure all tests pass, ask the user if questions arise.

- [x] 4. Implement Lambda function handlers
  - [x] 4.1 Implement Campaign Overview Lambda (`backend/lambdas/campaign_overview/handler.py`)
    - Parse query parameters into `CampaignOverviewRequest`
    - Call `AthenaClient.build_campaign_overview_query()` and execute
    - Compute take_up_rate, build trend data, apply PII filter
    - Return `CampaignOverviewResponse` as JSON
    - Handle empty data (return 200 with message), timeout (return 408), validation errors (return 400)
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7_

  - [x] 4.2 Implement Campaign Comparison Lambda (`backend/lambdas/campaign_comparison/handler.py`)
    - Parse body into `CampaignComparisonRequest`
    - Validate campaign_ids count (2-5), reject with 400 if invalid
    - Query Athena for campaign metrics, build comparison chart data
    - Apply grouping/sorting by attribute if specified
    - Return `CampaignComparisonResponse` as JSON
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

  - [x] 4.3 Implement Time Analysis Lambda (`backend/lambdas/time_analysis/handler.py`)
    - Parse path parameter `campaign_id` and optional query params (channel, region)
    - Query Athena for lead distribution and take-up dates
    - Compute time_to_take_up_days for each lead
    - Calculate histogram bins, statistics (min, max, mean, median)
    - Handle empty data states
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6_

  - [x] 4.4 Implement Regional Performance Lambda (`backend/lambdas/regional_performance/handler.py`)
    - Parse path parameter `campaign_id` and optional product filter
    - Query Athena for per-region metrics (leads, take_up, take_up_rate)
    - Sort regions by take_up_rate descending
    - Optionally return 8-week trend for a selected region
    - Handle empty regional data
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

  - [x] 4.5 Implement Customer Criteria Lambda (`backend/lambdas/customer_criteria/handler.py`)
    - Parse path parameter `campaign_id`
    - Query Athena for demographic and financial attribute distributions
    - Compute percentages for take-up vs non-take-up groups (must sum to 100%)
    - Compute per-attribute take_up_rate breakdown
    - Handle partially available data
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

  - [x] 4.6 Implement Similar Campaign Lambda (`backend/lambdas/similar_campaign/handler.py`)
    - Parse body into `SimilarCampaignRequest`
    - Query DynamoDB CampaignSimilarityIndex for matching campaigns
    - Apply dimension filter, sort by dimension_count desc + take_up_rate tiebreaker
    - Limit to max 20 results
    - Build learning summary: take_up_rate (2 decimal), top segment, top region
    - Handle no similar campaigns found
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_

  - [x] 4.7 Implement Export Service Lambda (`backend/lambdas/export_service/handler.py`)
    - Parse body into `ExportRequest`
    - Generate export file (PDF via reportlab/weasyprint, Excel via openpyxl, CSV via csv module)
    - Include metadata: active filters, time range, source page
    - Upload to S3, generate presigned download URL (valid 15 minutes)
    - 30-second timeout: cancel and return timeout response
    - Cleanup partial S3 objects on failure
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5_

  - [x] 4.8 Implement authentication and session management middleware
    - Create `backend/shared/auth.py` — JWT validation helper using Cognito public keys
    - Verify token in Lambda event (from API Gateway authorizer)
    - Extract user role (divisi_bisnis | divisi_data) from Cognito claims
    - Enforce 8-hour session expiry (28,800 seconds from login timestamp)
    - Return 401 for expired/invalid sessions
    - _Requirements: 7.1, 7.2, 7.3_

  - [x] 4.9 Implement audit logging middleware
    - Create `backend/shared/audit.py` — log access events to DynamoDB AuditLog table
    - Record: user_id, timestamp (ISO 8601), page_accessed, action, request_params
    - Integrate as decorator/middleware for all Lambda handlers
    - _Requirements: 7.4_

  - [x]* 4.10 Write unit tests for Lambda handlers
    - Test Campaign Overview: default 3-month period, empty state message, filter application
    - Test Campaign Comparison: valid 2-5 selection, rejection at 6, chart data structure
    - Test Time Analysis: histogram binning, statistics correctness, empty data
    - Test Regional Performance: sorting by take_up_rate, 8-week trend, empty region
    - Test Customer Criteria: percentage distributions, partial data handling
    - Test Similar Campaign: ranking, learning summary format, no results message
    - Test Export: format generation, timeout handling, metadata presence
    - Test Auth: expired token rejection, role extraction, redirect on unauthenticated
    - Use moto library to mock boto3 (Athena, S3, DynamoDB, Cognito)
    - _Requirements: 1.1–8.5_

- [x] 5. Checkpoint - Verify Lambda handlers pass unit tests
  - Ensure all tests pass, ask the user if questions arise.

- [x] 6. Implement remaining property tests and session/audit/export properties
  - [x]* 6.1 Write property test: Learning Summary Accuracy (Property 12)
    - **Property 12: Similar Campaign Learning Summary Accuracy**
    - Generate campaign data with random segments/regions/rates
    - Verify: take_up_rate formatted to 2 decimal places, correct top segment, correct top region
    - **Validates: Requirements 6.4**

  - [x]* 6.2 Write property test: Session Expiry Enforcement (Property 13)
    - **Property 13: Session Expiry Enforcement**
    - Generate random login timestamps; verify session expires at login + 8h (28,800s) exactly
    - **Validates: Requirements 7.2**

  - [x]* 6.3 Write property test: Audit Log Completeness (Property 15)
    - **Property 15: Audit Log Completeness**
    - Generate access events; verify audit entry contains user_id, timestamp, page_accessed — none null/empty
    - **Validates: Requirements 7.4**

  - [x]* 6.4 Write property test: Export Data Integrity (Property 16)
    - **Property 16: Export Data Integrity**
    - Generate filtered datasets; verify export contains exactly the same records as filtered view
    - **Validates: Requirements 8.1**

  - [x]* 6.5 Write property test: Export Metadata Presence (Property 17)
    - **Property 17: Export Metadata Presence**
    - Generate export requests; verify metadata includes filter names, time range, source page
    - **Validates: Requirements 8.2**

- [x] 7. Implement Glue ETL jobs
  - [x] 7.1 Implement raw-to-clean ETL job (`backend/glue_jobs/raw_to_clean.py`)
    - PySpark job reading from S3 Raw Zone (CSV/JSON)
    - Clean and normalize data: deduplicate, handle nulls, standardize date formats
    - Write to S3 Clean Zone as Parquet partitioned by year/month (campaigns) and campaign_id (leads)
    - _Requirements: 1.1, 3.1, 4.1, 5.1_

  - [x] 7.2 Implement aggregate metrics ETL job (`backend/glue_jobs/aggregate_metrics.py`)
    - PySpark job computing `campaign_overview_agg` table
    - Aggregate by period (weekly/monthly), product, channel, region
    - Compute: total_leads, total_take_up, take_up_rate, total_transaction_value, campaign_count
    - Write to S3 Aggregated Zone as Parquet
    - _Requirements: 1.1, 1.7_

  - [x] 7.3 Implement similarity index ETL job (`backend/glue_jobs/similarity_index.py`)
    - PySpark job computing campaign similarity based on 4 dimensions (product, segment, region, channel)
    - Calculate dimension_count and similarity_score for each campaign pair
    - Write results to DynamoDB CampaignSimilarityIndex table
    - _Requirements: 6.1_

  - [x] 7.4 Implement regional rollup ETL job (`backend/glue_jobs/regional_rollup.py`)
    - PySpark job computing `regional_performance_agg` table
    - Aggregate per campaign per region per week: leads_count, take_up_count, take_up_rate, avg_transaction_value
    - Write to S3 Aggregated Zone as Parquet
    - _Requirements: 4.1, 4.3_

  - [x]* 7.5 Write unit tests for Glue ETL jobs
    - Test raw-to-clean: schema validation, null handling, deduplication
    - Test aggregate metrics: correct aggregation math, partitioning
    - Test similarity index: dimension matching logic, score calculation
    - Test regional rollup: weekly bucketing, rate calculation
    - Use PySpark local mode with test DataFrames
    - _Requirements: 1.1, 4.1, 6.1_

- [x] 8. Implement AWS CDK infrastructure
  - [x] 8.1 Implement CDK app entry point and shared constructs (`backend/infrastructure/app.py`)
    - CDK app entry point with environment configuration (dev, staging, prod)
    - Define shared constructs: S3 buckets (raw, clean, aggregated, export), DynamoDB tables
    - _Requirements: 7.1_

  - [x] 8.2 Implement API stack (`backend/infrastructure/stacks/api_stack.py`)
    - API Gateway REST API with Cognito authorizer
    - Lambda functions for each endpoint with IAM roles
    - Route configuration matching design endpoint table
    - CORS configuration, request validation, rate limiting (429 response)
    - CloudWatch logging and CloudTrail integration
    - _Requirements: 1.2, 7.1, 7.4_

  - [x] 8.3 Implement data stack (`backend/infrastructure/stacks/data_stack.py`)
    - S3 buckets: campaign-datalake (raw/clean/aggregated zones), campaign-exports
    - DynamoDB tables: CampaignSimilarityIndex, AuditLog, UserSessions (with TTL)
    - Athena workgroup and named queries
    - Glue jobs with schedules (daily 02:00, 03:00, 03:30; weekly Sun 04:00)
    - _Requirements: 6.1, 7.4_

  - [x] 8.4 Implement auth stack (`backend/infrastructure/stacks/auth_stack.py`)
    - Cognito User Pool with custom attributes (role: divisi_bisnis | divisi_data)
    - User Pool Client configuration
    - Token validity: 8 hours for access token
    - API Gateway Cognito authorizer integration
    - _Requirements: 7.1, 7.2, 7.3_

- [x] 9. Checkpoint - Verify backend infrastructure and ETL
  - Ensure all tests pass, ask the user if questions arise.

- [x] 10. Initialize frontend project and implement core layout
  - [x] 10.1 Initialize React.js frontend project (`frontend/`)
    - Create React app with TypeScript template
    - Install dependencies: react-router-dom, chart.js/react-chartjs-2, axios, @aws-amplify/ui-react
    - Configure `tsconfig.json`, ESLint, Prettier
    - Set up Amplify hosting configuration
    - _Requirements: 1.1, 7.1_

  - [x] 10.2 Implement authentication components (`frontend/src/components/AuthGuard.tsx`)
    - `AuthGuard` component: route protection, redirect unauthenticated users to login
    - Login page with Cognito Hosted UI integration
    - Session management: auto-redirect on 8-hour expiry
    - Role extraction from JWT claims for conditional rendering
    - _Requirements: 7.1, 7.2, 7.3_

  - [x] 10.3 Implement dashboard layout and navigation (`frontend/src/components/DashboardLayout.tsx`)
    - Main layout: header with user info/logout, sidebar navigation, content area
    - Navigation links: Overview, Comparison, Time Analysis, Regional, Customer Criteria, Similar Campaigns
    - Responsive design for desktop use
    - _Requirements: 1.1_

  - [x] 10.4 Implement shared FilterPanel component (`frontend/src/components/FilterPanel.tsx`)
    - Filter fields: period (date range picker), product, sub-product, channel, region
    - Multi-select dropdowns for product/channel/region
    - Apply/Reset buttons
    - Emit filter state to parent page components
    - _Requirements: 1.3, 1.4, 1.5_

  - [x] 10.5 Implement API service layer (`frontend/src/services/api.ts`)
    - Axios instance with Cognito JWT token in Authorization header
    - API methods for all 8 endpoints matching design specification
    - Error interceptor: handle 401 (redirect to login), 408 (show retry), 429 (show wait)
    - Response type interfaces matching backend dataclasses
    - _Requirements: 7.1, 7.2_

- [x] 11. Implement frontend pages
  - [x] 11.1 Implement Campaign Overview page (`frontend/src/pages/CampaignOverviewPage.tsx`)
    - Display aggregate metrics: total leads, total take up, take up rate
    - Time-series trend chart (line chart with Chart.js)
    - Integration with FilterPanel — refresh on filter change
    - Empty state message when no data matches filters
    - Loading state and <5 second response indicator
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7_

  - [x] 11.2 Implement Campaign Comparison page (`frontend/src/pages/CampaignComparisonPage.tsx`)
    - Campaign multi-select (2-5 campaigns) with validation UI
    - Comparison table with 5 metrics per campaign
    - Side-by-side bar chart visualization
    - Group-by dropdown (product, region, channel) with ascending sort
    - Block 6th selection with max-limit message
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

  - [x] 11.3 Implement Time to Take Up page (`frontend/src/pages/TimeToTakeUpPage.tsx`)
    - Histogram visualization of time-to-take-up distribution
    - Statistics display: median, mean, min, max
    - Channel and region filter integration
    - Empty data state messaging
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6_

  - [x] 11.4 Implement Regional Performance page (`frontend/src/pages/RegionalPerformancePage.tsx`)
    - Region table/chart sorted by take_up_rate descending
    - Per-region detail view with 8-week trend (line chart)
    - Product filter integration
    - Empty regional data messaging
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

  - [x] 11.5 Implement Customer Criteria page (`frontend/src/pages/CustomerCriteriaPage.tsx`)
    - Demographic distribution charts (segment, age group, domicile region)
    - Financial distribution charts (product holding, balance category)
    - Take-up vs non-take-up comparison visualization
    - Per-attribute take_up_rate breakdown
    - Partial data availability messaging
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

  - [x] 11.6 Implement Similar Campaign page (`frontend/src/pages/SimilarCampaignPage.tsx`)
    - Reference campaign selector
    - Dimension filter checkboxes (product, segment, region, channel)
    - Similar campaign list (max 20, sorted by dimension_count desc)
    - Side-by-side comparison view with 4 sections (metrics, customer, regional, time)
    - Learning summary display (2-decimal rate, top segment, top region)
    - No similar campaigns found messaging
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_

  - [x] 11.7 Implement Export functionality (`frontend/src/components/ExportService.tsx`)
    - Export button on each applicable page
    - Format selector (PDF, Excel, CSV)
    - Trigger export API with current page filters
    - Success: auto-download via presigned URL + in-app notification
    - Timeout (30s): cancel, show timeout message, offer retry
    - Error: display cause, offer retry
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5_

- [ ] 12. Checkpoint - Verify frontend builds and renders
  - Ensure all tests pass, ask the user if questions arise.

- [x] 13. Integration wiring and end-to-end validation
  - [x] 13.1 Wire frontend to backend API endpoints
    - Configure Amplify environment variables (API Gateway URL, Cognito User Pool ID, Client ID)
    - Verify all 8 API calls from frontend reach correct Lambda handlers
    - Test CORS configuration end-to-end
    - Verify JWT token flow from Cognito through API Gateway to Lambda
    - _Requirements: 7.1, 7.2_

  - [x] 13.2 Implement error handling and retry logic
    - Frontend: exponential backoff retry for 408 and 503 (max 3 attempts: 1s, 2s, 4s)
    - Frontend: circuit breaker display after 5 consecutive failures
    - Backend: Lambda timeout handling (30s query limit), graceful error responses
    - Backend: Rate limit response (429) with Retry-After header
    - _Requirements: 1.6, 2.5, 3.5, 3.6, 4.5, 6.5, 8.4, 8.5_

  - [ ]* 13.3 Write integration tests for AWS service interactions
    - Test Athena query execution and result parsing (mock with moto)
    - Test S3 export file write and presigned URL generation
    - Test DynamoDB audit log writes and similarity index queries
    - Test Cognito token validation and session management
    - Test API Gateway request validation and routing
    - _Requirements: 1.1, 6.1, 7.1, 7.4, 8.1_

- [ ] 14. Final checkpoint - Full system validation
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design document (17 properties)
- Unit tests validate specific examples and edge cases using moto for AWS mocking
- Backend uses Python 3.11+ with type hints throughout
- Frontend uses TypeScript strict mode
- All Lambda handlers follow the same pattern: parse input → validate → query → compute → filter PII → respond

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "10.1"] },
    { "id": 1, "tasks": ["1.2", "1.3", "1.4", "1.5", "1.6", "10.2", "10.3"] },
    { "id": 2, "tasks": ["2.1", "2.2", "2.3", "2.4", "2.5", "2.6", "2.7", "2.8", "2.9", "2.10", "2.11", "2.12", "2.13", "10.4", "10.5"] },
    { "id": 3, "tasks": ["4.1", "4.2", "4.3", "4.4", "4.5", "4.6", "4.7", "4.8", "4.9", "7.1"] },
    { "id": 4, "tasks": ["4.10", "7.2", "7.3", "7.4", "8.1"] },
    { "id": 5, "tasks": ["6.1", "6.2", "6.3", "6.4", "6.5", "7.5", "8.2", "8.3", "8.4"] },
    { "id": 6, "tasks": ["11.1", "11.2", "11.3", "11.4", "11.5", "11.6", "11.7"] },
    { "id": 7, "tasks": ["13.1", "13.2"] },
    { "id": 8, "tasks": ["13.3"] }
  ]
}
```
