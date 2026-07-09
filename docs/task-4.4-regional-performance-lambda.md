# Task 4.4 — Regional Performance Lambda

## Ringkasan Singkat

Lambda handler ini melayani endpoint `GET /api/campaigns/regional/{id}` yang mengembalikan performa kampanye perbanking dipecah per wilayah (1–17 wilayah di seluruh Indonesia). Data yang dikembalikan mencakup jumlah leads, jumlah nasabah yang take up, take_up_rate, dan rata-rata nilai transaksi untuk setiap wilayah — diurutkan dari wilayah dengan performa tertinggi ke terendah. Jika pengguna memilih satu wilayah tertentu, handler ini juga mengembalikan data tren mingguan 8 titik untuk wilayah tersebut.

---

## Penjelasan Awam (Non-Technical)

Bayangkan sebuah peta Indonesia yang dipecah menjadi 17 area. Campaign Manager ingin tahu: **"Di area mana kampanye QRIS Agustus 2024 paling berhasil?"**

Handler ini bekerja seperti seorang analis yang:
1. Mengambil semua data leads kampanye tersebut dari gudang data
2. Mengelompokkannya per wilayah
3. Menghitung persentase keberhasilan (berapa persen nasabah yang benar-benar menggunakan produk) di tiap wilayah
4. Menyajikan hasilnya diurutkan dari wilayah terbaik ke terburuk

**Analogi kehidupan nyata:** Seperti laporan penjualan franchise makanan yang menampilkan cabang mana yang paling laris, diurutkan dari omset tertinggi.

**Manfaat bisnis:**
- Campaign Owner dapat segera tahu wilayah mana yang perlu didorong lebih keras
- Tim regional dapat memfokuskan sumber daya ke area yang underperform
- Manajer dapat melihat tren mingguan suatu wilayah untuk mendeteksi apakah performa sedang naik atau turun

---

## Penjelasan Teknis

### File yang Terlibat

| File | Peran |
|------|-------|
| `backend/lambdas/regional_performance/handler.py` | Entry point Lambda, orkestrasi utama |
| `backend/shared/athena_client.py` | Eksekusi query SQL ke Amazon Athena |
| `backend/shared/sorting.py` | Fungsi `sort_regional_performance()` |

### Library / Framework

- **AWS Lambda** — serverless compute, dipanggil via API Gateway
- **Amazon Athena** — query engine berbasis SQL di atas S3 data lake
- `boto3` — AWS SDK untuk Python (diakses lewat `AthenaClient` wrapper)
- `shared.athena_client.AthenaClient` — custom wrapper yang menangani polling, timeout, dan error

### Pola Arsitektur

Handler mengikuti pola **Lambda Proxy Integration** dengan API Gateway:
- Event masuk → parse parameter → query Athena → transform data → return JSON response
- Semua exception ditangkap dan dikonversi ke HTTP response yang bermakna (tidak ada unhandled exception)

### Alur Eksekusi (10 Langkah)

```
1. Ekstrak campaign_id dari path parameter
2. Ekstrak query parameter opsional (flag_program, selected_region)
3. Inisialisasi AthenaClient dari environment variable
4. Build SQL query regional via athena.build_regional_query(campaign_id)
5. Eksekusi query → tangani QueryTimeoutError (408) & QueryExecutionError (500)
6. Handle empty result → kembalikan 200 dengan regions: []
7. Terapkan filter flag_program jika ada
8. Build list dict per wilayah, konversi tipe data dengan _to_int / _to_float
9. Sort by take_up_rate DESC via sort_regional_performance()
10. Build tren 8 minggu untuk selected_region jika diminta
```

### Keputusan Desain Penting

| Keputusan | Alasan |
|-----------|--------|
| Filter `flag_program` dilakukan di Python, bukan SQL | Query Athena sudah dieksekusi sebelum filter diketahui; mencegah query kedua |
| Row malformed di-skip (bukan crash) | Satu baris data rusak tidak boleh merusak seluruh response |
| Tren diambil dari baris yang memiliki `week_start` != None | Data mingguan dan data agregat berbagi tabel; kolom `week_start` sebagai penanda |
| Konstanta `_TREND_WEEKS = 8` | Keputusan bisnis: tren 8 minggu cukup untuk mendeteksi pola tanpa overload frontend |
| Timeout → HTTP 408 bukan 500 | Timeout bukan kesalahan server, klien bisa retry dengan harapan query lebih ringan |

### Edge Cases yang Ditangani

- `campaign_id` kosong / tidak ada → HTTP 400
- `selected_region` bukan integer → HTTP 400
- Query Athena timeout → HTTP 408 dengan pesan retry
- Query Athena gagal → HTTP 500 dengan reason dari exception
- Tidak ada data untuk campaign → HTTP 200 dengan `regions: []`
- Setelah filter `flag_program`, tidak ada data tersisa → HTTP 200 dengan `regions: []`
- Row dengan tipe data rusak (non-numeric) → baris di-skip, bukan crash

---

## Struktur Kode

### Fungsi Utama

