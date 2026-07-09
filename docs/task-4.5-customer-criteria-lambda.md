# Task 4.5 — Customer Criteria Lambda

## Ringkasan Singkat

Lambda handler ini melayani endpoint `GET /api/campaigns/customer-criteria/{id}` yang menganalisis **siapa nasabah yang mengambil produk** dalam sebuah kampanye. Handler ini mengambil data mentah leads dari Amazon Athena, lalu menghitung distribusi demografis dan finansial nasabah — seperti segmen AUM, kelompok usia, wilayah domisili, produk yang dimiliki, dan kategori saldo — dengan memisahkan antara nasabah yang take up (berhasil) dan yang tidak take up (tidak berhasil). Hasilnya membantu tim marketing memahami profil ideal nasabah yang responsif terhadap kampanye.

---

## Penjelasan Awam (Non-Technical)

Bayangkan tim marketing ingin tahu: **"Nasabah seperti apa yang paling banyak menggunakan QRIS setelah kami kirimkan penawaran?"**

Handler ini bekerja seperti seorang peneliti yang:
1. Mengambil semua daftar nasabah yang masuk dalam kampanye
2. Mengelompokkan mereka berdasarkan 5 karakteristik: jenis segmen, kelompok usia, wilayah, produk yang dimiliki, dan kategori saldo
3. Untuk setiap kelompok, menghitung: berapa persen dari total? Dan dari kelompok itu sendiri, berapa persen yang akhirnya take up?
4. Menyajikannya dalam bentuk yang mudah dibaca di dashboard

**Analogi kehidupan nyata:** Seperti tim riset pasar yang menganalisis "Siapa pembeli produk kita? Umur berapa? Dari kalangan mana? Seberapa loyal mereka?" — tapi dalam konteks kampanye bank.

**Manfaat bisnis:**
- Mengetahui segmen mana yang paling responsif → lebih tepat sasaran di kampanye berikutnya
- Mengidentifikasi segmen yang banyak di-target tapi sedikit yang take up → perlu strategi berbeda
- Dasar pengambilan keputusan untuk menentukan kriteria nasabah yang dimasukkan ke kampanye selanjutnya

---

## Penjelasan Teknis

### File yang Terlibat

| File | Peran |
|------|-------|
| `backend/lambdas/customer_criteria/handler.py` | Entry point Lambda, orkestrasi utama |
| `backend/shared/athena_client.py` | Eksekusi query SQL ke Amazon Athena |
| `backend/shared/calculations.py` | Fungsi `compute_distribution_percentages()` |
| `backend/shared/pii_filter.py` | Fungsi `strip_pii()` — menghapus field `cif` sebelum processing |

### Library / Framework

- **AWS Lambda** — serverless compute
- **Amazon Athena** — query ke tabel `leads` di S3 data lake
- `boto3` — AWS SDK (diakses lewat `AthenaClient`)
- `shared.calculations.compute_distribution_percentages` — menghitung persentase distribusi yang menjumlah 100%
- `shared.pii_filter.strip_pii` — menghapus field `cif` (PII) sebelum data diproses

### Pola Arsitektur

- **Lambda Proxy Integration** dengan API Gateway
- **PII-safe pipeline**: data dari Athena langsung di-strip PII sebelum diproses lebih lanjut
- **Fail-partial gracefully**: jika satu atribut tidak tersedia, atribut lain tetap dikembalikan (bukan gagal total)

### Lima Atribut yang Dianalisis

```python
_CUSTOMER_ATTRIBUTES: list[str] = [
    "customer_segment",   # Segmen AUM nasabah (MASS, AFFLUENT, EMERALD, dll)
    "age_group",          # Kelompok usia generasi (GEN Y, GEN X, dll)
    "domicile_region",    # Wilayah domisili nasabah
    "product_holding",    # Produk yang sudah dimiliki nasabah
    "balance_category",   # Kategori saldo tabungan (LOW, MEDIUM, HIGH)
]
```

### Alur Eksekusi (7 Langkah)

```
1. Ekstrak campaign_id dari path parameter, validasi tidak kosong
2. Inisialisasi AthenaClient dari environment variable
3. Build SQL via athena.build_customer_criteria_query(campaign_id)
4. Eksekusi query → tangani QueryTimeoutError (408) & QueryExecutionError (500)
5. Handle empty result → kembalikan 200 dengan pesan "tidak ada data"
6. Strip PII via strip_pii(rows) — hapus field 'cif' dari semua baris
7. Loop 5 atribut → _build_attribute_distribution(rows, attr) → compile response
```

### Fungsi Inti: `_build_attribute_distribution()`

Fungsi ini adalah jantung dari handler. Untuk setiap atribut:

