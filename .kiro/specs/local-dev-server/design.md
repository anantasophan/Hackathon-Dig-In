# Design Document — Local Development Server

## Overview

Local Development Server adalah FastAPI application yang berjalan di `http://localhost:8000`
sebagai pengganti lengkap AWS API Gateway + Lambda untuk lingkungan development lokal.
Server membaca data dari file JSON statis di `backend/local_server/mock_data/`, mengimplementasi
ulang logika request/response yang sama dengan Lambda handlers (tanpa modifikasi pada Lambda handlers
itu sendiri), dan menyajikan semua 8 endpoint + health check + file serving untuk export.

Tujuan utama: developer dapat menjalankan seluruh stack (frontend React + backend Python) di laptop
lokal tanpa koneksi AWS, menggunakan satu perintah sederhana.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  Frontend React (localhost:3000)                                 │
│  .env.local → REACT_APP_API_URL=http://localhost:8000           │
└────────────────────┬────────────────────────────────────────────┘
                     │ HTTP (axios)
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│  FastAPI Application  (localhost:8000)                           │
│  backend/local_server/main.py                                    │
│                                                                  │
│  Middleware: CORSMiddleware (allow_origins=["*"])                │
│                                                                  │
│  Routers:                                                        │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  campaigns.py  — 6 campaign endpoints                     │   │
│  │  export.py     — 1 export endpoint + file serving         │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  Data Layer:                                                     │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  mock_store.py — loads & caches JSON files at startup     │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  Shared (reused from backend/shared/):                           │
│    calculations.py  ✓   filters.py    ✓                          │
│    models.py        ✓   pii_filter.py ✓                          │
│    sorting.py       ✓                                            │
│    athena_client.py ✗   auth.py       ✗  (AWS-dependent)        │
└──────────────────┬──────────────────────────────────────────────┘
                   │ reads
                   ▼
┌─────────────────────────────────────────────────────────────────┐
│  Mock Data  (backend/local_server/mock_data/)                    │
│    campaigns.json          leads.json                            │
│    similarity_index.json   trend_data.json                       │
│    regional_weekly.json                                          │
└─────────────────────────────────────────────────────────────────┘
                   │ writes exports
                   ▼
┌─────────────────────────────────────────────────────────────────┐
│  Export Files  (backend/local_server/exports/)                   │
│    {uuid}.csv   {uuid}.xlsx   {uuid}.pdf                         │
└─────────────────────────────────────────────────────────────────┘
```

---

## Folder Structure

```
backend/
└── local_server/
    ├── __init__.py
    ├── main.py                  # FastAPI app, CORS, router registration, startup log
    ├── mock_store.py            # MockDataStore — loads JSON, provides query methods
    ├── routers/
    │   ├── __init__.py
    │   ├── campaigns.py         # GET/POST campaign endpoints (6 routes)
    │   └── export.py            # POST /api/export + GET /exports/{filename}
    ├── mock_data/
    │   ├── campaigns.json       # 5 campaign master records
    │   ├── leads.json           # ~150 lead records across 5 campaigns
    │   ├── similarity_index.json  # pre-computed similar-campaign pairs
    │   ├── trend_data.json      # weekly trend aggregates per campaign
    │   └── regional_weekly.json # weekly per-region data per campaign
    └── exports/                 # generated export files (gitignored)
        └── .gitkeep
