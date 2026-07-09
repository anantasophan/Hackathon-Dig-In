# Task 4.3 — Time Analysis Lambda

## Ringkasan Singkat

`time_analysis/handler.py` adalah Lambda function yang melayani endpoint `GET /api/campaigns/time-analysis/{campaign_id}`. Fungsi ini menganalisis distribusi waktu yang dibutuhkan nasabah untuk melakukan take up setelah menerima penawaran campaign. Output utamanya adalah histogram dengan 7 bin waktu tetap (0–7 hari, 7–14 hari, dst.) beserta statistik deskriptif (min, max, mean, median). Lambda ini mendukung filtering opsional berdasarkan channel (media_blasting) dan region (wilayah) untuk analisis yang lebih granular.

---

## Penjelasan Awam (Non-Technical)

Bayangkan kamu adalah Campaign Manager yang penasaran: *"Kalau saya kirim penawaran ke nasabah, berapa hari rata-rata mereka butuh sebelum akhirnya menggunakan produknya?"* Atau lebih spesifik: *"Dari 87 nasabah yang menggunakan produk campaign QRIS Agustus, berapa persen yang langsung pakai dalam seminggu? Berapa persen yang butuh lebih dari sebulan?"*

Lambda ini adalah alat untuk menjawab pertanyaan itu. Analoginya seperti seorang analis yang membuka catatan follow-up dan mengelompokkannya ke dalam "laci" berdasarkan waktu respons nasabah:
- Laci 1: Yang merespons dalam 0–7 hari (sangat cepat)
- Laci 2: Yang merespons dalam 7–14 hari
- Laci 3: 14–21 hari
- Dan seterusnya hingga laci terakhir: yang butuh 90+ hari

Kamu juga bisa meminta: *"Khusus yang dihubungi via WhatsApp saja"* — dan hasilnya akan berubah sesuai filter tersebut.

Manfaat bagi pengguna bisnis:
- Memahami **kapan momentum terbaik** untuk mengingatkan nasabah (follow-up di hari ke-7 mungkin lebih efektif dari hari ke-30)
- Membandingkan pola respons antar channel (apakah WA lebih cepat dari telesales?)
- Membantu perencanaan durasi campaign yang optimal

---

## Penjelasan Teknis

### File yang Terlibat

| File | Peran |
|------|-------|
| `backend/lambdas/time_analysis/handler.py` | Entry point Lambda — query, filter, histogram, stats, response |
| `backend/shared/athena_client.py` | `build_time_analysis_query()`, `execute_query()` |
| `backend/shared/calculations.py` | `compute_statistics()` — hitung min, max, mean, median |

### Library / Framework

- **AWS Lambda** (Python 3.11+) — serverless execution
- **Amazon Athena** — query engine untuk tabel `leads` (data take up individual)
- **`json`** — serialisasi response
- **Hanya stdlib** — tidak ada dependency eksternal selain shared modules

### Pola Arsitektur

Lambda ini mengikuti pola **Path Param Extract → Query → In-Memory Filter → Compute → Respond**:

1. **Extract Path Param** — `campaign_id` diambil dari `event["pathParameters"]`. Jika tidak ada, return `400`.
2. **Extract Query Params** — `channel` dan `region` diambil dari query string (opsional).
3. **Execute Query** — `AthenaClient.build_time_analysis_query(campaign_id)` mengembalikan semua baris take up untuk campaign tersebut.
4. **In-Memory Filter** — Filtering channel dan region dilakukan **setelah** data dari Athena diterima, bukan di SQL. Ini adalah trade-off: query lebih sederhana tapi filtering dilakukan di memory Lambda.
5. **Extract Days** — Kolom `time_to_take_up_days` diambil dari setiap baris, dengan skip otomatis untuk nilai null atau non-numeric.
6. **Compute Statistics** — `compute_statistics(days_list)` menghitung min, max, mean, median.
7. **Build Histogram** — `_build_histogram(days_list)` mendistribusikan nilai ke 7 bin tetap.
8. **Return** — Response dikembalikan tanpa PII karena data adalah statistik agregat.

### Bin Histogram Tetap

Lambda ini menggunakan 7 bin yang ditentukan sebagai konstanta modul:

```python
_HISTOGRAM_BINS: list[tuple[int, int | None]] = [
    (0, 7),     # 0–6 hari    (sangat responsif)
    (7, 14),    # 7–13 hari   (responsif)
    (14, 21),   # 14–20 hari  (normal)
    (21, 30),   # 21–29 hari  (lambat)
    (30, 60),   # 30–59 hari  (sangat lambat)
    (60, 90),   # 60–89 hari  (lama sekali)
    (90, None), # 90+ hari    (open-ended: upper bound tidak ada)
]
```