```python
def _build_attribute_distribution(
    rows: list[dict[str, Any]],
    attribute: str,
) -> dict[str, Any]:
    """
    Menghitung distribusi untuk satu atribut.
    
    1. Group rows by nilai atribut
    2. Hitung total per group
    3. Hitung berapa yang take_up_flag == "YES" per group
    4. Hitung persentase keseluruhan (via compute_distribution_percentages)
    5. Hitung take_up_percentage per group (take_up_count / group_count × 100)
    6. Urutkan by count DESC
    7. Jika semua nilai null → tandai sebagai unavailable
    """
```

**Output per atribut:**
```json
{
  "attribute": "customer_segment",
  "available": true,
  "items": [
    {
      "label": "MASS",
      "count": 1950,
      "percentage": 65.0,
      "take_up_count": 164,
      "take_up_percentage": 8.4
    }
  ],
  "unavailable_reason": null
}
```

### Keputusan Desain Penting

| Keputusan | Alasan |
|-----------|--------|
| PII di-strip **sebelum** processing, bukan di response | Defense-in-depth: `cif` tidak pernah ada di variabel Python setelah `strip_pii()` |
| Atribut unavailable tidak crash, tapi ditandai | Data kampanye lama mungkin tidak punya semua atribut; partial response lebih baik dari error |
| Baris dengan nilai null untuk atribut di-skip (bukan dihitung sebagai "unknown") | Mencegah distorsi distribusi dari data yang tidak lengkap |
| `take_up_percentage` = take_up_count / group_count (bukan / total) | Ini adalah conversion rate per segment, bukan share dari seluruh take_up |
| Items diurutkan by count DESC | Segmen terbesar muncul pertama untuk keterbacaan dashboard |

### Edge Cases yang Ditangani

- `campaign_id` kosong/whitespace → HTTP 400
- Query Athena timeout → HTTP 408
- Query Athena gagal → HTTP 500
- Tidak ada data untuk campaign → HTTP 200 dengan pesan informatif
- Atribut dengan semua nilai null → `available: false` dengan `unavailable_reason`
- `take_up_flag` selain "YES" → dianggap tidak take up (no assumption about specific strings)
- Beberapa atribut unavailable, lainnya tersedia → response partial dengan `partial_data_message`

---

## Struktur Kode

### Fungsi Publik

```python
def lambda_handler(event: dict, context: Any) -> dict[str, Any]:
    """Entry point. Orkestrasi dari parse → Athena → strip PII → distribusi → response."""
```

### Fungsi Helper Privat

```python
def _ok(body: dict[str, Any]) -> dict[str, Any]:
    """HTTP 200 response dengan body JSON + CORS header (Access-Control-Allow-Origin: *)."""

def _error(status_code: int, message: str, extra: dict | None = None) -> dict[str, Any]:
    """HTTP error response. extra dict untuk field tambahan seperti campaign_id."""

def _build_attribute_distribution(
    rows: list[dict[str, Any]],
    attribute: str,
) -> dict[str, Any]:
    """Inti kalkulasi: hitung distribusi satu atribut dari baris mentah Athena."""
```

### Konstanta

```python
_CUSTOMER_ATTRIBUTES: list[str]  # 5 atribut yang dianalisis, urutan: demografi dulu
_TAKE_UP_YES: str = "YES"        # Nilai take_up_flag yang dianggap berhasil (case-insensitive via .upper())
_HEADERS: dict[str, str]         # Content-Type + CORS header
```

### Dependency Eksternal

```python
from shared.athena_client import AthenaClient, QueryExecutionError, QueryTimeoutError
from shared.calculations import compute_distribution_percentages
from shared.pii_filter import strip_pii
```

---

## Simulasi / Skenario

### Skenario 1 — Happy Path: Distribusi Lengkap

**Input (API Gateway Event):**
```json
{
  "pathParameters": { "campaign_id": "QRIS-AUG-2024" }
}
```

**Data Athena (3000 baris lead, disederhanakan):**
- MASS: 1950 nasabah (138 take up = 7.1%), AFFLUENT: 750 (84 take up = 11.2%), EMERALD: 300 (20 take up = 6.8%)
- GEN Y: 1260 (53 take up = 4.2%), GEN X: 1050 (78 take up = 7.4%), GEN Z: 450 (32 take up = 7.1%), BABY BOOMER: 240 (19 take up = 7.9%)
- LOW balance: 900 (58 take up = 6.4%), MEDIUM balance: 1350 (116 take up = 8.6%), HIGH balance: 750 (68 take up = 9.1%)

