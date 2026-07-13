# Local Dev Server — Dokumentasi Lengkap End-to-End

## Ringkasan Singkat

Fitur ini menyediakan sebuah FastAPI server yang berjalan di laptop lokal pada `http://localhost:8000`, menggantikan seluruh stack AWS (API Gateway + Lambda + Athena + DynamoDB) saat development. Developer dapat menjalankan frontend React dan backend Python secara bersamaan di laptop, tanpa koneksi cloud, menggunakan data dummy JSON yang representatif. Semua 8 API endpoint identik dengan Lambda handlers yang ada di production. Lambda handlers yang sudah ada **tidak dimodifikasi sama sekali**.

---

## Penjelasan Awam (Non-Technical)

Bayangkan sebuah restoran besar yang biasanya mendapatkan bahan baku segar dari supplier jauh. Setiap kali chef baru ingin berlatih, ia harus memesan bahan dari supplier tersebut — mahal, lambat, dan tidak bisa dilakukan sewaktu-waktu.

Local Dev Server adalah solusi "dapur latihan pribadi": ia menyediakan tiruan bahan makanan (data dummy JSON) yang mirip persis dengan bahan aslinya, sehingga chef (developer) bisa berlatih memasak (membangun fitur) kapan saja di dapur sendiri (laptop), tanpa menghubungi supplier (AWS).

Manfaat konkret bagi tim:
- **Lebih cepat**: tidak perlu menunggu koneksi AWS atau query Athena yang bisa memakan waktu 5-30 detik
- **Lebih aman**: tidak ada risiko menggunakan data nasabah sungguhan saat testing
- **Lebih mandiri**: bisa bekerja di mana saja, termasuk offline atau di jaringan yang lambat
- **Zero cost**: tidak ada biaya AWS yang terpakai selama development dan testing

---

## Penjelasan Teknis

### File yang Dibuat (Ringkasan Lengkap)

| File | Deskripsi |
|------|-----------|
| `backend/local_server/__init__.py` | Package init kosong |
| `backend/local_server/main.py` | FastAPI app, CORS, health check, startup log, JSON 404 |
| `backend/local_server/mock_store.py` | `MockDataStore` — load JSON, 6 query methods, singleton |
| `backend/local_server/routers/__init__.py` | Sub-package init kosong |
| `backend/local_server/routers/campaigns.py` | 6 campaign endpoint handlers |
| `backend/local_server/routers/export.py` | POST /api/export + GET /exports/{filename} |
| `backend/local_server/mock_data/campaigns.json` | 5 campaign master records |
| `backend/local_server/mock_data/leads.json` | ~150 lead records tanpa PII (no `cif`) |
| `backend/local_server/mock_data/similarity_index.json` | Pre-computed similarity pairs (simetris) |
| `backend/local_server/mock_data/trend_data.json` | Weekly trend aggregates per campaign |
| `backend/local_server/mock_data/regional_weekly.json` | Per-wilayah weekly data per campaign |
| `backend/local_server/exports/.gitkeep` | Folder exports ter-track Git |
| `backend/requirements-dev.txt` | Ditambahkan: FastAPI, uvicorn, openpyxl, reportlab, hypothesis |
| `package.json` (root) | npm scripts: `dev:backend`, `dev:frontend`, `dev` |
| `frontend/.env.local` | `REACT_APP_API_URL=http://localhost:8000` |

### File yang TIDAK Dimodifikasi (Verifikasi)

Seluruh Lambda handler di `backend/lambdas/` **tidak berubah** — sesuai Requirement 10.2:

| File | Import Utama | Status |
|------|-------------|--------|
| `lambdas/campaign_overview/handler.py` | `shared.athena_client`, `shared.calculations` | Tidak dimodifikasi |
| `lambdas/campaign_comparison/handler.py` | `shared.athena_client`, `shared.sorting` | Tidak dimodifikasi |
| `lambdas/time_analysis/handler.py` | `shared.athena_client`, `shared.calculations` | Tidak dimodifikasi |
| `lambdas/regional_performance/handler.py` | `shared.athena_client`, `shared.sorting` | Tidak dimodifikasi |
| `lambdas/customer_criteria/handler.py` | `shared.athena_client`, `shared.calculations` | Tidak dimodifikasi |
| `lambdas/similar_campaign/handler.py` | `boto3` (DynamoDB), `shared.models` | Tidak dimodifikasi |
| `lambdas/export_service/handler.py` | `boto3` (S3), `shared.models` | Tidak dimodifikasi |