Aturan binning: `range_start <= value < range_end`. Bin terakhir (90+) tidak memiliki batas atas.

### Keputusan Desain Penting

- **In-memory filtering vs. SQL filtering**: Channel dan region difilter di Python setelah data diterima dari Athena, bukan dengan menambahkan klausa `WHERE channel = ...` ke SQL. Keuntungannya: query SQL lebih sederhana dan dapat di-cache/reuse. Kerugiannya: jika data sangat besar, ini bisa memakan memory Lambda.
- **Skip null/non-numeric days**: Nilai `time_to_take_up_days` yang null atau tidak bisa dikonversi ke integer di-skip tanpa error — lead yang belum take up tidak punya nilai ini, jadi ini kondisi normal, bukan error data.
- **Empty state tetap 200**: Jika `days_list` kosong setelah filtering (artinya tidak ada take up untuk kombinasi filter tersebut), response tetap `200` dengan pesan informatif — bukan `404`.
- **Persentase dibulatkan 2 desimal**: Konsisten dengan presisi yang ditampilkan di UI dashboard.
- **Stats rounded 1 desimal**: `mean_days` dan `median_days` dibulatkan ke 1 desimal untuk keterbacaan.

### Edge Cases yang Ditangani

| Kondisi | Penanganan |
|---------|-----------|
| `campaign_id` tidak ada di path | Return 400: "campaign_id path parameter is required" |
| Athena timeout | Return 408 dengan `campaign_id` |
| Athena execution error | Return 500 dengan `campaign_id` dan pesan error |
| Tidak ada data take up sama sekali | Return 200 dengan pesan "Belum ada data take up" |
| Semua nilai `time_to_take_up_days` null | Return 200 dengan pesan "Belum ada data take up" |
| Filter `channel` tidak cocok dengan data apapun | Return 200 dengan pesan "Belum ada data take up" |
| Nilai `time_to_take_up_days` tidak bisa di-int | Di-skip per baris, tidak crash |
| `days_list` mengandung value 90+ | Masuk ke bin terakhir (open-ended) |

---

## Struktur Kode

```
handler.py
├── Constants
│   ├── _HISTOGRAM_BINS: list[tuple[int, int | None]]   # 7 bin tetap
│   └── _HEADERS: dict[str, str]                        # Content-Type header
│
├── Response Helper
│   └── _json_response(status_code, body) → dict        # Generic response builder
│
├── Histogram Builder
│   └── _build_histogram(days_list) → list[dict]        # 7 bin → count + percentage
│
└── Entry Point
    └── lambda_handler(event, context) → dict           # Orchestrator utama
        ├── Step 1:  Extract campaign_id dari pathParameters
        ├── Step 2:  Extract channel & region dari queryStringParameters
        ├── Step 3:  Init AthenaClient dari env vars
        ├── Step 4:  Build & execute SQL query
        ├── Step 5&6: In-memory filter: channel, region
        ├── Step 7:  Handle empty setelah filter
        ├── Step 8:  Extract & parse days_list
        ├── Step 9:  Handle all-null days
        ├── Step 10: Compute statistics
        ├── Step 11: Build histogram
        └── Step 12: Return response
```

### Fungsi Kunci

| Fungsi | Signature | Deskripsi |
|--------|-----------|-----------|
| `lambda_handler` | `(event, context) → dict` | Entry point. Mengkoordinasi seluruh alur dari path param hingga response. |
| `_build_histogram` | `(days_list: list[int]) → list[dict]` | Distribusikan nilai ke 7 bin tetap. Hitung count dan persentase per bin. |
| `_json_response` | `(status_code: int, body: dict) → dict` | Wrapper response API Gateway yang sederhana. |

### Output `_build_histogram` (contoh)

```python
[
    {"range_start": 0,  "range_end": 7,    "count": 12, "percentage": 13.79},
    {"range_start": 7,  "range_end": 14,   "count": 31, "percentage": 35.63},
    {"range_start": 14, "range_end": 21,   "count": 25, "percentage": 28.74},
    {"range_start": 21, "range_end": 30,   "count": 11, "percentage": 12.64},
    {"range_start": 30, "range_end": 60,   "count": 6,  "percentage": 6.90},
    {"range_start": 60, "range_end": 90,   "count": 2,  "percentage": 2.30},
    {"range_start": 90, "range_end": None, "count": 0,  "percentage": 0.0},
]
```