```python
def lambda_handler(event: dict, context: Any) -> dict[str, Any]:
    """Entry point Lambda. Orkestrasi 10 langkah dari parse → response."""
```

### Fungsi Helper Privat

```python
def _response(status_code: int, body: dict[str, Any]) -> dict[str, Any]:
    """Membungkus body dict menjadi format Lambda Proxy Integration response."""

def _to_int(value: Any) -> int:
    """Konversi aman ke int. Mengembalikan 0 jika gagal.
    
    Dibutuhkan karena Athena mengembalikan semua nilai sebagai string."""

def _to_float(value: Any) -> float:
    """Konversi aman ke float. Mengembalikan 0.0 jika gagal."""
```

### Konstanta

```python
_HEADERS: dict[str, str]  # Content-Type JSON, dipakai di semua response
_TREND_WEEKS: int = 8     # Jumlah titik data tren mingguan yang dikembalikan
```

### Dependency Eksternal

```python
from shared.athena_client import AthenaClient, QueryExecutionError, QueryTimeoutError
from shared.sorting import sort_regional_performance
```

---

## Simulasi / Skenario

### Skenario 1 — Happy Path: Semua Wilayah Berhasil

**Input (API Gateway Event):**
```json
{
  "pathParameters": { "campaign_id": "QRIS-AUG-2024" },
  "queryStringParameters": null
}
```

**Proses:**
1. `campaign_id = "QRIS-AUG-2024"`, tidak ada filter
2. Athena query mengambil 17 baris (1 per wilayah)
3. `sort_regional_performance()` mengurutkan berdasarkan `take_up_rate` DESC

**Output (HTTP 200):**
```json
{
  "campaign_id": "QRIS-AUG-2024",
  "regions": [
    {
      "wilayah": 3,
      "leads_count": 4500,
      "take_up_count": 558,
      "take_up_rate": 12.4,
      "avg_transaction_value": 185000.0
    },
    {
      "wilayah": 1,
      "leads_count": 3200,
      "take_up_count": 314,
      "take_up_rate": 9.8,
      "avg_transaction_value": 220000.0
    },
    {
      "wilayah": 5,
      "leads_count": 2900,
      "take_up_count": 235,
      "take_up_rate": 8.1,
      "avg_transaction_value": 175000.0
    }
  ],
  "selected_region_trend": null,
  "flag_program_filter": null
}
```

**Interpretasi:** Wilayah 3 (Jawa Tengah) memimpin dengan take_up_rate 12.4%, diikuti Wilayah 1 (Jakarta) 9.8%, dan Wilayah 5 (Jawa Barat) 8.1%.

---

### Skenario 2 — Drill Down: Tren Mingguan Wilayah 3

**Input:**
```json
{
  "pathParameters": { "campaign_id": "QRIS-AUG-2024" },
  "queryStringParameters": { "selected_region": "3" }
}
```

**Proses:**
1. `selected_region = 3` (parsed sebagai integer)
2. Query Athena mengembalikan data utama + data mingguan
3. Baris dengan `week_start != None` dan `region == 3` difilter
4. Diurutkan ascending by `week_start`, diambil 8 terakhir

**Output — field `selected_region_trend`:**
```json
"selected_region_trend": [
  { "week_start": "2024-07-01", "leads_count": 530, "take_up_count": 58, "take_up_rate": 10.9 },
  { "week_start": "2024-07-08", "leads_count": 545, "take_up_count": 63, "take_up_rate": 11.6 },
  { "week_start": "2024-07-15", "leads_count": 560, "take_up_count": 67, "take_up_rate": 12.0 },
  { "week_start": "2024-07-22", "leads_count": 572, "take_up_count": 71, "take_up_rate": 12.4 },
  { "week_start": "2024-07-29", "leads_count": 580, "take_up_count": 73, "take_up_rate": 12.6 },
  { "week_start": "2024-08-05", "leads_count": 590, "take_up_count": 76, "take_up_rate": 12.9 },
  { "week_start": "2024-08-12", "leads_count": 600, "take_up_count": 78, "take_up_rate": 13.0 },
  { "week_start": "2024-08-19", "leads_count": 523, "take_up_count": 72, "take_up_rate": 13.8 }
]
```

**Interpretasi:** Wilayah 3 menunjukkan tren naik konsisten selama 8 minggu — dari 10.9% ke 13.8%, mengindikasikan kampanye semakin efektif di wilayah ini.

---

### Skenario 3 — Filter Produk: Hanya PROGRAM QRIS

**Input:**
```json
{
  "pathParameters": { "campaign_id": "QRIS-AUG-2024" },
  "queryStringParameters": { "flag_program": "PROGRAM QRIS" }
}
```

**Proses:** Setelah Athena query, baris yang `product != "PROGRAM QRIS"` dibuang di Python.

**Output:** Sama seperti Skenario 1 tapi hanya menampilkan wilayah yang memiliki aktivitas PROGRAM QRIS.

---

### Skenario 4 — Error: Campaign Tidak Ada

