# Implementation Plan: Local Development Server

## Overview

Implementasi FastAPI local development server yang menggantikan AWS API Gateway + Lambda
di lingkungan lokal. Stack: Python 3.11+, FastAPI, uvicorn. Semua file baru ditempatkan
di `backend/local_server/` tanpa menyentuh Lambda handlers yang sudah ada.

Urutan implementasi mengikuti dependency graph: setup → data layer → aplikasi → routers → tests → konfigurasi.

---

## Tasks

- [x] 1. Setup: dependencies, folder structure, dan mock data JSON
  - Tambahkan baris berikut ke `backend/requirements-dev.txt`:
    ```
    fastapi>=0.111.0
    uvicorn[standard]>=0.29.0
    openpyxl>=3.1.2
    reportlab>=4.2.0
    hypothesis>=6.100.0
    ```
  - Buat struktur folder `backend/local_server/` beserta sub-folder `routers/`, `mock_data/`, `exports/`
  - Buat file `backend/local_server/__init__.py` dan `backend/local_server/routers/__init__.py` (kosong)
  - Buat `backend/local_server/exports/.gitkeep` agar folder masuk Git
  - _Requirements: 1.1, 10.1, 10.6_

  - [x] 1.1 Buat `mock_data/campaigns.json`
    - 5 campaign records: C001–C005 dengan `campaign_id`, `nama_program`, `flag_program`,
      `jenis_leads`, `media_blasting`, `periode_start`, `periode_end`, `duration_days`
    - Mix: 3 × PROGRAM QRIS, 2 × PROGRAM BIAYA ADMIN; 4 media_blasting berbeda
    - _Requirements: 9.1, 9.2_

  - [x] 1.2 Buat `mock_data/leads.json`
    - ~150 lead records, masing-masing memiliki `campaign_id` (C001–C005)
    - **Tidak ada field `cif`** — sesuai Requirement 9.3
    - Variasi wajib: `wilayah` (min 5 distinct 1–17), `flag_program` (keduanya),
      `media_blasting` (min 4 dari 6), `segment_by_aum` (semua 6 tier),
      `range_usia` (semua 5 generasi), `take_up_flag` (~20% YES),
      `time_to_take_up_days` terdistribusi eksponensial (mayoritas 0–30 hari)
    - _Requirements: 9.2, 9.3, 9.4, 9.6_

  - [x] 1.3 Buat `mock_data/similarity_index.json`
    - Pre-computed similarity pairs; setiap entry: `campaign_id`, `similar_campaign_id`,
      `campaign_name`, `matching_dimensions`, `dimension_count`, `similarity_score`,
      `take_up_rate`, `total_leads`, `total_take_up`
    - Pasangan simetris (jika C001→C003 ada, C003→C001 juga ada)
    - Min 3 pasang berbagi 2+ dimensi
    - _Requirements: 9.5_

  - [x] 1.4 Buat `mock_data/trend_data.json`
    - Dict keyed by campaign_id; setiap campaign min 4 entries mingguan
    - Setiap entry: `period_start`, `period_end`, `total_leads`, `total_take_up`, `take_up_rate`
    - `take_up_rate` antara 5–35% agar realistis
    - _Requirements: 2.8, 9.4_

  - [x] 1.5 Buat `mock_data/regional_weekly.json`
    - Dict keyed by campaign_id; setiap wilayah yang muncul di leads.json punya min 4 weekly entries
    - Setiap entry: `wilayah`, `week_start`, `leads_count`, `take_up_count`, `take_up_rate`
    - Max 8 entries per wilayah akan dikembalikan API (sesuai Requirement 5.6)
    - _Requirements: 5.6_

- [x] 2. Implementasi `mock_store.py` — data loading dan query methods
  - Buat `backend/local_server/mock_store.py` dengan class `MockDataStore`
  - Load semua 5 file JSON saat import (module-level singleton `store = MockDataStore()`)
  - File header dengan docstring, `from __future__ import annotations`, Google-style docstrings
  - Implementasi method `get_leads()` dengan filtering AND logic:
    - `campaign_id`: exact match
    - `flag_program`: value in list
    - `media_blasting`: value in list
    - `wilayah`: value in list (int)
    - `jenis_leads`: value in list
    - `start_date`/`end_date`: filter berdasarkan `periode_start` field
  - Implementasi `get_campaign()`, `get_all_campaigns()`, `get_similarity_index()`,
    `get_trend_data()`, `get_regional_weekly()`
  - _Requirements: 2.3, 2.4, 2.5, 2.6, 9.1–9.6_

  - [x] 2.1 Tulis unit tests untuk `MockDataStore.get_leads()`
    - Test setiap filter type secara isolated (campaign_id, flag_program, media_blasting, wilayah, jenis_leads)
    - Test kombinasi 2+ filter sekaligus (AND logic)
    - Test date range filtering
    - File: `backend/tests/unit/test_mock_store.py`
    - _Requirements: 2.3, 2.4, 2.5, 2.6_