**Output (HTTP 200):**
```json
{
  "campaign_id": "QRIS-AUG-2024",
  "distributions": [
    {
      "attribute": "customer_segment",
      "available": true,
      "items": [
        {
          "label": "MASS",
          "count": 1950,
          "percentage": 65.0,
          "take_up_count": 164,
          "take_up_percentage": 8.4
        },
        {
          "label": "AFFLUENT",
          "count": 750,
          "percentage": 25.0,
          "take_up_count": 84,
          "take_up_percentage": 11.2
        },
        {
          "label": "EMERALD",
          "count": 300,
          "percentage": 10.0,
          "take_up_count": 20,
          "take_up_percentage": 6.8
        }
      ],
      "unavailable_reason": null
    },
    {
      "attribute": "age_group",
      "available": true,
      "items": [
        {
          "label": "GEN Y",
          "count": 1260,
          "percentage": 42.0,
          "take_up_count": 53,
          "take_up_percentage": 4.2
        },
        {
          "label": "GEN X",
          "count": 1050,
          "percentage": 35.0,
          "take_up_count": 78,
          "take_up_percentage": 7.4
        },
        {
          "label": "GEN Z",
          "count": 450,
          "percentage": 15.0,
          "take_up_count": 32,
          "take_up_percentage": 7.1
        },
        {
          "label": "BABY BOOMER",
          "count": 240,
          "percentage": 8.0,
          "take_up_count": 19,
          "take_up_percentage": 7.9
        }
      ],
      "unavailable_reason": null
    },
    {
      "attribute": "balance_category",
      "available": true,
      "items": [
        {
          "label": "MEDIUM",
          "count": 1350,
          "percentage": 45.0,
          "take_up_count": 116,
          "take_up_percentage": 8.6
        },
        {
          "label": "LOW",
          "count": 900,
          "percentage": 30.0,
          "take_up_count": 58,
          "take_up_percentage": 6.4
        },
        {
          "label": "HIGH",
          "count": 750,
          "percentage": 25.0,
          "take_up_count": 68,
          "take_up_percentage": 9.1
        }
      ],
      "unavailable_reason": null
    }
  ],
  "available_attributes": ["customer_segment", "age_group", "balance_category"],
  "unavailable_attributes": ["domicile_region", "product_holding"]
}
```

**Interpretasi insight:**
- Segmen AFFLUENT memiliki `take_up_percentage` tertinggi (11.2%) meskipun hanya 25% dari total leads → efektif untuk AFFLUENT
- GEN Y paling banyak ditarget (42%) tapi `take_up_percentage`-nya paling rendah (4.2%) → strategi perlu dievaluasi untuk GEN Y
- Saldo HIGH (25% dari leads) punya `take_up_percentage` 9.1% — target yang efisien

---

### Skenario 2 — Atribut Tidak Tersedia (Partial Data)

Misalnya tabel `leads` untuk kampanye lama tidak punya kolom `domicile_region` dan `product_holding`.

**Output tambahan di response:**
```json
{
  "unavailable_attributes": ["domicile_region", "product_holding"],
  "partial_data_message": "Atribut berikut tidak tersedia untuk campaign ini: domicile_region, product_holding."
}
```

Dan di dalam `distributions`, kedua atribut itu akan muncul sebagai:
```json
{
  "attribute": "domicile_region",
  "available": false,
  "items": [],
  "unavailable_reason": "Atribut 'domicile_region' tidak tersedia untuk campaign ini."
}
```

Frontend dapat menampilkan placeholder atau pesan "Data tidak tersedia" untuk chart atribut ini, tanpa seluruh halaman error.

---

### Skenario 3 — Error: campaign_id Kosong

**Input:**
```json
{
  "pathParameters": { "campaign_id": "   " }
}
```

**Output (HTTP 400):**
```json
{
  "message": "Parameter 'campaign_id' wajib diisi."
}
```

---

### Skenario 4 — Error: Query Timeout

Query Athena melewati batas waktu (misalnya leads tabel sangat besar).

**Output (HTTP 408):**
```json
{
  "message": "Query Athena melewati batas waktu (30 detik). Coba kembali beberapa saat lagi."
}
```

---

### Skenario 5 — Tidak Ada Data

Campaign ID valid tapi tidak ada leads terdaftar.

**Output (HTTP 200):**
```json
{
  "campaign_id": "QRIS-AUG-2024",
  "message": "Tidak ada data karakteristik nasabah untuk campaign ini."
}
```

---

## Keterkaitan dengan Komponen Lain

### Bergantung Pada

