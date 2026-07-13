# Task 4 — Campaigns Router (`routers/campaigns.py`)

## Ringkasan Singkat

Mengimplementasikan enam FastAPI route handler di `backend/local_server/routers/campaigns.py` yang
menjadi pengganti lokal untuk enam Lambda endpoint produksi. Setiap handler membaca data dari
`MockDataStore` (file JSON), menjalankan logika bisnis yang sama persis seperti Lambda, dan
mengembalikan respons JSON yang identik — tanpa satu pun koneksi ke AWS.

---

## Penjelasan Awam (Non-Technical)

Bayangkan sebuah restoran besar yang punya dua dapur: dapur produksi (AWS di cloud) dan dapur
percobaan di rumah (laptop developer). Ketika chef ingin mencoba resep baru atau memperbaiki
tampilan menu, ia tidak perlu pergi ke dapur produksi yang jauh — cukup pakai dapur percobaan
di rumah dengan bahan-bahan contoh (data mock).

`routers/campaigns.py` adalah "daftar menu dan cara memasak" untuk dapur percobaan tersebut.
Setiap "menu" (endpoint) menghasilkan hidangan yang sama persis seperti dapur produksi:

- **Overview**: Ringkasan performa semua kampanye — berapa banyak nasabah yang dihubungi, berapa yang tertarik
- **Comparison**: Membandingkan 2–5 kampanye secara berdampingan, seperti membandingkan kampanye WA Blast vs Email QRIS
- **Time Analysis**: Seberapa cepat nasabah merespons kampanye — mayoritas dalam 0–7 hari atau lebih lama?
- **Regional**: Wilayah mana yang paling sukses? Kanwil 3 atau Kanwil 7?
- **Customer Criteria**: Profil nasabah yang paling sering take up — MASS atau EMERALD? Gen Y atau Gen X?
- **Similar Campaign**: Kampanye lain apa yang mirip dengan kampanye ini, dan apa yang bisa dipelajari?

Semua ini berjalan di laptop tanpa koneksi internet ke AWS, menggunakan 150 data contoh nasabah.

---

## Penjelasan Teknis

### File yang Dibuat

| File | Ukuran | Keterangan |
|------|--------|------------|
| `backend/local_server/routers/campaigns.py` | ~450 baris | Implementasi 6 route handler |

### Library / Framework

- **FastAPI** (`APIRouter`, `HTTPException`, `Query`, `JSONResponse`) — routing dan validasi
- **Pydantic** (`BaseModel`) — validasi request body POST (tidak memakai dataclass agar FastAPI bisa auto-parse)
- **shared.calculations** — `calculate_take_up_rate`, `compute_statistics`, `compute_distribution_percentages`
- **shared.pii_filter** — `strip_pii` untuk memastikan tidak ada `cif` di respons
- **shared.sorting** — `sort_regional_performance`, `sort_similar_campaigns`, `sort_by_attribute`
- **shared.models** — `SIMILAR_CAMPAIGN_DIMENSIONS`, `ActiveFilter`, `CampaignMetric`, `SimilarCampaignResult`
- **local_server.mock_store** — singleton `store` untuk akses data JSON

### Pola Arsitektur

Setiap handler mengikuti pola yang sama (mirror dari Lambda handlers):
1. **Validasi input** → raise `HTTPException(400)` jika tidak valid
2. **Query data** → panggil `store.get_leads()` atau method lain
3. **Tangani empty result** → return 200 dengan `message` (bukan 404)
4. **Hitung agregat** via shared modules
5. **Strip PII** via `strip_pii()` sebelum serialize
6. **Return `JSONResponse`** dengan content dict

### Keputusan Desain Penting

**Pydantic BaseModel untuk POST body** — FastAPI memerlukan Pydantic model (bukan dataclass) untuk
auto-parse request body. `ComparisonRequestBody` dan `SimilarRequestBody` didefinisikan lokal di
file ini dan tidak tumpang tindih dengan `shared.models`.

**`_build_attribute_distribution` mirip Lambda** — Logika distribusi attribute di customer criteria
di-port langsung dari `lambdas/customer_criteria/handler.py`, namun menggunakan field name yang
benar (`segment_by_aum`, `range_usia`, dll) bukan legacy field (`customer_segment`, `age_group`).

**Trend aggregation across multiple campaigns** — Endpoint overview mengumpulkan trend entries dari
semua campaign yang muncul di filtered leads, lalu deduplicates by `(period_start, period_end)`.
Ini berbeda dengan Lambda yang query Athena langsung dengan agregasi sudah built-in.