- [x] 3. Implementasi `main.py` — FastAPI app, CORS, health check, startup log
  - Buat `backend/local_server/main.py`
  - Instantiate `FastAPI(title="Local Dev Server")`
  - Register `CORSMiddleware` dengan `allow_origins=["*"]`, `allow_credentials=False`,
    `allow_methods=["*"]`, `allow_headers=["*"]`
  - Include `campaigns` dan `export` routers dengan prefix `/api`
  - Definisikan `GET /health` → `{"status": "ok", "mode": "local-dev"}`
  - Register `@app.on_event("startup")` untuk print startup log dengan port 8000 dan daftar endpoint
  - Handler 404 untuk unknown paths via `@app.exception_handler(404)` agar mengembalikan `{"detail": "Not found"}`
  - _Requirements: 1.1, 1.3, 1.4, 1.5, 1.6, 1.7_

  - [x] 3.1 Tulis unit tests untuk `main.py` (TestClient)
    - Test `GET /health` → 200, body `{"status": "ok", "mode": "local-dev"}`
    - Test unknown path → 404 JSON
    - Test CORS header hadir di response `GET /health`
    - Test preflight OPTIONS → 200
    - File: `backend/tests/unit/test_local_server_main.py`
    - _Requirements: 1.4, 1.5, 1.6, 1.7_

- [x] 4. Implementasi `routers/campaigns.py` — 6 campaign endpoints
  - Buat `backend/local_server/routers/campaigns.py`
  - Import: `store` dari `mock_store`, shared modules `calculations`, `pii_filter`, `sorting`, `models`
  - **Tidak import** `athena_client`, `auth`, `audit`, `rate_limiter`

  - [x] 4.1 Implementasi `GET /api/campaigns/overview`
    - Parse & validasi `start_date`/`end_date` (format yyyy-mm-dd) → 400 jika invalid
    - Filter leads via `store.get_leads()` dengan semua query params
    - Jika empty → return 200 `{"message": "Tidak ada data...", "filters": [...]}`
    - Hitung agregat via `calculate_take_up_rate`, count distinct campaign IDs
    - Ambil trend dari `store.get_trend_data()` (pre-aggregated)
    - Strip PII via `strip_pii`, build `filters` list via `ActiveFilter`
    - _Requirements: 2.1–2.9_

  - [x] 4.2 Implementasi `POST /api/campaigns/comparison`
    - Parse & validasi JSON body → 400 jika invalid/kosong
    - Validasi `campaign_ids` panjang 2–5 → 400 jika di luar range
    - Agregat leads per campaign, hitung metrics
    - Jika `group_by` ada → sort via `sort_by_attribute(ascending=True)`
    - Build `comparison_chart` format Chart.js
    - _Requirements: 3.1–3.7_

  - [x] 4.3 Implementasi `GET /api/campaigns/time-analysis/{campaign_id}`
    - Validasi `campaign_id` tidak kosong → 400
    - Load leads dimana `take_up_flag == "YES"`, apply optional channel/region filter
    - Jika kosong → return 200 `{"message": "Belum ada data take up..."}`
    - Build histogram 7 bins [0-7, 7-14, 14-21, 21-30, 30-60, 60-90, 90+] via `_build_histogram()`
    - Hitung stats via `compute_statistics`
    - _Requirements: 4.1–4.7_

  - [x] 4.4 Implementasi `GET /api/campaigns/regional/{campaign_id}`
    - Load leads untuk campaign, optional filter `flag_program`
    - Jika kosong → return 200 dengan message dan `regions: []`
    - Group by `wilayah`, hitung per-region metrics
    - Sort via `sort_regional_performance` (descending by `take_up_rate`)
    - Jika `selected_region` ada → load `regional_weekly.json`, return ≤ 8 entries
    - _Requirements: 5.1–5.6_

  - [x] 4.5 Implementasi `GET /api/campaigns/customer-criteria/{campaign_id}`
    - Validasi `campaign_id` → 400 jika kosong
    - Load semua leads untuk campaign, strip PII via `strip_pii` sebelum processing
    - Jika kosong → return 200 dengan message
    - Untuk 5 atribut (`segment_by_aum`, `range_usia`, `media_blasting`, `segment_div_owner`, `flag_program`):
      build distribution via `compute_distribution_percentages`
    - Mark unavailable jika semua values null/empty
    - _Requirements: 6.1–6.7_

  - [x] 4.6 Implementasi `POST /api/campaigns/similar`
    - Parse & validasi body: `reference_campaign_id`, `dimensions` (wajib ada, non-empty)
    - Validasi dimensions terhadap `SIMILAR_CAMPAIGN_DIMENSIONS` → 400 jika ada yang invalid
    - Load `similarity_index.json` dimana `campaign_id == reference_campaign_id`
    - Filter: keep entries dimana semua requested dimensions ada di `matching_dimensions`
    - Sort via `sort_similar_campaigns` (dimension_count desc, take_up_rate desc)
    - Apply `min(limit, 20)` cap
    - Jika kosong → return 200 `{"similar_campaigns": [], "message": "..."}`
    - _Requirements: 7.1–7.7_

  - [x] 4.7 Tulis unit tests untuk `routers/campaigns.py` (TestClient)
    - Overview: test tanpa params, test invalid date, test setiap filter, test empty result
    - Comparison: test valid 2 IDs, test < 2 IDs → 400, test > 5 IDs → 400, test group_by sort
    - Time analysis: test histogram 7 bins, test empty campaign, test channel/region filter
    - Regional: test sort descending, test selected_region, test empty regions
    - Customer criteria: test 5 distribusi hadir, test kosong campaign_id → 400
    - Similar: test invalid dimensions → 400, test sort order, test limit cap
    - File: `backend/tests/unit/test_local_server_campaigns.py`
    - _Requirements: 2.1–7.7_