---

## Simulasi / Skenario

### Skenario 1 — Happy Path: Campaign QRIS Agustus 2024, Tanpa Filter

**Request:**
```
GET /api/campaigns/time-analysis/QRIS_AGUSTUS24
```

**Data Campaign:**
- Campaign QRIS Agustus 2024
- Total 1000 leads, 87 di antaranya melakukan take up

**Proses Internal:**

1. **Extract path param** → `campaign_id = "QRIS_AGUSTUS24"`
2. **Extract query params** → `channel = None`, `region = None`

3. **SQL Query** (dihasilkan oleh `build_time_analysis_query`):
   ```sql
   SELECT time_to_take_up_days, channel, region
   FROM leads
   WHERE campaign_id = 'QRIS_AGUSTUS24'
     AND take_up_flag = 'YES'
   ```

4. **Hasil Athena** → 87 baris (hanya yang take up), contoh sebagian:
   ```
   row 1:  time_to_take_up_days=3,  channel="wa",        region="3"
   row 2:  time_to_take_up_days=10, channel="wa",        region="3"
   row 3:  time_to_take_up_days=14, channel="digisales",  region="5"
   row 4:  time_to_take_up_days=22, channel="telesales",  region="3"
   ...
   row 87: time_to_take_up_days=45, channel="wa",        region="1"
   ```

5. **In-memory filter** → `channel=None`, `region=None` → tidak ada filter, semua 87 baris dipakai

6. **Extract days_list** → `[3, 10, 14, 22, ..., 45]` — 87 nilai integer

7. **Compute statistics** via `compute_statistics([3, 10, 14, ..., 45])`:
   - `min = 2` hari (nasabah paling cepat merespons)
   - `max = 45` hari (nasabah paling lama merespons)
   - `mean = 16.3` hari (rata-rata waktu respons)
   - `median = 14.0` hari (nilai tengah distribusi)

8. **Build histogram** — 87 nilai didistribusikan ke 7 bin:
   - `0–7 hari`: 12 take up (13.79%)
   - `7–14 hari`: 31 take up (35.63%)
   - `14–21 hari`: 25 take up (28.74%)
   - `21–30 hari`: 11 take up (12.64%)
   - `30–60 hari`: 6 take up (6.90%)
   - `60–90 hari`: 2 take up (2.30%)
   - `90+ hari`: 0 take up (0.0%)

**Response (HTTP 200):**
```json
{
  "campaign_id": "QRIS_AGUSTUS24",
  "histogram": [
    {"range_start": 0,  "range_end": 7,    "count": 12, "percentage": 13.79},
    {"range_start": 7,  "range_end": 14,   "count": 31, "percentage": 35.63},
    {"range_start": 14, "range_end": 21,   "count": 25, "percentage": 28.74},
    {"range_start": 21, "range_end": 30,   "count": 11, "percentage": 12.64},
    {"range_start": 30, "range_end": 60,   "count": 6,  "percentage": 6.90},
    {"range_start": 60, "range_end": 90,   "count": 2,  "percentage": 2.30},
    {"range_start": 90, "range_end": null, "count": 0,  "percentage": 0.0}
  ],
  "stats": {
    "min_days": 2,
    "max_days": 45,
    "mean_days": 16.3,
    "median_days": 14.0,
    "total_take_up": 87
  },
  "channel_filter": null,
  "region_filter": null
}
```

**Insight bisnis yang bisa dibaca dari response ini:**
- Sebagian besar take up terjadi pada hari ke 7–14 (35.63%) — ini adalah "golden window"
- Hampir 80% take up terjadi dalam 21 hari pertama
- Hanya ~9% yang membutuhkan waktu lebih dari 30 hari

---

### Skenario 2 — Dengan Filter Channel "wa"

**Request:**
```
GET /api/campaigns/time-analysis/QRIS_AGUSTUS24?channel=wa
```

**Proses Internal:**

1. Steps 1–4 sama dengan skenario 1 (query Athena tidak berubah)

2. **In-memory filter channel="wa"** → dari 87 baris, hanya baris dengan `channel == "wa"` yang dipertahankan

3. **Hasil setelah filter** → misalnya 52 baris (52 nasabah yang dihubungi via WA dan take up)

4. **Extract days_list** → `[3, 10, 8, 5, ..., 31]` — 52 nilai