| Komponen | Ketergantungan |
|----------|----------------|
| `shared/athena_client.py` | Build query SQL dan eksekusi ke Athena dengan polling |
| `shared/calculations.py` → `compute_distribution_percentages()` | Menghitung persentase yang menjumlah 100% dari group counts |
| `shared/pii_filter.py` → `strip_pii()` | Menghapus field `cif` (PII) dari semua baris sebelum diproses |
| Tabel Athena `leads` | Sumber data mentah per lead dengan semua atribut nasabah |
| Environment variable `ATHENA_DATABASE` | Nama database Athena |
| Environment variable `ATHENA_S3_OUTPUT` | Lokasi S3 untuk hasil query |
| Environment variable `ATHENA_WORKGROUP` | Workgroup Athena |

### Digunakan Oleh

| Komponen | Penggunaan |
|----------|------------|
| API Gateway | Route `GET /api/campaigns/customer-criteria/{campaign_id}` |
| CDK ApiStack | Mendefinisikan Lambda dan routing |
| Frontend halaman Customer Criteria | Konsumsi data untuk chart distribusi (pie chart, bar chart per segmen) |

### Pengaruh Jika Berubah

- Penambahan atribut baru ke `_CUSTOMER_ATTRIBUTES` → atribut tersebut langsung dianalisis (tidak perlu ubah logika lain)
- Perubahan nilai `_TAKE_UP_YES` → definisi "berhasil" berubah untuk seluruh distribusi
- Perubahan skema tabel `leads` → nama kolom di atribut harus disesuaikan
- Perubahan `compute_distribution_percentages()` → persentase di semua distribusi berubah
- Perubahan `strip_pii()` → field PII apa yang dihapus sebelum processing berubah

---

## Requirements yang Dipenuhi

| Requirement | Deskripsi |
|-------------|-----------|
| **5.1** | Distribusi atribut demografis: `customer_segment` dan `age_group` dengan persentase per grup |
| **5.2** | Distribusi atribut finansial: `balance_category` dan `product_holding` |
| **5.3** | Perbandingan take-up vs non-take-up: `take_up_percentage` per label menunjukkan conversion rate per segmen |
| **5.4** | `take_up_percentage` dihitung per group (`take_up_count / group_count × 100`) untuk insight yang akurat |
| **5.5** | Graceful handling atribut yang tidak tersedia: `available: false` dengan `unavailable_reason`, partial data message |
| **7.5** | PII protection: `cif` di-strip via `strip_pii()` sebelum data diproses (tidak masuk response) |

---

## Catatan Penting

### Limitasi yang Diketahui

1. **`_CUSTOMER_ATTRIBUTES` menggunakan nama kolom seperti `customer_segment` dan `age_group`** — berbeda dari nama field `LeadRecord` (`segment_by_aum` dan `range_usia`). Ini berarti handler bergantung pada nama kolom yang di-return oleh `athena.build_customer_criteria_query()`, bukan langsung dari `LeadRecord`. Pastikan alias SQL dalam query Athena konsisten dengan list ini.

2. **Tidak ada sorting untuk items berdasarkan `take_up_percentage`** — items diurutkan berdasarkan `count` DESC. Jika kebutuhan berubah menjadi "segmen dengan take_up_rate tertinggi di atas", perlu modifikasi.

3. **`domicile_region` dan `product_holding` mungkin sering unavailable** untuk kampanye lama yang tidak memiliki data tersebut di kolom tabel `leads`.

4. **Query mengambil seluruh data mentah** (bukan agregat) — untuk kampanye dengan jutaan leads, ini bisa menjadi bottleneck. Pertimbangkan pre-aggregation di ETL layer.

### Asumsi yang Dibuat

- `take_up_flag` di tabel `leads` berisi `"YES"` untuk nasabah yang berhasil take up (sudah di-uppercase sebelum perbandingan)
- Tabel `leads` sudah di-populate dan di-join dengan monitoring report oleh Glue ETL job
- Field `cif` adalah satu-satunya PII yang perlu di-strip (sesuai `PII_FIELDS` di `models.py`)
- Query `build_customer_criteria_query()` di `athena_client.py` mengembalikan kolom dengan nama yang cocok dengan `_CUSTOMER_ATTRIBUTES`

### Todo untuk Pengembangan Berikutnya

- [ ] Tambahkan test unit untuk skenario `available: false` pada atribut yang semua nilainya null
- [ ] Pertimbangkan pindahkan distribusi kalkulasi ke Athena SQL (GROUP BY) untuk efisiensi pada dataset besar
- [ ] Tambahkan sorting opsional by `take_up_percentage` DESC (parameter query `sort_by=take_up_rate`)
- [ ] Validasi apakah nama kolom di `_CUSTOMER_ATTRIBUTES` match dengan output `build_customer_criteria_query()`
- [ ] Pertimbangkan menambahkan `total_leads` dan `total_take_up` di level response (bukan per atribut) untuk konteks umum