```

---

## Components and Interfaces

### `main.py` — FastAPI Application Entry Point

Responsibilities:
- Creates the FastAPI `app` instance
- Registers `CORSMiddleware` with `allow_origins=["*"]`
- Includes `campaigns` and `export` routers with prefix `/api`
- Defines `GET /health` handler
- Prints startup log with port and endpoint list on `@app.on_event("startup")`

```python
# Startup log example
print("=== Local Dev Server started on http://localhost:8000 ===")
print("Available endpoints:")
print("  GET  /health")
print("  GET  /api/campaigns/overview")
# ... etc
```

---

### `mock_store.py` — Mock Data Store

Loads all JSON files at import time (module-level singleton). Provides typed
query methods used by the routers.


**Public interface:**

```python
class MockDataStore:
    def get_leads(
        self,
        campaign_id: str | None = None,
        flag_program: list[str] | None = None,
        media_blasting: list[str] | None = None,
        wilayah: list[int] | None = None,
        jenis_leads: list[str] | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> list[dict]: ...

    def get_campaign(self, campaign_id: str) -> dict | None: ...
    def get_all_campaigns(self) -> list[dict]: ...
    def get_similarity_index(self, reference_id: str) -> list[dict]: ...
    def get_trend_data(self, campaign_id: str) -> list[dict]: ...
    def get_regional_weekly(self, campaign_id: str) -> list[dict]: ...
```

Singleton instance: `store = MockDataStore()` at module level, imported by routers.

---

### `routers/campaigns.py` — Campaign Endpoints

Six FastAPI route handlers. Each handler:
1. Validates request parameters (raises `HTTPException` on invalid input)
2. Calls `store` methods to get filtered lead records
3. Computes aggregates using `shared.calculations`
4. Strips PII using `shared.pii_filter.strip_pii`
5. Returns JSON response

Uses `shared.sorting` for sort operations and `shared.models` for dataclasses.

---

### `routers/export.py` — Export Endpoint + File Serving

Two route handlers:

**`POST /api/export`**:
1. Validates request body (`ExportRequest` model from `shared.models`)
2. Calls appropriate generator (`_generate_csv`, `_generate_excel`, `_generate_pdf`)
   — generator logic reused/adapted from `lambdas/export_service/handler.py`
3. Saves file to `backend/local_server/exports/{uuid}.{ext}`
4. Returns `{"status": "completed", "download_url": "/exports/{filename}"}`

**`GET /exports/{filename}`**:
- Uses FastAPI `FileResponse` to serve static files from the exports directory
- Returns 404 if file does not exist

---

## API Endpoint Table

| Method | Path | Handler | Req |
|--------|------|---------|-----|
| GET | `/health` | `health_check` | 1.4 |
| GET | `/api/campaigns/overview` | `campaign_overview` | 2.x |
| POST | `/api/campaigns/comparison` | `campaign_comparison` | 3.x |
| GET | `/api/campaigns/time-analysis/{campaign_id}` | `time_analysis` | 4.x |
| GET | `/api/campaigns/regional/{campaign_id}` | `regional_performance` | 5.x |
| GET | `/api/campaigns/customer-criteria/{campaign_id}` | `customer_criteria` | 6.x |
| POST | `/api/campaigns/similar` | `similar_campaign` | 7.x |
| POST | `/api/export` | `export_data` | 8.x |
| GET | `/exports/{filename}` | `serve_export` | 8.4 |

All endpoints respond with `Content-Type: application/json` (except `/exports/{filename}`
which responds with the file's MIME type).

---

## Data Models

### `mock_data/campaigns.json`

List of 5 campaign master records. Each record defines the campaign-level attributes
that summarise what the leads in `leads.json` belong to.

```json
[
  {
    "campaign_id": "C001",
    "nama_program": "Cashback QRIS Agustus 2024",
    "flag_program": "PROGRAM QRIS",
    "jenis_leads": "Akuisisi",
    "media_blasting": "wa",
    "periode_start": "2024-08-01",
    "periode_end": "2024-08-31",
    "duration_days": 30
  },
  {
    "campaign_id": "C002",
    "nama_program": "Migrasi Biaya Admin Q3 2024",
    "flag_program": "PROGRAM BIAYA ADMIN",
    "jenis_leads": "Migrasi",
    "media_blasting": "telesales",
    "periode_start": "2024-07-01",
    "periode_end": "2024-09-30",
    "duration_days": 91
  },
  {
    "campaign_id": "C003",
    "nama_program": "Digisales QRIS Nasabah Mass",
    "flag_program": "PROGRAM QRIS",
    "jenis_leads": "Akuisisi",
    "media_blasting": "digisales",
    "periode_start": "2024-09-01",
    "periode_end": "2024-09-30",
    "duration_days": 29
  },
  {
    "campaign_id": "C004",
    "nama_program": "WA Blast Biaya Admin Emerald",
    "flag_program": "PROGRAM BIAYA ADMIN",
    "jenis_leads": "Migrasi",
    "media_blasting": "wa",
    "periode_start": "2024-10-01",
    "periode_end": "2024-10-31",
    "duration_days": 30
  },
  {
    "campaign_id": "C005",
    "nama_program": "Email QRIS Nasabah Affluent",
    "flag_program": "PROGRAM QRIS",
    "jenis_leads": "Retensi",
    "media_blasting": "email",
    "periode_start": "2024-11-01",
    "periode_end": "2024-11-30",
    "duration_days": 29
  }
]
```


### `mock_data/leads.json`

List of ~150 lead records. `cif` field is intentionally **absent** — no PII in mock data.
Each record has a `campaign_id` field to associate it with a campaign.

```json
[
  {
    "campaign_id": "C001",
    "nama_program": "Cashback QRIS Agustus 2024",
    "jenis_leads": "Akuisisi",
    "media_blasting": "wa",
    "periode_start": "2024-08-01",
    "flag_program": "PROGRAM QRIS",
    "wilayah": 1,
    "cabang": 101,
    "outlet": 0,
    "segment_crs": "mass",
    "segment_by_aum": "MASS",
    "segment_wondr": "GEN Y",
    "segment_div_owner": "CRS",
    "range_usia": "GEN Y",
    "range_saldo_tab": 5000000.0,
    "avg_aum_3_bln": 12000000.0,
    "potensi_money": 500000.0,
    "take_up_flag": "YES",
    "take_up_date": "2024-08-08",
    "time_to_take_up_days": 7,
    "total_transaction_value": 450000.0
  }
]
```

**Variation requirements** in the 150 records:
- `wilayah`: integers 1–17, minimal 5 distinct values
- `flag_program`: mix of both valid values
- `media_blasting`: at least 4 of 6 valid values
- `segment_by_aum`: all 6 tier values present
- `range_usia`: all 5 generation values present
- `take_up_flag`: ~20% YES (realistic 10–25% take-up rate per campaign)
- `time_to_take_up_days`: weighted toward 0–30 days (exponential-like distribution)

---

### `mock_data/similarity_index.json`

Pre-computed similarity pairs. Each entry represents a relationship from
`reference_campaign_id` to `similar_campaign_id`.

```json
[
  {
    "campaign_id": "C001",
    "similar_campaign_id": "C003",
    "campaign_name": "Digisales QRIS Nasabah Mass",
    "matching_dimensions": ["flag_program"],
    "dimension_count": 1,
    "similarity_score": 0.67,
    "take_up_rate": 18.5,
    "total_leads": 45,
    "total_take_up": 8
  },
  {
    "campaign_id": "C001",
    "similar_campaign_id": "C005",
    "campaign_name": "Email QRIS Nasabah Affluent",
    "matching_dimensions": ["flag_program", "jenis_leads"],
    "dimension_count": 2,
    "similarity_score": 0.83,
    "take_up_rate": 22.1,
    "total_leads": 38,
    "total_take_up": 8
  }
]
```

Pairs are symmetric: if C001→C003 exists, C003→C001 must also exist.
At least 3 pairs share 2+ dimensions to satisfy Requirement 9.5.

---

### `mock_data/trend_data.json`

Weekly aggregated trend data per campaign. Used by `GET /api/campaigns/overview`.

```json
{
  "C001": [
    {
      "period_start": "2024-08-01",
      "period_end": "2024-08-07",
      "total_leads": 12,
      "total_take_up": 2,
      "take_up_rate": 16.67
    },
    {
      "period_start": "2024-08-08",
      "period_end": "2024-08-14",
      "total_leads": 14,
      "total_take_up": 3,
      "take_up_rate": 21.43
    }
  ]
}
```

Each campaign has at least 4 trend entries (Requirement 2.8).

---

### `mock_data/regional_weekly.json`

Weekly per-region data per campaign. Used by `GET /api/campaigns/regional/{campaign_id}`
for the `selected_region_trend` field.

```json
{
  "C001": [
    {
      "wilayah": 1,
      "week_start": "2024-08-01",
      "leads_count": 5,
      "take_up_count": 1,
      "take_up_rate": 20.0
    },
    {
      "wilayah": 1,
      "week_start": "2024-08-08",
      "leads_count": 6,
      "take_up_count": 2,
      "take_up_rate": 33.3
    }
  ]
}
```

Each wilayah that appears in leads.json for a campaign has at least 4 weekly entries.
Maximum 8 are returned per `selected_region` request (Requirement 5.6).

---

## Reuse of Shared Modules

| Module | Reused? | Usage in Local Server |
|--------|---------|----------------------|
| `shared/models.py` | ✓ | All request/response dataclasses, constants |
| `shared/calculations.py` | ✓ | `calculate_take_up_rate`, `compute_statistics`, `compute_distribution_percentages`, `select_granularity` |
| `shared/filters.py` | ✓ | `apply_filters` — though local server uses direct dict filtering |
| `shared/pii_filter.py` | ✓ | `strip_pii` on all response dicts |
| `shared/sorting.py` | ✓ | `sort_regional_performance`, `sort_similar_campaigns`, `sort_by_attribute` |
| `shared/athena_client.py` | ✗ | AWS dependency — not imported |
| `shared/auth.py` | ✗ | AWS Cognito dependency — not imported |
| `shared/audit.py` | ✗ | CloudWatch dependency — not imported |
| `shared/rate_limiter.py` | ✗ | DynamoDB dependency — not imported |

**Note on `filters.py`:** The `apply_filters` function uses `VALID_FILTER_FIELDS = {"product",
"sub_product", "channel", "region", "period"}` which uses legacy field names. The local server
applies filtering directly on the lead dict fields (`flag_program`, `media_blasting`, etc.)
rather than through `apply_filters`. The `shared.models.ActiveFilter` is used for building
response payloads.


---

## Endpoint Design Details

### GET `/api/campaigns/overview`

**Query params:** `start_date`, `end_date`, `flag_program`, `media_blasting`, `wilayah`, `jenis_leads`

**Logic:**
1. Parse and validate `start_date`/`end_date` — raise 400 on invalid format
2. Load leads filtered by date range + all provided filters
3. If empty result → return `{"message": "Tidak ada data untuk filter yang dipilih", "filters": [...]}`
4. Compute `total_leads`, `total_take_up`, `take_up_rate` via `calculate_take_up_rate`
5. Count distinct campaign IDs for `total_campaigns`
6. Build trend from `trend_data.json` (not re-computed from leads — pre-aggregated)
7. Apply `strip_pii` on response dict
8. Build `filters` list using `ActiveFilter`

**Response shape:**
```json
{
  "total_leads": 120,
  "total_take_up": 22,
  "take_up_rate": 18.33,
  "total_campaigns": 3,
  "trend": [{"period_start": "...", "period_end": "...", "take_up_rate": 16.5, "total_leads": 30, "total_take_up": 5}],
  "filters": [{"field": "period", "values": ["2024-08-01/2024-10-31"]}]
}
```

---

### POST `/api/campaigns/comparison`

**Body:** `{"campaign_ids": ["C001", "C002"], "group_by": "flag_program"}`

**Logic:**
1. Validate JSON body — 400 if missing/invalid
2. Validate `campaign_ids` length 2–5 — 400 otherwise
3. For each `campaign_id`, aggregate leads from `leads.json`
4. Compute `take_up_rate`, `total_transaction_value`, `duration_days` from `campaigns.json`
5. If `group_by` provided, sort via `sort_by_attribute(ascending=True)`
6. Build `comparison_chart` with Chart.js labels/datasets format

---

### GET `/api/campaigns/time-analysis/{campaign_id}`

**Query params:** `channel`, `region`

**Logic:**
1. Validate `campaign_id` not empty — 400 if empty
2. Load leads for campaign where `take_up_flag == "YES"`
3. Apply optional `channel` (= `media_blasting`) and `region` (= `wilayah`) filters
4. If no take-up records → return `{"message": "Belum ada data take up untuk campaign ini"}`
5. Extract `time_to_take_up_days` values
6. Build histogram with exactly 7 fixed bins: `[0-7, 7-14, 14-21, 21-30, 30-60, 60-90, 90+]`
7. Compute stats via `compute_statistics`

---

### GET `/api/campaigns/regional/{campaign_id}`

**Query params:** `flag_program`, `selected_region`

**Logic:**
1. Load leads for campaign, optionally filtered by `flag_program`
2. If no leads → return empty response with message
3. Group by `wilayah`, compute per-region metrics
4. Sort via `sort_regional_performance` (descending by `take_up_rate`)
5. If `selected_region` provided, load `regional_weekly.json` for that wilayah, return ≤ 8 entries

---

### GET `/api/campaigns/customer-criteria/{campaign_id}`

**Logic:**
1. Validate `campaign_id` — 400 if empty
2. Load all leads for campaign
3. If no leads → return message
4. Apply `strip_pii` on all rows before processing
5. For each of 5 attributes (`segment_by_aum`, `range_usia`, `media_blasting`, `segment_div_owner`, `flag_program`), build distribution using `compute_distribution_percentages`
6. Mark attribute as unavailable if all values are null/empty

**Attribute columns used:** `segment_by_aum`, `range_usia`, `media_blasting`, `segment_div_owner`, `flag_program`
(These are the actual `LeadRecord` field names, not the Lambda handler's `_CUSTOMER_ATTRIBUTES` list.)

---

### POST `/api/campaigns/similar`

**Body:** `{"reference_campaign_id": "C001", "dimensions": ["media_blasting", "flag_program"], "limit": 10}`

**Logic:**
1. Validate body, `reference_campaign_id`, `dimensions` — 400 on errors
2. Validate dimensions against `SIMILAR_CAMPAIGN_DIMENSIONS` — 400 if invalid
3. Load `similarity_index.json` entries where `campaign_id == reference_campaign_id`
4. Filter: keep entries where all requested dimensions are in `matching_dimensions`
5. Convert to `SimilarCampaignResult` objects
6. Sort via `sort_similar_campaigns` (dimension_count desc, take_up_rate desc)
7. Apply `min(limit, 20)` cap
8. Build `learning_summary` from top result
9. Return empty list with message if no results

---

### POST `/api/export`

**Body:** `{"page": "overview", "format": "csv", "filters": [...], "time_range_start": "...", "time_range_end": "..."}`

**Logic:**
1. Validate body → `ExportRequest`
2. Validate `format` in `{"csv", "excel", "pdf"}` — 400 otherwise
3. Generate file using same generators as Lambda handler (adapted without S3)
4. Save to `backend/local_server/exports/{uuid}.{ext}`
5. Return `{"status": "completed", "download_url": "/exports/{filename}"}`

**`GET /exports/{filename}`** — serves file via `FileResponse`, 404 if missing.

---

## CORS Configuration

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

`allow_credentials=False` is required when `allow_origins=["*"]` — browsers block
credentialed requests to wildcard origins. Since local dev doesn't use auth, this
is the correct configuration.

FastAPI's `CORSMiddleware` automatically handles OPTIONS preflight requests.

---

## npm Scripts

### Root `package.json` (create at project root)

```json
{
  "name": "campaign-insight-generator-workspace",
  "private": true,
  "scripts": {
    "dev:backend": "cd backend && uvicorn local_server.main:app --reload --port 8000",
    "dev:frontend": "cd frontend && npm start",
    "dev": "concurrently \"npm run dev:backend\" \"npm run dev:frontend\""
  }
}
```

**Note:** Windows `cd` in npm scripts uses `cmd /c cd ...` which changes directory
only within the subprocess. Use `--cwd` flag or PowerShell syntax if `cd &&` doesn't
work on Windows:

```json
"dev:backend": "uvicorn local_server.main:app --reload --port 8000 --app-dir backend"
```

Alternative: `uvicorn` does not have `--app-dir`. The correct Windows-compatible approach is:

```json
"dev:backend": "cd backend && uvicorn local_server.main:app --reload --port 8000"
```

This works in PowerShell and cmd when npm uses the system shell.

### Frontend `.env.local`

```
REACT_APP_API_URL=http://localhost:8000
```

---

## Dependencies

**`backend/requirements-dev.txt`** — add these lines:

```
fastapi>=0.111.0
uvicorn[standard]>=0.29.0
openpyxl>=3.1.2
reportlab>=4.2.0
```

These are dev-only (local server is not deployed to production).
`openpyxl` and `reportlab` are needed for the Excel/PDF export generators.

---


## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a
system — essentially, a formal statement about what the system should do. Properties serve as the
bridge between human-readable specifications and machine-verifiable correctness guarantees.*

---

### Property 1: Unknown paths return 404

*For any* request path that is not a registered route on the Local_Server, the server SHALL return
HTTP 404 with a JSON body containing a `"detail"` field.

**Validates: Requirements 1.5**

---

### Property 2: All responses carry CORS header

*For any* request to any registered endpoint, the response SHALL include the header
`Access-Control-Allow-Origin: *`.

**Validates: Requirements 1.6, 1.7**

---

### Property 3: Invalid date parameters always return 400

*For any* string value passed as `start_date` or `end_date` that does not match the `yyyy-mm-dd`
ISO 8601 format, the Campaign Overview endpoint SHALL return HTTP 400.

**Validates: Requirements 2.2**

---

### Property 4: Filter predicates are respected

*For any* combination of active filters (`flag_program`, `media_blasting`, `wilayah`,
`jenis_leads`), every lead record contributing to the aggregated response SHALL have field values
that satisfy ALL active filter predicates (AND semantics). No record outside the filter window
shall affect the returned `total_leads` or `total_take_up`.

**Validates: Requirements 2.3, 2.4, 2.5, 2.6**

---

### Property 5: Trend array is chronologically ordered and non-trivially populated

*For any* valid Campaign Overview request against the mock data (which provides ≥ 4 trend entries
per campaign), the `trend` field in the response SHALL contain at least 4 data points, and each
point's `period_start` SHALL be less than or equal to the next point's `period_start`.

**Validates: Requirements 2.8**

---

### Property 6: No cif or PII in any response

*For any* API endpoint and any request, the JSON response body SHALL not contain any field
named `cif`. The mock data itself must not include `cif` fields.

**Validates: Requirements 2.9, 6.7, 9.3**

---

### Property 7: Comparison result items contain all required fields

*For any* valid Campaign Comparison request with 2–5 known campaign IDs, every object in the
`campaigns` list SHALL contain the fields: `campaign_id`, `campaign_name`, `flag_program`,
`total_leads`, `total_take_up`, `take_up_rate`, `total_transaction_value`, `duration_days`.

**Validates: Requirements 3.5**

---

### Property 8: group_by produces ascending sort

*For any* valid Comparison request with a `group_by` value of `"flag_program"`, `"wilayah"`,
or `"media_blasting"`, the campaigns in the response SHALL be sorted by that attribute in
ascending order (i.e., for all adjacent pairs `[i, i+1]`, `campaigns[i][attr] <= campaigns[i+1][attr]`).

**Validates: Requirements 3.6**

---

### Property 9: comparison_chart has correct structure

*For any* valid Comparison request, the `comparison_chart` field SHALL contain a non-empty
`labels` list and a `datasets` list where each dataset has a `label` (string) and a `data`
list of the same length as `labels`.

**Validates: Requirements 3.7**

---

### Property 10: Histogram always has exactly 7 bins with correct ranges

*For any* list of `time_to_take_up_days` values, the histogram returned by `_build_histogram`
SHALL contain exactly 7 entries with `range_start` values `[0, 7, 14, 21, 30, 60, 90]` and
`range_end` values `[7, 14, 21, 30, 60, 90, None]` respectively. Additionally, the sum of
all `count` values SHALL equal the total number of input values.

**Validates: Requirements 4.3**

---

### Property 11: Statistics invariant — max >= min and all non-negative

*For any* non-empty list of `time_to_take_up_days` values (all >= 0), the `stats` object
SHALL satisfy: `max_days >= min_days >= 0`, `mean_days >= 0`, `median_days >= 0`, and
`total_take_up == len(input_values)`.

**Validates: Requirements 4.4**

---

### Property 12: Regions sorted descending by take_up_rate

*For any* Regional Performance response with a non-empty `regions` list, for all adjacent
pairs `[i, i+1]`, `regions[i]["take_up_rate"] >= regions[i+1]["take_up_rate"]`.

**Validates: Requirements 5.3**

---

### Property 13: selected_region_trend length bounded by 8

*For any* Regional Performance request with a valid `selected_region` parameter, the
`selected_region_trend` list SHALL have length at most 8.

**Validates: Requirements 5.6**

---

### Property 14: Distribution items contain required fields

*For any* Customer Criteria response where an attribute's `available == True`, every object
in `items` SHALL contain the fields: `label`, `count`, `percentage`, `take_up_count`,
`take_up_percentage`. The sum of all `percentage` values across items for one attribute
SHALL equal 100.0 (within floating-point rounding tolerance of 0.01).

**Validates: Requirements 6.3, 6.4**

---

### Property 15: Invalid dimensions return 400

*For any* Similar Campaign request where `dimensions` contains a string that is not in
`{"media_blasting", "jenis_leads", "flag_program"}`, the endpoint SHALL return HTTP 400.

**Validates: Requirements 7.4**

---

### Property 16: similar_campaigns sorted by dimension_count desc then take_up_rate desc

*For any* Similar Campaign response with a non-empty `similar_campaigns` list, for all
adjacent pairs `[i, i+1]`:
- `similar_campaigns[i]["dimension_count"] >= similar_campaigns[i+1]["dimension_count"]`
- If `dimension_count` is equal, `similar_campaigns[i]["take_up_rate"] >= similar_campaigns[i+1]["take_up_rate"]`

**Validates: Requirements 7.5**

---

### Property 17: similar_campaigns length bounded by min(limit, 20)

*For any* Similar Campaign request with a `limit` parameter `L`, the length of
`similar_campaigns` SHALL be at most `min(L, 20)`. When `limit` is omitted, the length
SHALL be at most 20.

**Validates: Requirements 7.6**

---

### Property 18: download_url uses local path format

*For any* valid Export request, the `download_url` in the response SHALL be a string
matching the pattern `/exports/{filename}` where `{filename}` is a non-empty string
with a valid file extension (`.csv`, `.xlsx`, or `.pdf`).

**Validates: Requirements 8.4**

---

### Property 19: CSV export contains metadata comment line

*For any* valid Export request with `format: "csv"`, the generated CSV file content SHALL
start with a line beginning with the `#` character containing `source`, `period`, and
`filters` information.

**Validates: Requirements 8.7**

---

## Error Handling

| Scenario | HTTP Status | Response Body |
|----------|-------------|---------------|
| Invalid date format | 400 | `{"detail": "Parameter tanggal tidak valid: ..."}` |
| Missing required body | 400 | `{"detail": "Request body is required."}` |
| Invalid JSON body | 400 | `{"detail": "Request body must be valid JSON."}` |
| campaign_ids < 2 | 400 | `{"detail": "campaign_ids must contain at least 2..."}` |
| campaign_ids > 5 | 400 | `{"detail": "campaign_ids must contain at most 5..."}` |
| Missing campaign_id | 400 | `{"detail": "campaign_id path parameter is required"}` |
| Missing reference_campaign_id | 400 | `{"detail": "reference_campaign_id is required..."}` |
| Invalid dimension | 400 | `{"detail": "Invalid dimension(s): [...] Allowed: [...]"}` |
| Unsupported export format | 400 | `{"detail": "Unsupported export format '...'. Must be one of: ..."}` |
| Export file not found | 404 | `{"detail": "Export file not found"}` |
| Unknown path | 404 | `{"detail": "Not found"}` |

FastAPI raises `HTTPException` which FastAPI serialises to JSON automatically.

For empty/zero-result cases (not errors), return HTTP 200 with a `"message"` field
explaining the empty state.

---

## Testing Strategy

### Unit Tests

Located in `backend/tests/unit/test_local_server_*.py`.

Focus areas:
- `MockDataStore.get_leads` filtering logic (each filter type)
- Export file generators (`_generate_csv`, `_generate_excel`, `_generate_pdf`)
- Histogram bin computation (`_build_histogram`)
- Distribution calculation correctness

Use `fastapi.testclient.TestClient` for HTTP-level tests against the FastAPI app.

### Property-Based Tests (Hypothesis)

Located in `backend/tests/property/test_local_server_properties.py`.

Uses [Hypothesis](https://hypothesis.readthedocs.io/) — already in `requirements-dev.txt`.

**Configuration:** Each property test runs minimum 100 examples (`settings(max_examples=100)`).

**Tag format:** Each test is annotated with:
```python
# Feature: local-dev-server, Property N: <property_text>
```

Properties to implement as Hypothesis tests:

| Property | Test strategy |
|----------|---------------|
| Property 3: Invalid dates → 400 | Generate arbitrary strings that are not valid ISO dates |
| Property 4: Filter predicates | Generate random filter combinations, check all returned records match |
| Property 5: Trend ordered | Check `trend[i].period_start <= trend[i+1].period_start` for all i |
| Property 6: No cif in response | Check all endpoint responses for absence of `cif` key at any depth |
| Property 10: Histogram 7 bins | Generate random list of int days, check exactly 7 bins and count sum |
| Property 11: Stats invariant | Generate random positive int lists, check max >= min >= 0 |
| Property 12: Regions sorted | Generate random region dicts, check sort_regional_performance result |
| Property 14: Distribution 100% | Generate random group counts, check percentages sum to 100 |
| Property 16: Similar sorted | Generate random SimilarCampaignResult lists, check sort order |
| Property 17: Limit bounded | Generate random limit values 1–100, check response length |

Properties 1, 2, 7, 8, 9, 13, 15, 18, 19 are tested via example-based tests (TestClient).

### Integration Tests

Not applicable — local server is itself the integration boundary.
Verify end-to-end flows manually by running the server and hitting endpoints via browser/curl.

---

## Setup Instructions

### Prerequisites

- Python 3.11+ installed (not Microsoft Store stub)
- Node.js 18+ installed
- `pip install -r backend/requirements-dev.txt` from project root

### Install Dependencies

```powershell
cd "c:\Users\robin\OneDrive\Documents\Project Kiro"
pip install -r backend/requirements-dev.txt
```

### Run Local Server

```powershell
# Option 1: Direct uvicorn (from project root)
cd backend
uvicorn local_server.main:app --reload --port 8000

# Option 2: npm script (from project root)
npm run dev:backend
```

### Run Frontend (separate terminal)

```powershell
cd frontend
# Create .env.local with: REACT_APP_API_URL=http://localhost:8000
npm start
```

### Verify Server is Running

```powershell
curl http://localhost:8000/health
# Expected: {"status": "ok", "mode": "local-dev"}
```

### Verify Python Path (important)

The `uvicorn` command must be run from `backend/` directory so that
`from shared.models import ...` resolves correctly (the `backend/` directory
must be on `sys.path`). `uvicorn` adds the current working directory to
`sys.path` automatically.

Alternatively, configure `PYTHONPATH`:
```powershell
$env:PYTHONPATH = "c:\Users\robin\OneDrive\Documents\Project Kiro\backend"
uvicorn local_server.main:app --reload --port 8000
```