5. **Compute statistics** (berbeda dari skenario 1 karena subset):
   - `min = 1` hari
   - `max = 31` hari
   - `mean = 11.4` hari
   - `median = 9.5` hari
   - Note: Nasabah WA cenderung lebih cepat merespons!

6. **Build histogram** — 52 nilai didistribusikan ulang:
   - `0–7 hari`: 18 take up (34.62%) ← lebih tinggi dari tanpa filter!
   - `7–14 hari`: 22 take up (42.31%)
   - `14–21 hari`: 9 take up (17.31%)
   - `21–30 hari`: 3 take up (5.77%)
   - `30–60 hari`: 0 take up (0.0%)
   - `60–90 hari`: 0 take up (0.0%)
   - `90+ hari`: 0 take up (0.0%)

**Response (HTTP 200):**
```json
{
  "campaign_id": "QRIS_AGUSTUS24",
  "histogram": [
    {"range_start": 0,  "range_end": 7,    "count": 18, "percentage": 34.62},
    {"range_start": 7,  "range_end": 14,   "count": 22, "percentage": 42.31},
    {"range_start": 14, "range_end": 21,   "count": 9,  "percentage": 17.31},
    {"range_start": 21, "range_end": 30,   "count": 3,  "percentage": 5.77},
    {"range_start": 30, "range_end": 60,   "count": 0,  "percentage": 0.0},
    {"range_start": 60, "range_end": 90,   "count": 0,  "percentage": 0.0},
    {"range_start": 90, "range_end": null, "count": 0,  "percentage": 0.0}
  ],
  "stats": {
    "min_days": 1,
    "max_days": 31,
    "mean_days": 11.4,
    "median_days": 9.5,
    "total_take_up": 52
  },
  "channel_filter": "wa",
  "region_filter": null
}
```

**Insight bisnis:** Nasabah yang dihubungi via WA merespons jauh lebih cepat (median 9.5 hari vs 14 hari keseluruhan). Hampir 77% take up via WA terjadi dalam 14 hari pertama.

---

### Skenario 3 — Empty State: Campaign Tanpa Data Take Up

**Request:**
```
GET /api/campaigns/time-analysis/QRIS_AGUSTUS24?channel=email
```

**Proses:**
- Query Athena mengembalikan 87 baris (seluruh take up campaign)
- In-memory filter `channel="email"` → tidak ada baris yang cocok (campaign ini tidak menggunakan channel email)
- `rows` menjadi list kosong

**Response (HTTP 200):**
```json
{
  "message": "Belum ada data take up untuk campaign ini",
  "campaign_id": "QRIS_AGUSTUS24"
}
```

---

### Skenario 4 — Error: campaign_id Tidak Disertakan

**Request:**
```
GET /api/campaigns/time-analysis/
```

**Proses:**
- `event["pathParameters"]` = `{}` atau `None`
- `campaign_id = None`
- Guard check: `if not campaign_id: return _json_response(400, {...})`

**Response (HTTP 400):**
```json
{
  "error": "campaign_id path parameter is required"
}
```

---

### Skenario 5 — Error: Athena Timeout

**Request:**
```
GET /api/campaigns/time-analysis/PROGRAM_BESAR_2020
```

**Konteks:** Campaign lama dengan jutaan leads, query scan terlalu besar.

**Response (HTTP 408):**
```json
{
  "error": "Query timed out. Please retry.",
  "campaign_id": "PROGRAM_BESAR_2020"
}
```

---

### Skenario 6 — Data dengan Nilai time_to_take_up_days Null

**Konteks:** Beberapa baris di Athena memiliki `take_up_flag = 'YES'` tapi `time_to_take_up_days = NULL` (data tidak lengkap dari monitoring report).

**Proses:**
```python
for row in rows:
    raw = row.get("time_to_take_up_days")   # → None
    if raw is None or raw == "":
        continue    # ← di-skip, tidak masuk ke days_list
    try:
        days_list.append(int(raw))
    except (ValueError, TypeError):
        continue    # ← jika tidak bisa di-convert, juga di-skip
```

Hasilnya: baris dengan null diabaikan, `total_take_up` di stats hanya menghitung baris yang punya nilai valid.

---

## Keterkaitan dengan Komponen Lain