**Histogram bin logic** — `_build_histogram()` di-port identik dari `time_analysis/handler.py`,
memastikan 7 bin fixed dengan semantik `range_start <= value < range_end` (bin terakhir open-ended).

### Edge Cases yang Ditangani

- `start_date`/`end_date` dengan format non-ISO → 400 dengan pesan deskriptif
- `campaign_ids` kurang dari 2 atau lebih dari 5 → 400
- `campaign_id` kosong/blank → 400
- `dimensions` kosong atau mengandung nilai invalid → 400
- Filter yang menghasilkan zero records → 200 dengan `message` field (bukan error)
- `selected_region` sebagai string non-integer → silently treated as no filter
- `time_to_take_up_days` bernilai None/unparseable → dilewati dari days_list
- Campaign yang tidak ada di `campaigns.json` → `CampaignMetric` dengan empty string fields

---

## Struktur Kode

```python
# Pydantic models untuk POST body
class ComparisonRequestBody(BaseModel): ...
class SimilarRequestBody(BaseModel): ...

# Private helpers
def _validate_date(raw, field_name) -> str | None
    # Validates yyyy-mm-dd, raises HTTPException 400 if invalid

def _parse_string_list(raw) -> list[str] | None
    # Splits comma-separated query param

def _parse_int_list(raw) -> list[int] | None
    # Splits comma-separated integers, drops non-numeric tokens

def _build_active_filters(start_date, end_date, ...) -> list[ActiveFilter]
    # Builds filter list for response payload

def _build_histogram(days_list) -> list[dict]
    # 7-bin histogram with fixed boundaries [0,7,14,21,30,60,90,∞]

def _build_attribute_distribution(rows, attribute) -> dict
    # Distribution with percentage and take_up breakdown

def _build_chart(campaigns) -> dict
    # Chart.js-compatible labels + datasets structure

# Route handlers
@router.get("/campaigns/overview")
async def campaign_overview(...) -> JSONResponse

@router.post("/campaigns/comparison")
async def campaign_comparison(body) -> JSONResponse

@router.get("/campaigns/time-analysis/{campaign_id}")
async def time_analysis(campaign_id, channel, region) -> JSONResponse

@router.get("/campaigns/regional/{campaign_id}")
async def regional_performance(campaign_id, flag_program, selected_region) -> JSONResponse

@router.get("/campaigns/customer-criteria/{campaign_id}")
async def customer_criteria(campaign_id) -> JSONResponse

@router.post("/campaigns/similar")
async def similar_campaign(body) -> JSONResponse
```

---

## Simulasi / Skenario

### Skenario 1: Developer menguji Overview dengan filter wilayah

**Input:** `GET /api/campaigns/overview?wilayah=1,3&flag_program=PROGRAM+QRIS`

**Proses:**
1. `_parse_int_list("1,3")` → `[1, 3]`
2. `_parse_string_list("PROGRAM QRIS")` → `["PROGRAM QRIS"]`
3. `store.get_leads(wilayah=[1, 3], flag_program=["PROGRAM QRIS"])` → ~30 leads
4. Hitung: `total_leads=30`, `total_take_up=6`, `take_up_rate=20.0`
5. Ambil trend dari C001, C003, C005 (kampanye QRIS)
6. `strip_pii()` tidak mengubah apa pun (leads.json tidak punya `cif`)

**Output:**
```json
{
  "total_leads": 30,
  "total_take_up": 6,
  "take_up_rate": 20.0,
  "total_campaigns": 3,
  "trend": [
    {"period_start": "2024-08-01", "period_end": "2024-08-07",
     "total_leads": 12, "total_take_up": 2, "take_up_rate": 16.67}
  ],
  "filters": [
    {"field": "wilayah", "values": ["1", "3"]},
    {"field": "flag_program", "values": ["PROGRAM QRIS"]}
  ]
}
```

---

### Skenario 2: Developer membandingkan 3 kampanye dengan group_by

**Input:** `POST /api/campaigns/comparison` dengan body:
```json
{"campaign_ids": ["C001", "C003", "C005"], "group_by": "flag_program"}
```

**Proses:**
1. Validasi: 3 IDs ✓ (antara 2–5)
2. Untuk setiap campaign: hitung leads, take_up, transaction_value dari `leads.json`
3. Ambil `duration_days` dari `campaigns.json` master record
4. `sort_by_attribute(campaigns_dicts, "flag_program", ascending=True)` → urut alfabet
5. Build Chart.js structure: labels=["Cashback QRIS", "Digisales QRIS", "Email QRIS"]