- [x] 5. Checkpoint — Verifikasi campaigns router
  - Pastikan semua file tidak ada error diagnostics (`get_diagnostics` pada semua file baru)
  - Pastikan semua unit tests di `test_local_server_campaigns.py` pass (jalankan secara manual jika Python tersedia)
  - Tanyakan ke user jika ada pertanyaan sebelum lanjut ke export router

- [x] 6. Implementasi `routers/export.py` — export endpoint dan file serving
  - Buat `backend/local_server/routers/export.py`

  - [x] 6.1 Implementasi helper `_generate_csv()`, `_generate_excel()`, `_generate_pdf()`
    - Adapt logika dari `lambdas/export_service/handler.py` (tanpa S3)
    - CSV: tulis baris metadata `#source`, `#period`, `#filters` di atas
    - Excel: gunakan `openpyxl` untuk format `.xlsx`
    - PDF: gunakan `reportlab` untuk format `.pdf`
    - _Requirements: 8.1, 8.2, 8.3, 8.7_

  - [x] 6.2 Implementasi `POST /api/export`
    - Parse & validasi `ExportRequest` dari `shared.models` → 400 jika invalid/kosong
    - Validasi `format` in `{"csv", "excel", "pdf"}` → 400 jika selain itu
    - Generate file via helper yang sesuai
    - Simpan ke `backend/local_server/exports/{uuid}.{ext}`
    - Return `{"status": "completed", "download_url": "/exports/{filename}"}`
    - _Requirements: 8.1–8.6_

  - [x] 6.3 Implementasi `GET /exports/{filename}`
    - Serve file via `FileResponse` dari direktori `exports/`
    - Return 404 jika file tidak ditemukan (`{"detail": "Export file not found"}`)
    - _Requirements: 8.4_

  - [ ]* 6.4 Tulis unit tests untuk `routers/export.py` (TestClient)
    - Test POST /api/export dengan format csv/excel/pdf → 200, `status: "completed"`
    - Test `download_url` pattern `/exports/{filename}.{ext}`
    - Test format tidak valid → 400
    - Test body kosong → 400
    - Test GET /exports/{filename} → file response
    - Test GET /exports/nonexistent → 404
    - File: `backend/tests/unit/test_local_server_export.py`
    - _Requirements: 8.1–8.7_

