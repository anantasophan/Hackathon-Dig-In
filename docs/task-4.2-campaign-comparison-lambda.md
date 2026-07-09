# Task 4.2 — Campaign Comparison Lambda

## Ringkasan Singkat

`campaign_comparison/handler.py` adalah Lambda function yang melayani endpoint `POST /api/campaigns/comparison`. Fungsi ini menerima daftar 2 hingga 5 campaign ID, mengambil metrik agregat dari Athena, lalu mengembalikan tabel perbandingan beserta data siap-pakai untuk grafik Chart.js di frontend. Lambda ini memungkinkan pengguna bisnis membandingkan performa beberapa campaign secara berdampingan dengan lima metrik kunci: total leads, total take up, take-up rate, nilai transaksi, dan durasi campaign.

---

## Penjelasan Awam (Non-Technical)

Bayangkan kamu adalah Campaign Manager yang ingin membandingkan tiga campaign yang berjalan bersamaan bulan Agustus 2024: QRIS Agustus, QRIS Juli, dan Biaya Admin Agustus. Kamu ingin tahu: campaign mana yang paling efektif? Yang mana yang menghasilkan nilai transaksi terbesar? Yang mana yang take-up-nya paling tinggi?

Lambda ini seperti seorang analis yang kamu minta: *"Tolong buatkan tabel perbandingan untuk ketiga campaign ini."* Dalam hitungan detik, analis itu pergi ke database, mengambil angka-angka penting, menyusunnya dalam tabel yang rapi, dan juga menyiapkan data untuk membuat grafik batang perbandingan.

Yang penting: kamu hanya bisa membandingkan **maksimal 5 campaign sekaligus** — ini kesepakatan yang dibuat agar grafik perbandingan tetap terbaca dan tidak terlalu ramai. Minimal 2 campaign, karena kalau hanya satu ya bukan "perbandingan".

Manfaat bagi pengguna bisnis:
- Tidak perlu membuka laporan satu per satu dan menghitung manual
- Grafik langsung terbentuk di dashboard
- Bisa mengurutkan hasil berdasarkan program, channel, atau wilayah

---

## Penjelasan Teknis

### File yang Terlibat

| File | Peran |
|------|-------|
| `backend/lambdas/campaign_comparison/handler.py` | Entry point Lambda — parsing, validasi, query, response building |
| `backend/shared/models.py` | Dataclass `CampaignComparisonRequest`, `CampaignComparisonResponse`, `CampaignMetric` |
| `backend/shared/athena_client.py` | `build_comparison_query()`, `execute_query()` |
| `backend/shared/calculations.py` | `calculate_take_up_rate()` — dihitung ulang untuk safety |
| `backend/shared/sorting.py` | `sort_by_attribute()` — untuk optional grouping/sorting |

### Library / Framework

- **AWS Lambda** (Python 3.11+) — serverless execution
- **Amazon Athena** — query engine untuk tabel `campaign`
- **`json`** — parsing request body dan serialisasi response
- **`dataclasses.asdict`** — serialisasi `CampaignComparisonResponse` ke dict

### Pola Arsitektur

Lambda ini menggunakan pola **POST with Body Validation → Query → Transform → Chart Build → Respond**:

1. **Parse Body** — `event["body"]` diparsing dari JSON. Jika body kosong atau bukan JSON valid, return `400` segera.
2. **Validate Request** — `CampaignComparisonRequest` di-construct dari payload. `__post_init__` di dataclass secara otomatis melempar `ValueError` jika jumlah campaign ID kurang dari 2 atau lebih dari 5.
3. **Execute Query** — `AthenaClient.build_comparison_query(campaign_ids)` menghasilkan SQL dengan `IN` clause, lalu dieksekusi.
4. **Build Metrics** — setiap baris Athena dikonversi ke `CampaignMetric`. `take_up_rate` dihitung ulang secara lokal (tidak murni mengandalkan nilai dari Athena) untuk konsistensi.
5. **Optional Sort** — jika `group_by` diisi, list `CampaignMetric` diurutkan menggunakan `sort_by_attribute()`.
6. **Build Chart** — `_build_chart()` menghasilkan struktur Chart.js dengan 5 dataset.
7. **Return** — response dikembalikan tanpa `strip_pii()` karena data di tabel `campaign` adalah agregat, bukan data individu nasabah.

### Keputusan Desain Penting