**Output:**
```json
{
  "campaigns": [
    {"campaign_id": "C001", "campaign_name": "Cashback QRIS Agustus 2024",
     "flag_program": "PROGRAM QRIS", "total_leads": 32, "total_take_up": 6,
     "take_up_rate": 18.75, "total_transaction_value": 2700000.0, "duration_days": 30}
  ],
  "comparison_chart": {
    "labels": ["Cashback QRIS...", "Digisales QRIS...", "Email QRIS..."],
    "datasets": [
      {"label": "Total Leads", "data": [32, 28, 25]},
      {"label": "Take Up Rate (%)", "data": [18.75, 21.43, 16.0]}
    ]
  }
}
```

---

### Skenario 3: Similar campaign dengan dimensi invalid

**Input:** `POST /api/campaigns/similar` dengan body:
```json
{"reference_campaign_id": "C001", "dimensions": ["flag_program", "segment_by_aum"]}
```

**Proses:**
1. Validasi: `"segment_by_aum"` bukan anggota `SIMILAR_CAMPAIGN_DIMENSIONS`
2. Raise `HTTPException(400)`

**Output:** HTTP 400
```json
{
  "detail": "Invalid dimension(s): ['segment_by_aum']. Allowed values: ['flag_program', 'jenis_leads', 'media_blasting']."
}
```

---

## Keterkaitan dengan Komponen Lain

**Bergantung pada:**
- `local_server.mock_store.store` — sumber data seluruh handler; semua query data melewati singleton ini
- `shared.calculations` — `calculate_take_up_rate`, `compute_statistics`, `compute_distribution_percentages`
- `shared.sorting` — `sort_regional_performance`, `sort_similar_campaigns`, `sort_by_attribute`
- `shared.pii_filter.strip_pii` — filter PII pada response
- `shared.models` — `ActiveFilter`, `CampaignMetric`, `SimilarCampaignResult`, `SIMILAR_CAMPAIGN_DIMENSIONS`

**Digunakan oleh:**
- `local_server.main` — me-include router ini via `app.include_router(campaigns.router, prefix="/api")`
- Frontend React (axios) — memanggil semua 6 endpoint ini melalui `REACT_APP_API_URL=http://localhost:8000`

**Pengaruh ke:**
- Mengubah field name di `mock_data/leads.json` akan mempengaruhi customer criteria distribution
- Mengubah `SIMILAR_CAMPAIGN_DIMENSIONS` di `shared/models.py` akan mempengaruhi validasi POST /similar
- Mengubah bin edges di `_HISTOGRAM_BINS` akan mempengaruhi time analysis dan property test 7.5

---

## Requirements yang Dipenuhi

| Requirement | Endpoint | Keterangan |
|-------------|----------|------------|
| 2.1–2.9 | GET /api/campaigns/overview | Filter, agregat, trend, PII-free |
| 3.1–3.7 | POST /api/campaigns/comparison | Validasi 2–5 IDs, group_by sort, Chart.js |
| 4.1–4.7 | GET /api/campaigns/time-analysis/{id} | 7-bin histogram, stats, channel/region filter |
| 5.1–5.6 | GET /api/campaigns/regional/{id} | Per-wilayah metrics, sort desc, weekly trend ≤8 |
| 6.1–6.7 | GET /api/campaigns/customer-criteria/{id} | 5 distribusi atribut, PII-free |
| 7.1–7.7 | POST /api/campaigns/similar | Dimensi validasi, sort, limit cap |

---

## Catatan Penting

**Limitasi yang diketahui:**
- `learning_summary` di endpoint similar selalu mengembalikan `top_segment: "N/A"` dan `top_region: "N/A"` —
  data segment dan region tidak ada di `similarity_index.json` (sama seperti Lambda handler produksi)
- Trend di overview di-aggregate dari semua campaign yang muncul di filtered leads, bukan per-campaign;
  duplikat entries untuk period yang sama di-deduplicate by `(period_start, period_end)`
- `avg_transaction_value` di regional performance dihitung hanya dari leads yang `take_up_flag == "YES"`;
  jika tidak ada take-up di suatu wilayah, nilai ini 0.0

**Asumsi yang dibuat:**
- `wilayah` selalu integer di `leads.json` — tidak ada validasi tipe di query layer
- `total_transaction_value` di leads.json bisa `None` atau tidak ada; dihandle dengan `or 0.0`
- Campaign yang tidak ada di `campaigns.json` tetap diproses (comparison tetap jalan dengan empty string fields)

**Todo untuk pengembangan berikutnya:**
- Task 4.7: unit tests untuk semua 6 handler
- Endpoint overview bisa diperluas untuk mendukung `campaign_id` filter sebagai query param
- `learning_summary` bisa diperkaya jika `similarity_index.json` diperluas dengan data segment