- [x] 7. Tulis property-based tests (Hypothesis)
  - File: `backend/tests/property/test_local_server_properties.py`
  - Import: `from hypothesis import given, settings, strategies as st`
  - Setiap test dengan `@settings(max_examples=100)`
  - Tag format: `# Feature: local-dev-server, Property N: <property_text>`

  - [x]* 7.1 Property 3: Invalid date parameters return 400
    - **Property 3: Invalid date parameters always return 400**
    - Generate arbitrary strings yang bukan format valid `yyyy-mm-dd`
    - Hit `GET /api/campaigns/overview?start_date={invalid}`
    - Assert response.status_code == 400
    - **Validates: Requirements 2.2**

  - [x]* 7.2 Property 4: Filter predicates respects AND semantics
    - **Property 4: Filter predicates are respected**
    - Generate random subset dari valid `flag_program` dan `media_blasting` values
    - Hit overview endpoint dengan filter tersebut
    - Assert semua lead records dalam response memenuhi SEMUA active filter (AND logic)
    - **Validates: Requirements 2.3, 2.4, 2.5, 2.6**

  - [x]* 7.3 Property 5: Trend array is chronologically ordered
    - **Property 5: Trend array is chronologically ordered and non-trivially populated**
    - Hit `GET /api/campaigns/overview` tanpa filter
    - Assert `len(trend) >= 4`
    - Assert `trend[i].period_start <= trend[i+1].period_start` untuk semua i
    - **Validates: Requirements 2.8**

  - [x]* 7.4 Property 6: No cif in any response
    - **Property 6: No cif or PII in any response**
    - Generate random request params untuk setiap endpoint
    - Assert response JSON (rekursif) tidak mengandung key `"cif"` di level manapun
    - **Validates: Requirements 2.9, 6.7, 9.3**

  - [x]* 7.5 Property 10: Histogram always has exactly 7 bins
    - **Property 10: Histogram always has exactly 7 bins with correct ranges**
    - Generate random list of non-negative integers sebagai `time_to_take_up_days`
    - Call `_build_histogram(values)` langsung (unit test pada helper function)
    - Assert `len(result) == 7`
    - Assert `range_start` values = `[0, 7, 14, 21, 30, 60, 90]`
    - Assert `sum(bin.count for bin in result) == len(values)`
    - **Validates: Requirements 4.3**

  - [x]* 7.6 Property 11: Statistics invariant max >= min >= 0
    - **Property 11: Statistics invariant — max >= min and all non-negative**
    - Generate non-empty list of non-negative integers
    - Call `compute_statistics(values)` dari `shared.calculations`
    - Assert `max_days >= min_days >= 0`
    - Assert `mean_days >= 0`, `median_days >= 0`
    - Assert `total_take_up == len(values)`
    - **Validates: Requirements 4.4**

  - [x]* 7.7 Property 12: Regions sorted descending by take_up_rate
    - **Property 12: Regions sorted descending by take_up_rate**
    - Generate random list of region dicts dengan `take_up_rate` field
    - Call `sort_regional_performance(regions)` dari `shared.sorting`
    - Assert `result[i]["take_up_rate"] >= result[i+1]["take_up_rate"]` untuk semua adjacent pairs
    - **Validates: Requirements 5.3**

  - [x]* 7.8 Property 14: Distribution percentages sum to 100
    - **Property 14: Distribution items contain required fields and sum to 100%**
    - Generate random group counts (dict of label → count)
    - Call `compute_distribution_percentages(data, group_by_field)` dari `shared.calculations`
    - Assert setiap item mengandung: `label`, `count`, `percentage`, `take_up_count`, `take_up_percentage`
    - Assert `sum(item.percentage for item in items) ≈ 100.0` (tolerance 0.01)
    - **Validates: Requirements 6.3, 6.4**

  - [x]* 7.9 Property 16: Similar campaigns sorted by dimension_count desc then take_up_rate desc
    - **Property 16: similar_campaigns sorted by dimension_count desc then take_up_rate desc**
    - Generate random list of `SimilarCampaignResult` objects
    - Call `sort_similar_campaigns(results)` dari `shared.sorting`
    - Assert untuk semua adjacent pairs: `result[i].dimension_count >= result[i+1].dimension_count`
    - Assert jika `dimension_count` sama: `result[i].take_up_rate >= result[i+1].take_up_rate`
    - **Validates: Requirements 7.5**

  - [x]* 7.10 Property 17: similar_campaigns length bounded by min(limit, 20)
    - **Property 17: similar_campaigns length bounded by min(limit, 20)**
    - Generate random `limit` values antara 1–100
    - Hit `POST /api/campaigns/similar` dengan valid reference_id dan generated limit
    - Assert `len(response["similar_campaigns"]) <= min(limit, 20)`
    - **Validates: Requirements 7.6**

- [x] 8. Checkpoint — Verifikasi semua tests
  - Pastikan semua file tidak ada error dari `get_diagnostics`
  - Pastikan tidak ada import dari `athena_client`, `auth`, `audit`, `rate_limiter`
    di semua file `local_server/`
  - Jalankan test suite secara manual jika Python tersedia: `cd backend && python -m pytest tests/ -v`
  - Tanyakan ke user jika ada pertanyaan sebelum lanjut ke konfigurasi