- **Validasi batas 2–5 di dataclass, bukan di handler**: `CampaignComparisonRequest.__post_init__` menangani validasi ini. Handler hanya perlu menangkap `ValueError` — separation of concerns yang baik.
- **Recalculate take_up_rate secara lokal**: Meski Athena sudah menghitung rate, handler menghitung ulang dari `total_leads` dan `total_take_up` untuk mencegah ketidakkonsistenan data agregat yang basi.
- **Sorting setelah build metrics**: Sorting dilakukan setelah semua `CampaignMetric` terbentuk — sort menggunakan dict sementara lalu di-reconstruct kembali ke dataclass. Ini menjaga non-mutating principle.
- **Empty response tetap 200**: Jika tidak ada data untuk campaign ID yang diminta, response tetap `200` dengan `campaigns: []` dan pesan informatif — bukan `404`. Ini karena "tidak ditemukan data" bukan error teknis.
- **Tidak ada `strip_pii()`**: Berbeda dengan overview handler, comparison tidak memerlukan strip PII karena output adalah agregat per-campaign, bukan per-nasabah.

### Edge Cases yang Ditangani

| Kondisi | Penanganan |
|---------|-----------|
| Body request kosong / tidak ada | Return 400: "Request body is required." |
| Body bukan JSON valid | Return 400: "Request body must be valid JSON." |
| `campaign_ids` kurang dari 2 | Return 400 via `ValueError` dari `__post_init__` |
| `campaign_ids` lebih dari 5 | Return 400 via `ValueError` dari `__post_init__` |
| Athena timeout | Return 408 dengan detail error |
| Athena execution error | Return 500 dengan detail error |
| Tidak ada data untuk campaign IDs | Return 200 dengan `campaigns: []` dan message |
| `total_leads = 0` saat hitung rate | Guard condition: `if total_leads > 0` sebelum kalkulasi |
| `group_by` null / tidak diisi | Skip sorting, return dalam urutan dari Athena |

---

## Struktur Kode

```
handler.py
├── Constants
│   └── _CONTENT_TYPE_JSON: str = "application/json"
│
├── Response Helper
│   └── _response(status_code, body) → dict    # Generic response builder
│
├── Chart Builder
│   └── _build_chart(campaigns) → dict          # Struktur Chart.js 5 dataset
│
└── Entry Point
    └── lambda_handler(event, context) → dict   # Orchestrator utama
        ├── Step 1: Parse JSON body
        ├── Step 2: Validate & build CampaignComparisonRequest
        ├── Step 3: Init AthenaClient dari env vars
        ├── Step 4: Build & execute SQL query
        ├── Step 5: Handle empty result
        ├── Step 6: Build CampaignMetric dari rows
        ├── Step 7: Optional sort by group_by
        └── Step 8: Build chart & return response
```

### Fungsi Kunci

| Fungsi | Signature | Deskripsi |
|--------|-----------|-----------|
| `lambda_handler` | `(event, context) → dict` | Entry point AWS Lambda. Seluruh alur diatur di sini. |
| `_response` | `(status_code: int, body: dict) → dict` | Membangun response API Gateway proxy standar. |
| `_build_chart` | `(campaigns: list[CampaignMetric]) → dict` | Menghasilkan struktur `{labels, datasets}` siap Chart.js dengan 5 dataset. |

### Struktur `_build_chart` Output

```python
{
    "labels": ["QRIS Agustus 2024", "QRIS Juli 2024", "Biaya Admin Agustus 2024"],
    "datasets": [
        {"label": "Total Leads",          "data": [4200, 3980, 4270]},
        {"label": "Total Take Up",        "data": [380, 341, 290]},
        {"label": "Take Up Rate (%)",     "data": [9.05, 8.57, 6.79]},
        {"label": "Nilai Transaksi",      "data": [1250000000, 980000000, 750000000]},
        {"label": "Durasi (hari)",        "data": [31, 31, 31]},
    ]
}
```

---

## Simulasi / Skenario

### Skenario 1 — Happy Path: Perbandingan 3 Campaign

**Request:**
```http
POST /api/campaigns/comparison
Content-Type: application/json

{
  "campaign_ids": ["QRIS_AGUSTUS24", "QRIS_JULI24", "BIAYA_ADMIN_AGUSTUS24"],
  "group_by": null
}
```

**Proses Internal:**

1. **Parse body** → `payload = {"campaign_ids": [...], "group_by": null}`

2. **Validate** → `CampaignComparisonRequest(campaign_ids=["QRIS_AGUSTUS24","QRIS_JULI24","BIAYA_ADMIN_AGUSTUS24"], group_by=None)`
   - 3 campaign ID → lolos validasi (2 ≤ 3 ≤ 5) ✅

