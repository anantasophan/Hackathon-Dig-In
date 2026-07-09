# Task 4.1 — Campaign Overview Lambda

## Ringkasan Singkat

`campaign_overview/handler.py` adalah Lambda function yang melayani endpoint `GET /api/campaigns/overview`. Fungsi ini memproses permintaan ringkasan performa campaign dari dashboard, menjalankan query ke Amazon Athena, mengagregasi metrik utama (total leads, total take up, take-up rate), membangun data tren, lalu mengembalikan hasil yang sudah dibersihkan dari data PII. Lambda ini adalah pintu masuk utama bagi pengguna yang ingin melihat gambaran besar performa semua campaign dalam satu periode waktu.

---

## Penjelasan Awam (Non-Technical)

Bayangkan kamu membuka halaman ringkasan laporan di dashboard campaign bank. Di sana kamu bisa melihat:
- "Berapa total nasabah yang dihubungi bulan ini?"
- "Berapa yang akhirnya menggunakan produk yang ditawarkan?"
- "Bagaimana trennya minggu per minggu?"

Lambda ini adalah "mesin di balik layar" yang memproses pertanyaan-pertanyaan itu. Analoginya seperti seorang staf yang kamu minta untuk merekap laporan: kamu bilang "tolong ambilkan data 3 bulan terakhir, khusus program QRIS, yang dikirim via WhatsApp" — staf itu pergi ke gudang data, menyaring file yang relevan, menghitung totalnya, lalu membawakan ringkasan ke mejamu.

Yang membuat ini istimewa: staf tersebut juga memastikan **informasi pribadi nasabah tidak ikut dibawa** ke laporan — hanya angka-angka agregat yang ditampilkan, bukan nama atau nomor rekening siapapun.

Manfaat bagi pengguna bisnis:
- Campaign Owner bisa langsung melihat performa tanpa harus menunggu laporan manual
- Bisa memfilter berdasarkan program, channel, wilayah, atau jenis leads sesuai kebutuhan
- Data tren membantu melihat apakah performa membaik atau memburuk dari minggu ke minggu

---

## Penjelasan Teknis

### File yang Terlibat

| File | Peran |
|------|-------|
| `backend/lambdas/campaign_overview/handler.py` | Entry point Lambda — parsing, orchestration, response building |
| `backend/shared/models.py` | Dataclass `CampaignOverviewRequest`, `CampaignOverviewResponse`, `TrendDataPoint`, `ActiveFilter` |
| `backend/shared/athena_client.py` | Eksekusi query ke Amazon Athena (`build_campaign_overview_query`, `execute_query`) |
| `backend/shared/calculations.py` | `calculate_take_up_rate`, `select_granularity` |
| `backend/shared/pii_filter.py` | `strip_pii` — menghapus field PII dari response |

### Library / Framework

- **AWS Lambda** (Python 3.11+) — serverless execution
- **Amazon Athena** — query engine untuk data di S3
- **`dataclasses.asdict`** — serialisasi dataclass ke dict untuk JSON response
- **`datetime`** — kalkulasi default date range (90 hari ke belakang)

### Pola Arsitektur

Lambda ini mengikuti pola **Request → Validate → Query → Aggregate → Respond**:

1. **Parse & Validate** — query string parameters diparsing dengan helper `_parse_request()`. Tanggal divalidasi format `yyyy-mm-dd`. Jika tidak valid, langsung return `400`.
2. **Build Active Filters** — filter yang aktif dibangun lebih awal (sebelum query) agar bisa disertakan juga pada response error, sehingga frontend tahu filter apa yang sedang aktif.
3. **Execute Query** — `AthenaClient` membangun SQL dengan filter yang sesuai dan menjalankannya secara sinkron.
4. **Aggregate** — baris hasil query disum ke total keseluruhan menggunakan `_aggregate_rows()`.
5. **Build Trend** — setiap baris hasil juga dijadikan satu `TrendDataPoint` menggunakan `_build_trend()`.
6. **Strip PII & Return** — seluruh response dict dilewatkan melalui `strip_pii()` sebelum diserialkan ke JSON.

### Keputusan Desain Penting