**Input:**
```json
{
  "pathParameters": { "campaign_id": "TIDAK-ADA-123" },
  "queryStringParameters": null
}
```

**Output (HTTP 200):**
```json
{
  "campaign_id": "TIDAK-ADA-123",
  "message": "Data regional tidak tersedia untuk campaign ini",
  "regions": [],
  "selected_region_trend": null,
  "flag_program_filter": null
}
```

**Catatan:** Athena mengembalikan 0 baris → handler mengembalikan 200 (bukan 404) dengan array kosong dan pesan informatif. Ini adalah keputusan desain agar frontend tetap bisa render halaman kosong tanpa error handling tambahan.

---

### Skenario 5 — Error: Query Timeout

**Output (HTTP 408):**
```json
{
  "error": "Regional performance query timed out. Please try again.",
  "campaign_id": "QRIS-AUG-2024"
}
```

---

## Keterkaitan dengan Komponen Lain

### Bergantung Pada

| Komponen | Ketergantungan |
|----------|----------------|
| `shared/athena_client.py` | Eksekusi SQL ke Athena, polling status, error handling |
| `shared/sorting.py` → `sort_regional_performance()` | Pengurutan wilayah by `take_up_rate` DESC |
| Tabel Athena `regional_performance_agg` | Sumber data utama per wilayah per minggu |
| Environment variable `ATHENA_DATABASE` | Nama database Athena yang digunakan |
| Environment variable `ATHENA_S3_OUTPUT` | Lokasi S3 untuk menyimpan hasil query |
| Environment variable `ATHENA_WORKGROUP` | Workgroup Athena (default: `"primary"`) |
| Environment variable `AWS_REGION` | Region AWS tempat Athena berjalan |

### Digunakan Oleh

| Komponen | Penggunaan |
|----------|------------|
| API Gateway | Route `GET /api/campaigns/regional/{campaign_id}` diarahkan ke Lambda ini |
| CDK ApiStack | Mendefinisikan Lambda function dan route di API Gateway |
| Frontend halaman Regional Performance | Konsumsi data untuk chart peta wilayah dan grafik tren |

### Pengaruh Jika Berubah

- Perubahan skema tabel `regional_performance_agg` (nama kolom) → handler perlu diupdate di bagian build dict wilayah (step 7)
- Perubahan `sort_regional_performance()` di `sorting.py` → urutan tampilan wilayah berubah
- Penambahan kolom baru di Athena → perlu ditambahkan secara eksplisit di step 7 (tidak otomatis)
- Perubahan konstanta `_TREND_WEEKS` → jumlah titik grafik tren yang dikembalikan berubah

---

## Requirements yang Dipenuhi

| Requirement | Deskripsi |
|-------------|-----------|
| **4.1** | Menampilkan data per wilayah: `leads_count`, `take_up_count`, `take_up_rate`, `avg_transaction_value` |
| **4.2** | Wilayah diurutkan berdasarkan `take_up_rate` descending (tertinggi di atas) |
| **4.3** | Tren 8 minggu untuk wilayah yang dipilih (`selected_region_trend`) |
| **4.4** | Filter opsional berdasarkan `flag_program` (jenis produk) |
| **4.5** | Graceful handling ketika data tidak tersedia — mengembalikan array kosong dengan pesan, bukan error |

---

## Catatan Penting

### Limitasi yang Diketahui

1. **Filter di Python, bukan SQL** — `flag_program` difilter setelah data diambil dari Athena. Jika ada ribuan wilayah di masa depan, ini bisa inefisien. Solusi: tambahkan parameter filter ke `build_regional_query()`.

2. **Data tren bergantung pada kolom `week_start`** — Jika ETL tidak mengisi `week_start` (misalnya saat backfill), tren tidak akan muncul meskipun data ada.

3. **Tidak ada validasi `campaign_id`** — Handler tidak memverifikasi apakah `campaign_id` adalah ID yang valid sebelum query ke Athena. Athena hanya mengembalikan 0 baris untuk ID yang tidak ada.

4. **Tidak ada paginasi** — Seluruh 17 wilayah dikembalikan sekaligus. Jika jumlah wilayah bertambah secara signifikan di masa depan, perlu ditambahkan paginasi.

### Asumsi yang Dibuat

- `wilayah` adalah integer 1–17 sesuai domain data model
- Tabel `regional_performance_agg` sudah di-populate oleh Glue job `regional_rollup` (task 7.4)
- Kolom `week_start` ada di tabel dan terisi untuk data mingguan
- Satu baris per `(campaign_id, wilayah)` untuk data agregat keseluruhan

### Todo untuk Pengembangan Berikutnya

- [ ] Pindahkan filter `flag_program` ke level SQL untuk efisiensi
- [ ] Tambahkan validasi format `campaign_id` (misalnya regex pattern)
- [ ] Tambahkan unit test untuk skenario `selected_region` dengan data mingguan kosong
- [ ] Pertimbangkan cache layer (ElastiCache) untuk query yang sering diulang
- [ ] Tambahkan field `nama_wilayah` (string nama daerah) di samping kode integer `wilayah`