3. **SQL Query** (contoh dihasilkan oleh `build_comparison_query`):
   ```sql
   SELECT campaign_id, campaign_name, flag_program,
          total_leads, total_take_up,
          total_transaction_value, duration_days
   FROM campaign
   WHERE campaign_id IN ('QRIS_AGUSTUS24', 'QRIS_JULI24', 'BIAYA_ADMIN_AGUSTUS24')
   ```

4. **Hasil Athena** (3 baris):
   ```
   QRIS_AGUSTUS24    | QRIS Agustus 2024       | PROGRAM QRIS | 4200 | 380 | 1.25B | 31
   QRIS_JULI24       | QRIS Juli 2024          | PROGRAM QRIS | 3980 | 341 | 0.98B | 31
   BIAYA_ADMIN_AGU24 | Biaya Admin Agustus 2024| PROG BIAYA   | 4270 | 290 | 0.75B | 31
   ```

5. **Build CampaignMetric** (rate dihitung ulang lokal):
   - QRIS_AGUSTUS24: `take_up_rate = (380/4200)*100 = 9.05%`
   - QRIS_JULI24: `take_up_rate = (341/3980)*100 = 8.57%`
   - BIAYA_ADMIN_AGU24: `take_up_rate = (290/4270)*100 = 6.79%`

6. **group_by = null** → skip sorting

7. **Build chart** → 5 dataset dengan 3 data point masing-masing

**Response (HTTP 200):**
```json
{
  "campaigns": [
    {
      "campaign_id": "QRIS_AGUSTUS24",
      "campaign_name": "QRIS Agustus 2024",
      "flag_program": "PROGRAM QRIS",
      "total_leads": 4200,
      "total_take_up": 380,
      "take_up_rate": 9.05,
      "total_transaction_value": 1250000000.0,
      "duration_days": 31
    },
    {
      "campaign_id": "QRIS_JULI24",
      "campaign_name": "QRIS Juli 2024",
      "flag_program": "PROGRAM QRIS",
      "total_leads": 3980,
      "total_take_up": 341,
      "take_up_rate": 8.57,
      "total_transaction_value": 980000000.0,
      "duration_days": 31
    },
    {
      "campaign_id": "BIAYA_ADMIN_AGUSTUS24",
      "campaign_name": "Biaya Admin Agustus 2024",
      "flag_program": "PROGRAM BIAYA ADMIN",
      "total_leads": 4270,
      "total_take_up": 290,
      "take_up_rate": 6.79,
      "total_transaction_value": 750000000.0,
      "duration_days": 31
    }
  ],
  "comparison_chart": {
    "labels": ["QRIS Agustus 2024", "QRIS Juli 2024", "Biaya Admin Agustus 2024"],
    "datasets": [
      {"label": "Total Leads",      "data": [4200, 3980, 4270]},
      {"label": "Total Take Up",    "data": [380, 341, 290]},
      {"label": "Take Up Rate (%)", "data": [9.05, 8.57, 6.79]},
      {"label": "Nilai Transaksi",  "data": [1250000000.0, 980000000.0, 750000000.0]},
      {"label": "Durasi (hari)",    "data": [31, 31, 31]}
    ]
  }
}
```

---

### Skenario 2 — Happy Path dengan group_by

**Request:**
```json
{
  "campaign_ids": ["QRIS_AGUSTUS24", "QRIS_JULI24", "BIAYA_ADMIN_AGUSTUS24"],
  "group_by": "flag_program"
}
```

**Proses Tambahan:**
Setelah `CampaignMetric` terbentuk, `sort_by_attribute(campaigns_dicts, "flag_program", ascending=True)` dijalankan.

**Efek sorting:**
- "PROGRAM BIAYA ADMIN" secara alfabetis < "PROGRAM QRIS"
- Hasil: `BIAYA_ADMIN_AGUSTUS24` muncul pertama, lalu dua campaign QRIS berurutan

Ini memudahkan frontend untuk mengelompokkan visualisasi berdasarkan tipe program.

---

### Skenario 3 — Error: Melebihi Batas 5 Campaign

**Request:**
```json
{
  "campaign_ids": ["C001", "C002", "C003", "C004", "C005", "C006"],
  "group_by": null
}
```

**Proses:**
- `len(campaign_ids) = 6`
- `CampaignComparisonRequest.__post_init__` melempar `ValueError`: `"campaign_ids must contain at most 5 campaign identifiers, got 6"`
- Handler menangkap `ValueError` dan mereturn error

**Response (HTTP 400):**
```json
{
  "error": "campaign_ids must contain at most 5 campaign identifiers, got 6"
}
```

Frontend dapat menampilkan pesan ini langsung kepada pengguna.

---

### Skenario 4 — Error: Body JSON Tidak Valid