- **Default lookback 90 hari**: Konstanta `_DEFAULT_LOOKBACK_DAYS = 90` ditetapkan agar UI selalu punya data bermakna meski pengguna tidak mengisi filter tanggal.
- **Active filters di error response**: Ketika terjadi timeout (408), response tetap menyertakan `filters` payload. Ini memudahkan frontend menampilkan pesan error yang kontekstual ("Query timeout dengan filter: QRIS + WA").
- **Skip baris tidak valid di agregasi**: `_aggregate_rows()` dan `_build_trend()` menggunakan `try/except` per baris alih-alih membatalkan seluruh request. Ini mencegah satu baris data kotor merusak keseluruhan response.
- **Fallback rate calculation**: `_build_trend()` mencoba menggunakan `take_up_rate` pre-computed dari Athena, tapi jika nilainya tidak bisa diparsing, dihitung ulang secara lokal via `calculate_take_up_rate()`.
- **PII stripping wajib**: `strip_pii()` dipanggil di langkah terakhir, memastikan tidak ada field sensitif yang lolos meskipun ada perubahan di lapisan sebelumnya.

### Edge Cases yang Ditangani

| Kondisi | Penanganan |
|---------|-----------|
| `start_date` / `end_date` format salah | Return 400 dengan pesan format yang diharapkan |
| Parameter tanggal tidak diisi | Default ke `today - 90 hari` s/d `today` |
| Athena timeout (>30 detik) | Return 408 dengan `filters` aktif dan pesan retry |
| Athena execution error | Return 500 dengan state dan reason dari Athena |
| Hasil query kosong (tidak ada data) | Return 200 dengan pesan "tidak ada data" + `filters` |
| Baris Athena dengan nilai null | Di-skip secara per-baris, tidak crash keseluruhan |
| `total_leads = 0` saat hitung rate | Di-guard: `if total_leads > 0` sebelum `calculate_take_up_rate` |

---

## Struktur Kode

```
handler.py
├── Constants
│   ├── _DEFAULT_LOOKBACK_DAYS: int = 90
│   ├── _DATE_FORMAT: str = "%Y-%m-%d"
│   └── _HEADERS: dict[str, str]          # CORS headers
│
├── Response Helpers
│   ├── _ok(body) → dict                  # Wrap response HTTP 200
│   └── _error(status_code, msg, extra)   # Wrap response error
│
├── Parsing Helpers
│   ├── _parse_string_list(raw) → list    # "a,b,c" → ["a","b","c"]
│   ├── _parse_int_list(raw) → list       # "1,2,3" → [1,2,3]
│   └── _parse_request(params) → CampaignOverviewRequest
│
├── Filter Builder
│   └── _build_active_filters(request) → list[ActiveFilter]
│
├── Aggregation Helpers
│   ├── _aggregate_rows(rows) → (total_leads, total_take_up, total_campaigns)
│   └── _build_trend(rows) → list[TrendDataPoint]
│
└── Entry Point
    └── lambda_handler(event, context) → dict   # Orchestrator utama
```

### Fungsi Kunci

| Fungsi | Signature | Deskripsi |
|--------|-----------|-----------|
| `lambda_handler` | `(event, context) → dict` | Entry point AWS Lambda. Mengkoordinasi seluruh alur dari parse hingga response. |
| `_parse_request` | `(params: dict) → CampaignOverviewRequest` | Mengkonversi raw query string ke dataclass request yang tervalidasi. |
| `_build_active_filters` | `(request) → list[ActiveFilter]` | Membangun daftar filter yang aktif, termasuk `period` sebagai pseudo-filter. |
| `_aggregate_rows` | `(rows: list[dict]) → tuple[int, int, int]` | Menjumlahkan `total_leads`, `total_take_up`, `campaign_count` dari semua baris. |
| `_build_trend` | `(rows: list[dict]) → list[TrendDataPoint]` | Konversi baris Athena ke list `TrendDataPoint` untuk sparkline chart. |
| `_parse_string_list` | `(raw: str | None) → list[str] | None` | Memparse nilai CSV query parameter menjadi list string. |
| `_parse_int_list` | `(raw: str | None) → list[int] | None` | Memparse nilai CSV query parameter menjadi list integer (non-integer dibuang). |

---

## Simulasi / Skenario

### Skenario 1 — Happy Path: Filter 3 Bulan, Program QRIS, Channel WA

**Request (query parameters):**
```
GET /api/campaigns/overview?start_date=2024-06-01&end_date=2024-08-31&flag_program=PROGRAM QRIS&media_blasting=wa
```

**Proses Internal:**

1. **Parse** → `CampaignOverviewRequest(start_date="2024-06-01", end_date="2024-08-31", flag_program=["PROGRAM QRIS"], media_blasting=["wa"])`