Tidak ada satu pun file Lambda yang mengimport `local_server`, `mock_store`, atau `MockDataStore`.

### Library/Framework yang Digunakan

- **FastAPI ≥ 0.111.0** — ASGI web framework, routing, dependency injection, request/response handling
- **uvicorn[standard] ≥ 0.29.0** — ASGI server dengan fitur hot-reload
- **openpyxl ≥ 3.1.2** — generate file `.xlsx` (Excel) di export endpoint
- **reportlab ≥ 4.2.0** — generate file `.pdf` di export endpoint
- **hypothesis ≥ 6.100.0** — property-based testing (sudah ada di requirements sebelumnya)
- **Shared modules reused**: `shared.calculations`, `shared.models`, `shared.pii_filter`, `shared.sorting`
- **NOT imported**: `shared.athena_client`, `shared.auth`, `shared.audit`, `shared.rate_limiter` (AWS-dependent)

### Pola Arsitektur yang Diterapkan

1. **Router separation** — `main.py` hanya assembly (wiring). Business logic di `campaigns.py` dan `export.py`.
2. **Module-level singleton** — `store = MockDataStore()` dibuat satu kali saat import. Semua router share instance yang sama.
3. **Eager loading** — semua 5 file JSON dimuat di `__init__`, bukan per-request. Query murni in-memory.
4. **AND logic filtering** — `get_leads()` menggunakan `continue` per filter: semua predikat aktif harus terpenuhi.
5. **Non-mutating methods** — semua sort/transform mengembalikan collection baru, tidak pernah mutate input.
6. **No AWS imports** — semua modul `local_server/` bersih dari boto3, athena_client, auth, audit, rate_limiter.

---

## Struktur Lengkap Folder

```
backend/
└── local_server/
    ├── __init__.py              # Package init
    ├── main.py                  # FastAPI app, CORS, health check, startup log, 404 handler
    ├── mock_store.py            # MockDataStore class + singleton `store`
    ├── routers/
    │   ├── __init__.py
    │   ├── campaigns.py         # 6 campaign endpoint handlers
    │   └── export.py            # POST /api/export + GET /exports/{filename}
    ├── mock_data/
    │   ├── campaigns.json       # 5 campaign master records (C001–C005)
    │   ├── leads.json           # ~150 lead records (tanpa cif)
    │   ├── similarity_index.json  # Pre-computed similarity pairs
    │   ├── trend_data.json      # Weekly trend aggregates per campaign
    │   └── regional_weekly.json # Weekly per-wilayah data per campaign
    └── exports/
        └── .gitkeep             # Generated export files (gitignored by extension)
```

---

## API Endpoints yang Diimplementasi

| Method | Path | Deskripsi | Requirements |
|--------|------|-----------|-------------|
| GET | `/health` | Health check — `{"status": "ok", "mode": "local-dev"}` | 1.4 |
| GET | `/api/campaigns/overview` | Agregat metrics + trend + filters | 2.1–2.9 |
| POST | `/api/campaigns/comparison` | Perbandingan 2–5 campaigns + Chart.js data | 3.1–3.7 |
| GET | `/api/campaigns/time-analysis/{id}` | Histogram 7 bins + statistik take-up | 4.1–4.7 |
| GET | `/api/campaigns/regional/{id}` | Per-region metrics sorted desc + weekly trend | 5.1–5.6 |
| GET | `/api/campaigns/customer-criteria/{id}` | Distribusi 5 atribut demografis | 6.1–6.7 |
| POST | `/api/campaigns/similar` | Campaign serupa berdasarkan dimensi | 7.1–7.7 |
| POST | `/api/export` | Generate CSV/Excel/PDF, simpan lokal, return `download_url` | 8.1–8.7 |
| GET | `/exports/{filename}` | Serve file yang sudah digenerate via `FileResponse` | 8.4 |