**Request:**
```
POST /api/campaigns/comparison
Content-Type: application/json

{campaign_ids: ["C001"  // syntax error: tanpa tanda kutip pada key
```

**Response (HTTP 400):**
```json
{
  "error": "Request body must be valid JSON."
}
```

---

### Skenario 5 — Error: Athena Timeout

**Response (HTTP 408):**
```json
{
  "error": "Query timed out.",
  "details": "Query execution timed out after 30 seconds"
}
```

---

## Keterkaitan dengan Komponen Lain

### Bergantung pada:
- **`shared/models.py`** — `CampaignComparisonRequest` (dengan validasi 2–5 di `__post_init__`), `CampaignComparisonResponse`, `CampaignMetric`
- **`shared/athena_client.py`** — `build_comparison_query(campaign_ids)` menghasilkan SQL dengan `IN` clause yang aman
- **`shared/calculations.py`** — `calculate_take_up_rate()` untuk recalculation lokal
- **`shared/sorting.py`** — `sort_by_attribute()` untuk optional `group_by` sorting
- **Tabel Athena `campaign`** — berisi 5 metrik agregat per campaign ID
- **Environment variables**: `ATHENA_DATABASE`, `ATHENA_S3_OUTPUT`, `ATHENA_WORKGROUP`, `AWS_REGION`

### Digunakan oleh:
- **Frontend** — halaman Campaign Comparison (`/dashboard/comparison`) mengirim POST request dan merender `comparison_chart` menggunakan Chart.js
- **Export Service** (Task 4.7) — kemungkinan memanggil endpoint ini untuk mengisi section perbandingan pada PDF/Excel export

### Pengaruh jika komponen ini berubah:
- Perubahan pada `_build_chart()` — menambah atau mengubah dataset — memerlukan update di frontend komponen Chart.js
- Perubahan batas 2–5 campaign harus sinkron antara handler, model `__post_init__`, dan UI validation di frontend
- Perubahan `CampaignMetric` fields akan mempengaruhi tabel perbandingan di UI

---

## Requirements yang Dipenuhi

| Req ID | Deskripsi |
|--------|-----------|
| **2.1** | Terima list campaign ID (2–5) dan kembalikan metrik per campaign |
| **2.2** | Hitung dan kembalikan 5 metrik: `total_leads`, `total_take_up`, `take_up_rate`, `total_transaction_value`, `duration_days` |
| **2.3** | Validasi: tolak jika campaign ID kurang dari 2 atau lebih dari 5 |
| **2.4** | Support `group_by` untuk sorting hasil berdasarkan dimensi tertentu |
| **2.5** | Kembalikan data siap-pakai untuk Chart.js (`comparison_chart`) |

---

## Catatan Penting

### Limitasi yang Diketahui
- **Tidak ada validasi apakah campaign ID eksis**: Handler tidak mengecek apakah ID yang diminta benar-benar ada di database sebelum query — Athena akan mengembalikan kosong jika tidak ada. Response tetap `200` dengan array kosong.
- **Tidak ada `strip_pii()`**: Karena data comparison adalah agregat per-campaign (bukan per-nasabah), PII stripping tidak diperlukan. Jika di masa depan handler menambahkan breakdown per nasabah, wajib tambahkan `strip_pii()`.
- **`flag_program` default empty string**: Tabel `campaign` yang di-query oleh `build_comparison_query` mungkin tidak mengembalikan kolom `flag_program`, sehingga defaultnya `""`. Perlu dicek apakah SQL query menyertakan kolom ini.

### Asumsi yang Dibuat
- `AthenaClient.build_comparison_query(campaign_ids)` menghasilkan SQL yang aman (tidak rentan SQL injection) karena menggunakan `_in_clause()` dari shared athena_client.
- Tabel `campaign` di Athena sudah berisi data agregat yang diproses oleh Glue ETL — bukan raw leads.
- `sort_by_attribute()` dari `sorting.py` bersifat non-mutating dan mengembalikan list dict baru.

### Todo / Pengembangan Berikutnya
- Tambahkan validasi bahwa setiap `campaign_id` dalam request hanya mengandung karakter alfanumerik dan underscore (sanitasi input)
- Pertimbangkan menambahkan `strip_pii()` sebagai defense-in-depth meskipun saat ini tidak diperlukan
- Tambahkan caching untuk kombinasi campaign ID yang sama — comparison adalah operasi read-heavy yang bisa di-cache dengan TTL pendek (misalnya 5 menit)
- Evaluasi apakah perlu menambahkan `group_by` breakdown per-segment (saat ini hanya sorting)