2. **Build Active Filters** → 3 filter aktif:
   - `{field: "period", values: ["2024-06-01/2024-08-31"]}`
   - `{field: "flag_program", values: ["PROGRAM QRIS"]}`
   - `{field: "media_blasting", values: ["wa"]}`

3. **Athena Query** → `SELECT period_start, period_end, total_leads, total_take_up, take_up_rate, campaign_count FROM campaign_overview_agg WHERE periode_start BETWEEN '2024-06-01' AND '2024-08-31' AND flag_program IN ('PROGRAM QRIS') AND media_blasting IN ('wa') ORDER BY period_start ASC`

4. **Hasil Athena** → 13 baris (13 minggu dalam ~3 bulan):
   ```
   week 1:  leads=950,  take_up=83,  rate=8.74
   week 2:  leads=980,  take_up=85,  rate=8.67
   ...
   week 13: leads=960,  take_up=84,  rate=8.75
   ```

5. **Aggregate** → `total_leads=12.450`, `total_take_up=1.082`, `total_campaigns=4`

6. **Overall Rate** → `calculate_take_up_rate(12450, 1082)` = **8.69%**

7. **Build Trend** → 13 `TrendDataPoint` untuk sparkline chart

8. **Strip PII** → Tidak ada field PII di response ini (semua agregat)

**Response (HTTP 200):**
```json
{
  "total_leads": 12450,
  "total_take_up": 1082,
  "take_up_rate": 8.69,
  "total_campaigns": 4,
  "trend": [
    {"period_start": "2024-06-03", "period_end": "2024-06-09", "take_up_rate": 8.74, "total_leads": 950, "total_take_up": 83},
    {"period_start": "2024-06-10", "period_end": "2024-06-16", "take_up_rate": 8.67, "total_leads": 980, "total_take_up": 85},
    ...
    {"period_start": "2024-08-26", "period_end": "2024-08-31", "take_up_rate": 8.75, "total_leads": 960, "total_take_up": 84}
  ],
  "filters": [
    {"field": "period", "values": ["2024-06-01/2024-08-31"]},
    {"field": "flag_program", "values": ["PROGRAM QRIS"]},
    {"field": "media_blasting", "values": ["wa"]}
  ]
}
```

---

### Skenario 2 — Tanpa Filter (Default)

**Request:**
```
GET /api/campaigns/overview
```

**Proses:**
- `start_date` default ke `today - 90 hari`
- `end_date` default ke `today`
- Tidak ada filter program, channel, wilayah, maupun jenis_leads
- Query Athena mengambil seluruh data 90 hari terakhir tanpa klausa WHERE tambahan

**Response:** Sama seperti skenario 1 tapi mencakup semua program dan channel, dengan `filters` hanya berisi 1 entry: `period`.

---

### Skenario 3 — Error: Athena Timeout (30 Detik)

**Konteks:** Pengguna menerapkan filter yang menghasilkan scan data sangat besar, atau Athena sedang sibuk.

**Request:**
```
GET /api/campaigns/overview?start_date=2020-01-01&end_date=2024-08-31&wilayah=1,2,3,4,5
```

**Proses:**
- `_parse_request()` berhasil — tanggal dan wilayah valid
- `_build_active_filters()` menghasilkan 2 filter: `period` + `wilayah`
- `athena.execute_query(sql)` → `QueryTimeoutError(timeout_seconds=30)`

**Response (HTTP 408):**
```json
{
  "message": "Query Athena melewati batas waktu (30 detik). Coba persempit filter atau coba kembali.",
  "filters": [
    {"field": "period", "values": ["2020-01-01/2024-08-31"]},
    {"field": "wilayah", "values": ["1", "2", "3", "4", "5"]}
  ]
}
```

Frontend dapat menggunakan `filters` ini untuk menampilkan pesan yang kontekstual: *"Permintaan data untuk rentang 4 tahun dengan 5 wilayah terlalu besar. Coba kurangi rentang tanggal."*

---

### Skenario 4 — Data Kosong

**Request:**
```
GET /api/campaigns/overview?flag_program=PROGRAM QRIS&jenis_leads=Migrasi&wilayah=17
```

**Proses:** Query Athena berjalan sukses, tapi tidak ada baris yang cocok dengan kombinasi filter tersebut.