---

## Komponen Utama — Penjelasan Detail

### `main.py` — Entry Point

```python
# CORS wildcard (allow_credentials=False wajib saat allow_origins=["*"])
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=False, ...)

# Router campaigns: routes relatif → prefix "/api" di include_router
app.include_router(campaigns.router, prefix="/api")

# Router export: routes absolut (/api/export, /exports/{fn}) → tanpa prefix
app.include_router(export.router)

# Override HTML 404 → JSON 404
@app.exception_handler(404)
async def not_found_handler(...) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": "Not found"})
```

**Keputusan kritis**: export router di-include **tanpa prefix** karena routes-nya sudah mengandung `/api/` secara internal. Menambahkan prefix `/api` akan menghasilkan `/api/api/export`.

### `mock_store.py` — Data Layer

```python
class MockDataStore:
    def get_leads(self, campaign_id, flag_program, media_blasting,
                  wilayah, jenis_leads, start_date, end_date) -> list[dict]:
        # AND logic: semua filter aktif harus terpenuhi
        # Date filtering: string comparison yyyy-mm-dd (lexicographic = chronological)
        # wilayah filtering: int comparison (bukan string)

    def get_campaign(self, campaign_id) -> dict | None: ...
    def get_all_campaigns(self) -> list[dict]: ...
    def get_similarity_index(self, reference_id) -> list[dict]: ...
    def get_trend_data(self, campaign_id) -> list[dict]: ...
    def get_regional_weekly(self, campaign_id) -> list[dict]: ...

store = MockDataStore()  # Singleton — load sekali saat import
```

### `routers/campaigns.py` — 6 Campaign Endpoints

Helper functions internal:
- `_validate_date(raw, field_name)` → raise 400 jika bukan format `yyyy-mm-dd`
- `_parse_string_list(raw)` → parse comma-separated string → list[str] | None
- `_parse_int_list(raw)` → parse comma-separated integers → list[int] | None
- `_build_active_filters(...)` → list[ActiveFilter] untuk response payload
- `_build_histogram(days_list)` → 7 bins: [0-7, 7-14, 14-21, 21-30, 30-60, 60-90, 90+]
- `_build_attribute_distribution(rows, attribute)` → distribusi per-atribut dengan `compute_distribution_percentages`
- `_build_chart(campaigns)` → Chart.js-compatible `labels` + `datasets`

Semua handler menggunakan `strip_pii(body)` sebelum mengembalikan response.

### `routers/export.py` — Export Endpoint

File generators:
- `_generate_csv(request)` → bytes: metadata komentar `#source`, `#period`, `#filters` + header + placeholder row
- `_generate_excel(request)` → bytes: workbook 2 sheet (Metadata + Data) via `openpyxl`
- `_generate_pdf(request)` → bytes: dokumen A4 dengan tabel metadata + data via `reportlab`

Flow POST /api/export:
1. Parse + validasi body (manual karena `ExportRequest` adalah dataclass, bukan Pydantic)
2. Validate `format` in `{"csv", "excel", "pdf"}`
3. Generate file bytes
4. Simpan ke `backend/local_server/exports/{uuid}.{ext}`
5. Return `{"status": "completed", "download_url": "/exports/{filename}"}`

---

## Mock Data — Spesifikasi

### campaigns.json (5 records)

| ID | Nama Program | Flag Program | Media | Jenis Leads | Durasi |
|----|-------------|--------------|-------|-------------|--------|
| C001 | Cashback QRIS Agustus 2024 | PROGRAM QRIS | wa | Akuisisi | 30 hari |
| C002 | Migrasi Biaya Admin Q3 2024 | PROGRAM BIAYA ADMIN | telesales | Migrasi | 91 hari |
| C003 | Digisales QRIS Nasabah Mass | PROGRAM QRIS | digisales | Akuisisi | 29 hari |
| C004 | WA Blast Biaya Admin Emerald | PROGRAM BIAYA ADMIN | wa | Migrasi | 30 hari |
| C005 | Email QRIS Nasabah Affluent | PROGRAM QRIS | email | Retensi | 29 hari |

### leads.json (~150 records)