- [x] 9. Konfigurasi: npm scripts, `.env.local`, dan `.gitignore`
  - [x] 9.1 Buat atau update root `package.json` dengan npm scripts
    - Tambahkan script `"dev:backend"`, `"dev:frontend"`, dan `"dev"` (dengan `concurrently`)
    - Gunakan format yang kompatibel Windows PowerShell
    - Tambahkan `concurrently` sebagai devDependency jika belum ada
    - _Requirements: 1.2, 10.5_

  - [x] 9.2 Buat `frontend/.env.local`
    - Isi: `REACT_APP_API_URL=http://localhost:8000`
    - Jika sudah ada, tambahkan/update hanya baris `REACT_APP_API_URL`
    - _Requirements: frontend connectivity_

  - [x] 9.3 Update `.gitignore` untuk exports directory
    - Pastikan `backend/local_server/exports/*.csv`,
      `backend/local_server/exports/*.xlsx`,
      `backend/local_server/exports/*.pdf` sudah ter-ignore
    - Jaga agar `exports/.gitkeep` tetap tracked
    - _Requirements: 10.1_

- [x] 10. Final checkpoint — Verifikasi end-to-end
  - Pastikan semua file `backend/local_server/` bisa di-import tanpa error (`get_diagnostics`)
  - Pastikan `backend/requirements-dev.txt` sudah diupdate dengan dependencies baru
  - Verifikasi bahwa tidak ada Lambda handler yang dimodifikasi (baca setiap file di `backend/lambdas/` untuk konfirmasi)
  - Buat dokumentasi di `docs/task-local-dev-server.md` sesuai format auto-documentation
  - Tanyakan ke user jika ada hal yang perlu dikonfirmasi sebelum dinyatakan selesai

---

## Notes

- Tasks bertanda `*` adalah opsional (tests) — bisa di-skip untuk MVP lebih cepat
- Semua kode Python mengikuti konvensi di `backend-conventions.md`:
  - File header dengan docstring + `from __future__ import annotations`
  - Google-style docstrings pada semua public functions
  - Non-mutating functions untuk sort/transform
- **Python tidak tersedia di PATH sistem** — verifikasi dengan `get_diagnostics` bukan `python -m pytest`
- Import shared modules: `from shared.calculations import ...` (asumsi `backend/` ada di PYTHONPATH)
- **Jangan import**: `shared.athena_client`, `shared.auth`, `shared.audit`, `shared.rate_limiter`
- Property-based tests menggunakan Hypothesis dengan `@settings(max_examples=100)`
- Setiap property test diberi tag komentar: `# Feature: local-dev-server, Property N: <text>`
- Properties 1, 2, 7, 8, 9, 13, 15, 18, 19 diverifikasi via example-based tests (TestClient)

## Task Dependency Graph

```json
{
  "waves": [
    {
      "wave": 1,
      "description": "Setup: dependencies, folder structure, dan semua mock data JSON",
      "tasks": ["1", "1.1", "1.2", "1.3", "1.4", "1.5"]
    },
    {
      "wave": 2,
      "description": "Data layer: MockDataStore dengan semua query methods",
      "tasks": ["2", "2.1"]
    },
    {
      "wave": 3,
      "description": "App entry point: FastAPI app, CORS, health check, startup log",
      "tasks": ["3", "3.1"]
    },
    {
      "wave": 4,
      "description": "Campaign endpoints: 6 routes di routers/campaigns.py",
      "tasks": ["4", "4.1", "4.2", "4.3", "4.4", "4.5", "4.6", "4.7"]
    },
    {
      "wave": 5,
      "description": "Checkpoint: verifikasi campaigns router sebelum export",
      "tasks": ["5"]
    },
    {
      "wave": 6,
      "description": "Export endpoint: file generators, POST /api/export, GET /exports/{filename}",
      "tasks": ["6", "6.1", "6.2", "6.3", "6.4"]
    },
    {
      "wave": 7,
      "description": "Property-based tests dengan Hypothesis (semua opsional)",
      "tasks": ["7", "7.1", "7.2", "7.3", "7.4", "7.5", "7.6", "7.7", "7.8", "7.9", "7.10"]
    },
    {
      "wave": 8,
      "description": "Checkpoint: verifikasi semua tests dan diagnostics",
      "tasks": ["8"]
    },
    {
      "wave": 9,
      "description": "Konfigurasi: npm scripts, .env.local, .gitignore",
      "tasks": ["9", "9.1", "9.2", "9.3"]
    },
    {
      "wave": 10,
      "description": "Final checkpoint: end-to-end verification dan dokumentasi",
      "tasks": ["10"]
    }
  ]
}
```