**Response (HTTP 200):**
```json
{
  "message": "Tidak ada data untuk filter yang dipilih",
  "filters": [
    {"field": "period", "values": ["2024-06-01/2024-08-31"]},
    {"field": "flag_program", "values": ["PROGRAM QRIS"]},
    {"field": "jenis_leads", "values": ["Migrasi"]},
    {"field": "wilayah", "values": ["17"]}
  ]
}
```

---

## Keterkaitan dengan Komponen Lain

### Bergantung pada:
- **`shared/athena_client.py`** — `AthenaClient.build_campaign_overview_query()` untuk membangun SQL, `AthenaClient.execute_query()` untuk menjalankannya
- **`shared/models.py`** — `CampaignOverviewRequest`, `CampaignOverviewResponse`, `TrendDataPoint`, `ActiveFilter`
- **`shared/calculations.py`** — `calculate_take_up_rate()` untuk hitung persentase konversi
- **`shared/pii_filter.py`** — `strip_pii()` wajib dipanggil sebelum response dikirim
- **Tabel Athena `campaign_overview_agg`** — pre-aggregated table, bukan raw leads
- **Environment variables**: `ATHENA_DATABASE`, `ATHENA_S3_OUTPUT`, `ATHENA_WORKGROUP`

### Digunakan oleh:
- **Frontend** — halaman Campaign Overview (`/dashboard/overview`) memanggil endpoint ini
- **Export Service** (Task 4.7) — kemungkinan memanggil logic ini untuk mengisi section overview pada PDF/Excel export

### Pengaruh jika komponen ini berubah:
- Perubahan pada struktur response (menambah/menghapus field) akan mempengaruhi frontend Overview Page
- Perubahan pada default lookback days (`_DEFAULT_LOOKBACK_DAYS`) akan mengubah data yang tampil saat pengguna pertama kali membuka dashboard
- Perubahan pada `_build_active_filters()` mempengaruhi bagaimana error timeout ditampilkan di frontend

---

## Requirements yang Dipenuhi

| Req ID | Deskripsi |
|--------|-----------|
| **1.1** | Tampilkan `total_leads`, `total_take_up`, `take_up_rate`, `total_campaigns` |
| **1.2** | Filter berdasarkan `start_date` / `end_date` (default 90 hari) |
| **1.3** | Filter berdasarkan `flag_program` (multi-value, comma-separated) |
| **1.4** | Filter berdasarkan `media_blasting` (channel) |
| **1.5** | Filter berdasarkan `wilayah` (integer list) dan `jenis_leads` |
| **1.6** | Tampilkan pesan kosong yang informatif ketika tidak ada data |
| **1.7** | Kembalikan data tren (sparkline) sebagai list `TrendDataPoint` |
| **7.5** | Strip PII dari semua API response sebelum dikirim |

---

## Catatan Penting

### Limitasi yang Diketahui
- **Granularitas tren hardcoded per-baris Athena**: Granularitas (weekly/monthly) diatur di `AthenaClient.build_campaign_overview_query()`, bukan di handler ini. Fungsi `select_granularity()` diimport tapi tidak secara eksplisit dipanggil di handler — ini delegasi ke Athena client.
- **Sinkron**: Query Athena dijalankan secara sinkron (blocking). Untuk periode sangat panjang, Lambda bisa timeout sebelum Athena selesai.
- **Tidak ada pagination**: Response mengembalikan semua titik tren sekaligus. Untuk range data sangat panjang, ukuran response bisa besar.

### Asumsi yang Dibuat
- Tabel `campaign_overview_agg` sudah berisi data agregat yang diproses oleh Glue ETL job (`aggregate_metrics.py`). Lambda ini **tidak** membaca tabel `leads` raw.
- `strip_pii()` dari `pii_filter.py` memfilter field `nama_lengkap`, `nomor_rekening`, `nomor_identitas`, `alamat_lengkap` — sesuai implementasi aktual di modul tersebut.
- Environment variable `ATHENA_S3_OUTPUT` harus berisi URI S3 yang valid untuk output query Athena.

### Todo / Pengembangan Berikutnya
- Tambahkan caching (misalnya DynamoDB TTL atau API Gateway cache) untuk query dengan parameter yang sama
- Pertimbangkan async pattern untuk query yang memakan waktu lama
- Tambahkan validasi nilai `flag_program` dan `media_blasting` terhadap `VALID_FLAG_PROGRAM` dan `VALID_MEDIA_BLASTING` di `models.py` agar error lebih cepat tanpa harus menunggu Athena