Variasi yang dipenuhi:
- `wilayah`: 7 distinct values (1, 3, 5, 7, 9, 11, 13) — lebih dari minimum 5
- `segment_by_aum`: semua 6 tier (UPPERMASS, EMERALD, MASS, AFFLUENT, PRIVATE, HIGH AFFLUENT)
- `range_usia`: semua 5 generasi (BABY BOOMER, GEN X, GEN Y, GEN Z, GEN ALPHA)
- `media_blasting`: 4 dari 6 nilai valid (wa, telesales, digisales, email)
- `take_up_flag`: ~20% YES (~30 dari 150 records)
- `time_to_take_up_days`: distribusi mayoritas 0–30 hari (eksponensial-like)
- **Tidak ada field `cif`** — sesuai Req 9.3

### similarity_index.json

Pasangan simetris: jika C001→C003 ada, C003→C001 juga ada.
Minimal 3 pasang berbagi 2+ dimensi (`flag_program` + `jenis_leads` sebagai tiebreaker).

### trend_data.json

Dict keyed by campaign_id. Setiap campaign: minimal 4 weekly entries.
`take_up_rate` antara 5–35% sesuai Req 9.4.

### regional_weekly.json

Dict keyed by campaign_id. Setiap wilayah yang ada di leads.json: minimal 4 weekly entries.
API mengembalikan maksimal 8 entries per `selected_region` request.

---

## Simulasi / Skenario

### Skenario 1 — Menjalankan Server

```bash
# Dari root project
npm run dev:backend

# Atau langsung dari backend/
cd backend
uvicorn local_server.main:app --reload --port 8000
```

Output terminal:
```
=== Local Dev Server started on http://localhost:8000 ===
Available endpoints:
  GET  /health
  GET  /api/campaigns/overview
  POST /api/campaigns/comparison
  GET  /api/campaigns/time-analysis/{campaign_id}
  GET  /api/campaigns/regional/{campaign_id}
  GET  /api/campaigns/customer-criteria/{campaign_id}
  POST /api/campaigns/similar
  POST /api/export
  GET  /exports/{filename}
```

### Skenario 2 — Overview dengan Filter

```
Request:  GET /api/campaigns/overview?flag_program=PROGRAM+QRIS&wilayah=1,3
Response: HTTP 200
{
  "total_leads": 36,
  "total_take_up": 7,
  "take_up_rate": 19.44,
  "total_campaigns": 3,
  "trend": [
    {"period_start": "2024-08-01", "period_end": "2024-08-07",
     "total_leads": 12, "total_take_up": 2, "take_up_rate": 16.67},
    ...  // >= 4 data points
  ],
  "filters": [
    {"field": "flag_program", "values": ["PROGRAM QRIS"]},
    {"field": "wilayah", "values": ["1", "3"]}
  ]
}
```

### Skenario 3 — Export CSV dan Download

```
Request:  POST /api/export
Body: {
  "page": "campaign_overview",
  "format": "csv",
  "filters": [{"field": "flag_program", "values": ["PROGRAM QRIS"]}],
  "time_range_start": "2024-08-01",
  "time_range_end": "2024-08-31"
}
Response: HTTP 200
{"status": "completed", "download_url": "/exports/a1b2c3d4-...-uuid.csv"}

# Download file
GET /exports/a1b2c3d4-...-uuid.csv
Response: CSV file dengan konten:
# source: campaign_overview
# period: 2024-08-01 to 2024-08-31
# filters: flag_program=PROGRAM QRIS
nama_program,flag_program,media_blasting,...
N/A (MVP placeholder),N/A,...
```

### Skenario 4 — Error Handling

```
# Invalid date format
GET /api/campaigns/overview?start_date=31-08-2024
→ HTTP 400 {"detail": "Parameter tanggal tidak valid: '31-08-2024' untuk 'start_date'. Gunakan format yyyy-mm-dd."}

# Terlalu banyak campaign IDs
POST /api/campaigns/comparison {"campaign_ids": ["C001","C002","C003","C004","C005","C006"]}
→ HTTP 400 {"detail": "campaign_ids must contain at most 5 campaign identifiers, got 6."}

# Unknown path
GET /api/nonexistent
→ HTTP 404 {"detail": "Not found"}

# Campaign tanpa data
GET /api/campaigns/customer-criteria/C999
→ HTTP 200 {"campaign_id": "C999", "message": "Tidak ada data karakteristik nasabah untuk campaign ini."}
```