### Bergantung pada:
- **`shared/athena_client.py`** — `build_time_analysis_query(campaign_id)` menghasilkan SQL, `execute_query()` mengeksekusinya
- **`shared/calculations.py`** — `compute_statistics(days_list)` untuk menghitung min, max, mean, median
- **Tabel Athena `leads`** — berisi data individual per lead termasuk `time_to_take_up_days`, `channel`, `region`
- **Environment variables**: `ATHENA_DATABASE`, `ATHENA_OUTPUT_LOCATION`, `AWS_REGION`

### Digunakan oleh:
- **Frontend** — halaman Time to Take Up (`/dashboard/time-analysis`) menampilkan histogram sebagai bar chart dan statistik sebagai kartu metrik
- **Export Service** (Task 4.7) — untuk menyertakan analisis timing dalam laporan ekspor

### Pengaruh jika komponen ini berubah:
- Perubahan pada `_HISTOGRAM_BINS` (menambah/mengubah bin) memerlukan update di frontend — label sumbu X chart histogram harus sinkron
- Perubahan pada logic in-memory filtering (dari `channel` ke nama field lain) memerlukan update di API documentation dan frontend query builder
- Perubahan nama field response (`min_days` → `minimum_days`) memerlukan update di frontend

---

## Requirements yang Dipenuhi

| Req ID | Deskripsi |
|--------|-----------|
| **3.1** | Query data `time_to_take_up_days` untuk campaign ID tertentu |
| **3.2** | Bangun histogram dengan 7 bin waktu tetap (0–7, 7–14, 14–21, 21–30, 30–60, 60–90, 90+) |
| **3.3** | Hitung statistik deskriptif: min, max, mean, median, total_take_up |
| **3.4** | Support filter opsional berdasarkan `channel` (media_blasting) |
| **3.5** | Support filter opsional berdasarkan `region` |
| **3.6** | Kembalikan empty state yang informatif jika tidak ada data take up |

---

## Catatan Penting

### Limitasi yang Diketahui
- **In-memory filtering**: Filter `channel` dan `region` dilakukan di memory Lambda, bukan di SQL Athena. Jika sebuah campaign memiliki ratusan ribu leads, seluruh data harus ditarik ke Lambda dulu sebelum difilter. Ini berpotensi menyebabkan:
  - Penggunaan memory Lambda yang tinggi
  - Latency lebih tinggi karena data transfer dari Athena
  - Risiko Lambda timeout untuk campaign dengan volume sangat besar
- **Tidak ada validasi `campaign_id` format**: Handler tidak memvalidasi apakah `campaign_id` mengandung karakter berbahaya. Validasi ini dilimpahkan ke `AthenaClient.build_time_analysis_query()` yang harus menggunakan parameterisasi SQL yang aman.
- **`total_take_up` di stats ≠ total leads campaign**: `total_take_up` di response hanya menghitung lead yang punya nilai `time_to_take_up_days` valid — bukan total lead yang `take_up_flag = 'YES'`. Ini bisa berbeda jika ada data null.

### Asumsi yang Dibuat
- `AthenaClient.build_time_analysis_query()` hanya mengembalikan baris dengan `take_up_flag = 'YES'` dari tabel `leads`. Handler tidak melakukan filtering tambahan untuk ini.
- Kolom `channel` di tabel `leads` sesuai dengan nilai di `VALID_MEDIA_BLASTING` (`"wa"`, `"digisales"`, dst.) — filter dilakukan dengan exact match string, bukan case-insensitive.
- `region` di query parameter ditreat sebagai string dan di-match dengan kolom `region` yang juga string di Athena result. Perhatikan bahwa field `wilayah` di domain model adalah integer, tapi kolom `region` di result Athena mungkin berbeda nomenklaturnya.
- Environment variable `ATHENA_OUTPUT_LOCATION` (bukan `ATHENA_S3_OUTPUT` seperti di overview handler) — perlu konsistensi penamaan env var di deployment.

### Todo / Pengembangan Berikutnya
- Pindahkan filter `channel` dan `region` ke SQL query (sebagai klausa `WHERE`) untuk menghindari masalah memory pada campaign besar
- Tambahkan validasi format `campaign_id` (hanya alfanumerik + underscore + dash)
- Pertimbangkan endpoint yang mengembalikan perbandingan histogram antar channel dalam satu request (untuk menghindari multiple API calls)
- Tambahkan percentile (P25, P75) ke stats response untuk memberikan gambaran distribusi yang lebih lengkap
- Unifikasi nama env var: `ATHENA_OUTPUT_LOCATION` vs `ATHENA_S3_OUTPUT` — perlu standarisasi di semua Lambda handler