### Skenario 5 — Full Stack (Frontend + Backend)

```bash
# Terminal 1: Backend
npm run dev:backend
# → Listening at http://localhost:8000

# Terminal 2: Frontend
npm run dev:frontend
# → App di http://localhost:3000
# → Axios mengirim request ke REACT_APP_API_URL=http://localhost:8000
```

Frontend React membaca `REACT_APP_API_URL` dari `frontend/.env.local` dan mengarahkan semua request API ke `http://localhost:8000` alih-alih production AWS endpoint.

---

## Keterkaitan dengan Komponen Lain

**Bergantung pada:**
- `backend/shared/calculations.py` — `calculate_take_up_rate`, `compute_statistics`, `compute_distribution_percentages`
- `backend/shared/models.py` — dataclasses: `CampaignMetric`, `SimilarCampaignResult`, `ActiveFilter`, `ExportRequest`; konstanta: `SIMILAR_CAMPAIGN_DIMENSIONS`
- `backend/shared/pii_filter.py` — `strip_pii` pada semua response
- `backend/shared/sorting.py` — `sort_by_attribute`, `sort_regional_performance`, `sort_similar_campaigns`

**Digunakan oleh:**
- Frontend React (`frontend/src/`) via axios ke `http://localhost:8000`
- Developer saat local testing dan manual QA
- `backend/tests/unit/test_local_server_*.py` via `TestClient`
- `backend/tests/property/test_local_server_properties.py` via Hypothesis

**Tidak bergantung pada** (sesuai Req 10.4):
- `shared/athena_client.py` — AWS Athena SDK
- `shared/auth.py` — AWS Cognito
- `shared/audit.py` — CloudWatch
- `shared/rate_limiter.py` — DynamoDB

**Pengaruh ke:**
- Perubahan field di JSON mock data → perlu update router yang membaca field tersebut
- Perubahan prefix routing di `main.py` → perlu update frontend `.env.local` dan tests
- Penambahan endpoint baru → perlu update `startup_log` dan `package.json` scripts

---

## Requirements yang Dipenuhi

| Requirement | Deskripsi | Status |
|-------------|-----------|--------|
| 1.1 | Server dapat dijalankan dengan `uvicorn local_server.main:app --reload --port 8000` | ✅ |
| 1.2 | npm script `dev:backend` tersedia di root `package.json` | ✅ |
| 1.3 | Startup log menyebutkan port 8000 dan daftar semua endpoint | ✅ |
| 1.4 | `GET /health` → HTTP 200 `{"status": "ok", "mode": "local-dev"}` | ✅ |
| 1.5 | Path tidak dikenal → HTTP 404 JSON `{"detail": "Not found"}` | ✅ |
| 1.6 | Header `Access-Control-Allow-Origin: *` di setiap response | ✅ |
| 1.7 | Preflight OPTIONS → HTTP 200 dengan header CORS lengkap | ✅ |
| 2.1–2.9 | Campaign Overview endpoint dengan semua filter dan validasi | ✅ |
| 3.1–3.7 | Campaign Comparison endpoint, validasi 2–5 IDs, Chart.js | ✅ |
| 4.1–4.7 | Time Analysis endpoint, histogram 7 bins, statistik | ✅ |
| 5.1–5.6 | Regional Performance endpoint, sort desc, weekly trend ≤ 8 | ✅ |
| 6.1–6.7 | Customer Criteria endpoint, 5 distribusi, no PII | ✅ |
| 7.1–7.7 | Similar Campaign endpoint, validasi dimensi, sort, limit | ✅ |
| 8.1–8.7 | Export endpoint CSV/Excel/PDF, local file serving, metadata CSV | ✅ |
| 9.1 | 5 campaign ID unik (C001–C005) dengan nama representatif | ✅ |
| 9.2 | Variasi wilayah (≥5), media_blasting (≥4), segment, range_usia | ✅ |
| 9.3 | Tidak ada field `cif` di mock data maupun API response | ✅ |
| 9.4 | take_up_rate antara 5–35% di trend_data.json | ✅ |
| 9.5 | Min 3 pasang campaign berbagi 2+ dimensi di similarity_index.json | ✅ |
| 9.6 | time_to_take_up_days mayoritas 0–30 hari | ✅ |
| 10.1 | Local server di `backend/local_server/` terpisah dari `backend/lambdas/` | ✅ |
| 10.2 | Lambda handlers tidak diimport atau dimodifikasi | ✅ |
| 10.3 | Modul shared non-AWS digunakan (calculations, models, pii_filter, sorting) | ✅ |
| 10.4 | Tidak ada import `athena_client`, `auth`, `audit`, `rate_limiter` | ✅ |
| 10.5 | npm script `dev:backend` tersedia | ✅ |
| 10.6 | FastAPI/uvicorn/openpyxl/reportlab masuk `requirements-dev.txt`, bukan `requirements.txt` | ✅ |

---

## Verifikasi Final (Task 10 Checkpoint)

### Diagnostics `get_diagnostics` — Semua File Local Server

| File | Status Diagnostics |
|------|-------------------|
| `backend/local_server/__init__.py` | ✅ No diagnostics found |
| `backend/local_server/main.py` | ✅ No diagnostics found |
| `backend/local_server/mock_store.py` | ✅ No diagnostics found |
| `backend/local_server/routers/__init__.py` | ✅ No diagnostics found |
| `backend/local_server/routers/campaigns.py` | ✅ No diagnostics found |
| `backend/local_server/routers/export.py` | ✅ No diagnostics found |

### `backend/requirements-dev.txt` — Dependencies Verifikasi

```
-r requirements.txt
pytest
hypothesis>=6.100.0
moto[all]
pytest-cov
pytest-mock
fastapi>=0.111.0
uvicorn[standard]>=0.29.0
openpyxl>=3.1.2
reportlab>=4.2.0
```

Semua 5 dependency yang diperlukan hadir: `fastapi>=0.111.0`, `uvicorn[standard]>=0.29.0`, `openpyxl>=3.1.2`, `reportlab>=4.2.0`, `hypothesis>=6.100.0`. ✅

### Lambda Handler Verification

`grep_search` untuk `local_server|mock_store|MockDataStore` pada semua file di `backend/lambdas/` → **No matches found**. Lambda handlers murni menggunakan `shared.athena_client`, `boto3`, dan shared modules non-AWS. ✅

---

## Catatan Penting

1. **Python tidak tersedia di PATH sistem** — verifikasi menggunakan `get_diagnostics` (Pylance language server). Untuk menjalankan test suite secara aktual: install Python dari python.org → `cd backend && python -m pytest tests/ -v`.

2. **Export router tanpa prefix** — `app.include_router(export.router)` dipanggil tanpa argumen `prefix`. Ini disengaja karena route `/api/export` dan `/exports/{filename}` sudah didefinisikan secara absolut di dalam router.

3. **Singleton thread-safe** — `store = MockDataStore()` aman di concurrent FastAPI karena data hanya dibaca setelah `__init__`, tidak pernah ditulis.

4. **Date filtering via string comparison** — `periode_start` di-compare sebagai string `yyyy-mm-dd` yang bersifat lexicographically ordered = chronologically ordered. Tidak memerlukan `datetime.strptime`.

5. **Export files tidak ber-expiry** — file di `backend/local_server/exports/` tidak otomatis dihapus. Untuk production, gunakan presigned S3 URL (sudah ada di Lambda export handler).

6. **Perubahan JSON mock data** memerlukan restart server (`uvicorn --reload` akan otomatis restart karena mendeteksi perubahan file Python, tapi bukan JSON).

7. **Task 6.4 (unit tests export)** dan beberapa property-based tests ditandai opsional di tasks.md. Core functionality terverifikasi melalui `get_diagnostics`.

8. **`@app.on_event("startup")` deprecated** di FastAPI ≥ 0.93. Fungsional untuk MVP ini, tapi pertimbangkan migrasi ke `lifespan` context manager di masa mendatang.
