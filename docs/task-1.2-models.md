# Task 1.2 — Shared Data Models

## Ringkasan Singkat

File `backend/shared/models.py` mendefinisikan semua struktur data yang digunakan secara bersama di seluruh sistem Campaign Insight Generator. File ini berisi dataclass Python untuk setiap request dan response dari masing-masing endpoint, satu dataclass untuk merepresentasikan baris data leads mentah (`LeadRecord`), serta konstanta validasi yang menjadi satu-satunya sumber kebenaran (single source of truth) untuk nilai-nilai yang diizinkan. Seluruh Lambda handler, ETL pipeline, dan modul bersama bergantung pada model-model ini untuk berkomunikasi dengan format yang konsisten.

---

## Penjelasan Awam (Non-Technical)

Bayangkan sebuah kantor bank yang besar dengan banyak departemen: tim marketing, tim data, tim IT, tim manajemen wilayah. Setiap kali mereka perlu saling bertukar informasi — misalnya laporan performa kampanye QRIS bulan lalu — mereka harus mengisi **formulir standar** yang sudah disepakati bersama.

Formulir ini memastikan bahwa semua departemen menggunakan kolom yang sama, format tanggal yang sama, dan pilihan isian yang sama. Tim marketing tidak akan menulis "WhatsApp" sementara tim data menulis "wa" untuk hal yang sama.

`models.py` adalah kumpulan **formulir standar** tersebut dalam bentuk kode:

- Ada formulir untuk **meminta laporan overview kampanye** (CampaignOverviewRequest)
- Ada formulir untuk **menerima hasilnya** (CampaignOverviewResponse)
- Ada formulir untuk **data satu nasabah leads** (LeadRecord)
- Ada daftar resmi **pilihan channel** yang boleh diisi (`wa`, `digisales`, `telesales`, dst.)

Manfaat bagi pengguna bisnis: jika data yang masuk tidak sesuai formulir standar, sistem langsung menolaknya sebelum menyebabkan hasil yang salah. Laporan yang muncul di dashboard dijamin berasal dari data yang strukturnya benar.

---

## Penjelasan Teknis

**File:** `backend/shared/models.py`

**Library yang digunakan:**
- `dataclasses` — dekorator `@dataclass` dan `field()` untuk mendefinisikan struktur data dengan boilerplate minimal
- `datetime.date` — tipe tanggal untuk `take_up_date` pada `LeadRecord`
- `typing` — `Optional`, `Literal`, `List` untuk anotasi tipe yang ekspresif

**Pola arsitektur:**
- **Plain dataclass** (bukan Pydantic) — ringan, tanpa dependency eksternal, cocok untuk Lambda layer
- **`__post_init__`** digunakan pada `CampaignComparisonRequest` untuk validasi bisnis (jumlah campaign 2–5) yang dijalankan otomatis saat objek dibuat
- **`field(default_factory=list)`** digunakan untuk field list agar tidak ada shared mutable default antar instance
- **`frozenset`** untuk konstanta validasi — immutable, O(1) lookup, hashable

**Keputusan desain penting:**
- `wilayah` bertipe `int` (bukan `str`) karena kode wilayah adalah angka 1–17. Saat dipakai di SQL `IN` clause, dikonversi ke string secara eksplisit.
- Field monitoring report di `LeadRecord` (`take_up_flag`, `take_up_date`, dst.) bersifat `Optional` karena hanya tersedia setelah proses ETL join dengan data laporan monitoring.
- `cif` dimasukkan ke `PII_FIELDS` — modul `pii_filter.py` membaca konstanta ini untuk menghapus field tersebut sebelum data dikirim ke API response.
- `CampaignOverviewResponse.filters` menyimpan `ActiveFilter` aktif agar frontend dapat menampilkan label filter yang sedang aktif tanpa perlu memparsing request ulang.

**Edge cases yang ditangani:**
- `CampaignComparisonRequest.__post_init__` melempar `ValueError` jika `campaign_ids` < 2 atau > 5
- `SimilarCampaignRequest.limit` default 20 untuk mencegah response terlalu besar
- Semua field list pada request menggunakan `Optional[list[...]] = None` (bukan `[]`) sehingga "tidak ada filter" dapat dibedakan dari "filter kosong"

---

## Struktur Kode

### Konstanta Validasi

```python
# Satu-satunya sumber kebenaran untuk nilai yang diizinkan
PII_FIELDS: frozenset[str] = frozenset({"cif"})

VALID_MEDIA_BLASTING: frozenset[str] = frozenset(
    {"wa", "digisales", "telesales", "email", "push notif", "sms"}
)
VALID_FLAG_PROGRAM: frozenset[str] = frozenset(
    {"PROGRAM BIAYA ADMIN", "PROGRAM QRIS"}
)
VALID_SEGMENT_BY_AUM: frozenset[str] = frozenset(
    {"UPPERMASS", "EMERALD", "MASS", "AFFLUENT", "PRIVATE", "HIGH AFFLUENT"}
)
VALID_RANGE_USIA: frozenset[str] = frozenset(
    {"BABY BOOMER", "GEN X", "GEN Y", "GEN Z", "GEN ALPHA"}
)
VALID_SEGMENT_DIV_OWNER: frozenset[str] = frozenset(
    {"CRS", "WEM (Perorangan)"}
)
SIMILAR_CAMPAIGN_DIMENSIONS: frozenset[str] = frozenset(
    {"media_blasting", "jenis_leads", "flag_program"}
)
```

### `ActiveFilter`

```python
@dataclass
class ActiveFilter:
    field: str           # nama kolom, misal "channel" atau "region"
    values: list[str]    # nilai aktif, misal ["wa", "sms"]
```

Digunakan di `CampaignOverviewResponse` dan `ExportRequest` untuk menyimpan filter yang sedang aktif.

---

### `LeadRecord`

```python
@dataclass
class LeadRecord:
    # --- Field inti kampanye (selalu ada) ---
    cif: str                          # ID nasabah (PII — wajib dihapus sebelum response)
    nama_program: str                 # Nama kampanye, misal "Cashback QRIS Vol.3"
    jenis_leads: str                  # Tujuan leads, misal "Migrasi"
    media_blasting: str               # Channel distribusi, misal "wa"
    periode_start: str                # Tanggal blasting (yyyy-mm-dd)
    flag_program: str                 # Jenis program, misal "PROGRAM QRIS"
    wilayah: int                      # Kode wilayah 1–17
    cabang: int                       # Kode cabang 1–324
    outlet: int                       # 0 = KC, 1–99 = outlet
    segment_crs: str                  # Segmen berdasarkan pekerjaan
    segment_by_aum: str               # Segmen berdasarkan tier AUM
    segment_wondr: str                # Segmen permanen berdasarkan usia/pendapatan
    segment_div_owner: str            # Segmen berdasarkan divisi pengelola
    range_usia: str                   # Kelompok generasi usia
    range_saldo_tab: float            # Range saldo tabungan
    avg_aum_3_bln: float              # Rata-rata AUM 3 bulan
    potensi_money: float              # Potensi maksimum yang diharapkan

    # --- Field monitoring report (opsional — diisi setelah ETL join) ---
    take_up_flag: str = "NO"                        # "YES" atau "NO"
    take_up_date: Optional[date] = None             # Tanggal take-up
    time_to_take_up_days: Optional[int] = None      # Jarak hari blasting→take-up
    total_transaction_value: Optional[float] = None # Nilai transaksi realisasi
```

---

### `CampaignOverviewRequest` / `CampaignOverviewResponse` / `TrendDataPoint`

```python
@dataclass
class CampaignOverviewRequest:
    start_date: str                           # Wajib: "2024-01-01"
    end_date: str                             # Wajib: "2024-03-31"
    flag_program: Optional[list[str]] = None  # Filter program, misal ["PROGRAM QRIS"]
    media_blasting: Optional[list[str]] = None# Filter channel, misal ["wa", "sms"]
    wilayah: Optional[list[int]] = None       # Filter wilayah, misal [1, 5, 9]
    jenis_leads: Optional[list[str]] = None   # Filter tujuan leads

@dataclass
class TrendDataPoint:
    period_start: str    # "2024-01-01"
    period_end: str      # "2024-01-07"
    take_up_rate: float  # Persentase 0–100, misal 12.5
    total_leads: int     # Jumlah leads periode ini
    total_take_up: int   # Jumlah konversi periode ini

@dataclass
class CampaignOverviewResponse:
    total_leads: int           # Total leads keseluruhan
    total_take_up: int         # Total konversi keseluruhan
    take_up_rate: float        # Rate keseluruhan (%)
    total_campaigns: int       # Jumlah kampanye unik
    trend: list[TrendDataPoint]     # Data sparkline per periode
    filters: list[ActiveFilter]     # Filter aktif yang diaplikasikan
```

---

### `CampaignComparisonRequest` / `CampaignComparisonResponse` / `CampaignMetric`

```python
@dataclass
class CampaignComparisonRequest:
    campaign_ids: list[str]   # 2–5 ID kampanye; validasi di __post_init__
    group_by: Optional[Literal["flag_program", "wilayah", "media_blasting"]] = None

    def __post_init__(self) -> None:
        # Melempar ValueError jika jumlah kampanye di luar rentang 2–5
        ...

@dataclass
class CampaignMetric:
    campaign_id: str               # ID unik kampanye
    campaign_name: str             # Nama kampanye
    flag_program: str              # Jenis program
    total_leads: int
    total_take_up: int
    take_up_rate: float            # Persentase (%)
    total_transaction_value: float # Total nilai transaksi realisasi
    duration_days: int             # Durasi kampanye dalam hari

@dataclass
class CampaignComparisonResponse:
    campaigns: list[CampaignMetric]  # Satu entri per kampanye
    comparison_chart: dict           # Data siap render untuk frontend
```

---

### `SimilarCampaignRequest` / `SimilarCampaignResult` / `SimilarCampaignResponse`

```python
@dataclass
class SimilarCampaignRequest:
    reference_campaign_id: str       # ID kampanye acuan
    dimensions: list[Literal[        # Dimensi pencocokan (1–3 dimensi)
        "media_blasting",
        "jenis_leads",
        "flag_program"
    ]]
    limit: Optional[int] = 20        # Maksimum hasil yang dikembalikan

@dataclass
class SimilarCampaignResult:
    campaign_id: str
    campaign_name: str
    matching_dimensions: list[str]   # Dimensi yang cocok, misal ["flag_program"]
    dimension_count: int             # Jumlah dimensi yang cocok (convenience field)
    similarity_score: float          # Skor kemiripan 0.0–1.0
    take_up_rate: float
    total_leads: int
    total_take_up: int

@dataclass
class SimilarCampaignResponse:
    similar_campaigns: list[SimilarCampaignResult]  # Urutan: paling mirip dulu
```

---

### `ExportRequest` / `ExportResponse`

```python
@dataclass
class ExportRequest:
    page: str                                # Halaman yang diekspor, misal "overview"
    format: Literal["pdf", "excel", "csv"]  # Format output
    filters: list[ActiveFilter]             # Filter aktif saat export
    time_range_start: str                   # "2024-01-01"
    time_range_end: str                     # "2024-03-31"

@dataclass
class ExportResponse:
    status: Literal["completed", "timeout", "error"]
    download_url: Optional[str] = None      # Pre-signed S3 URL jika berhasil
    error_message: Optional[str] = None     # Pesan error jika gagal
```

---

## Simulasi / Skenario

### Skenario 1 — Request Overview Kampanye QRIS Wilayah Jakarta

Seorang manajer marketing ingin melihat performa kampanye QRIS di wilayah Jakarta (kode 1) selama Q1 2024 melalui channel WhatsApp dan SMS.

**Input (request body dari frontend):**
```json
{
  "start_date": "2024-01-01",
  "end_date": "2024-03-31",
  "flag_program": ["PROGRAM QRIS"],
  "media_blasting": ["wa", "sms"],
  "wilayah": [1]
}
```

**Proses di handler:**
```python
# Lambda handler membuat objek request
req = CampaignOverviewRequest(
    start_date="2024-01-01",
    end_date="2024-03-31",
    flag_program=["PROGRAM QRIS"],
    media_blasting=["wa", "sms"],
    wilayah=[1],
)
# Tidak ada error → objek valid, diteruskan ke AthenaClient
```

**Output (response ke frontend):**
```python
CampaignOverviewResponse(
    total_leads=45_200,
    total_take_up=5_650,
    take_up_rate=12.5,
    total_campaigns=3,
    trend=[
        TrendDataPoint("2024-01-01", "2024-01-31", 11.2, 14800, 1658),
        TrendDataPoint("2024-02-01", "2024-02-29", 13.1, 15600, 2044),
        TrendDataPoint("2024-03-01", "2024-03-31", 13.2, 14800, 1954),
    ],
    filters=[
        ActiveFilter("product", ["PROGRAM QRIS"]),
        ActiveFilter("channel", ["wa", "sms"]),
        ActiveFilter("region", ["1"]),
    ],
)
```

---

### Skenario 2 — Validasi CampaignComparisonRequest Gagal

Tim analitik mengirimkan request perbandingan dengan hanya 1 kampanye.

**Input:**
```python
req = CampaignComparisonRequest(campaign_ids=["CAMP-001"])
# → __post_init__ dipanggil otomatis
```

**Output:**
```
ValueError: campaign_ids must contain at least 2 campaign identifiers, got 1
```

Handler menangkap `ValueError` ini dan mengembalikan HTTP 400 ke frontend dengan pesan yang sesuai.

---

### Skenario 3 — LeadRecord dengan Data Lengkap (Setelah ETL Join)

Data satu nasabah setelah proses ETL menggabungkan data blasting dengan laporan monitoring:

```python
lead = LeadRecord(
    cif="0012345678",           # PII — akan dihapus oleh pii_filter.py
    nama_program="Cashback QRIS Vol.3",
    jenis_leads="Migrasi",
    media_blasting="wa",
    periode_start="2024-02-01",
    flag_program="PROGRAM QRIS",
    wilayah=1,                  # Jakarta
    cabang=101,
    outlet=0,                   # KC
    segment_crs="Karyawan",
    segment_by_aum="MASS",
    segment_wondr="Priority",
    segment_div_owner="WEM (Perorangan)",
    range_usia="GEN Y",
    range_saldo_tab=5_500_000.0,
    avg_aum_3_bln=48_000_000.0,
    potensi_money=10_000_000.0,
    # Field monitoring (diisi setelah ETL join)
    take_up_flag="YES",
    take_up_date=date(2024, 2, 8),
    time_to_take_up_days=7,
    total_transaction_value=8_750_000.0,
)
```

---

## Keterkaitan dengan Komponen Lain

**Bergantung pada:**
- Tidak ada dependency eksternal — `models.py` adalah fondasi, tidak mengimpor modul shared lain

**Digunakan oleh:**
- `backend/shared/athena_client.py` — menerima `CampaignOverviewRequest` di `build_campaign_overview_query()`
- `backend/shared/pii_filter.py` — membaca konstanta `PII_FIELDS` untuk menentukan field yang dihapus
- `backend/shared/filters.py` — menerima `ActiveFilter` dan list leads
- `backend/shared/calculations.py` — menerima list `LeadRecord` untuk kalkulasi metrik
- `backend/lambdas/campaign_overview/handler.py` — menggunakan `CampaignOverviewRequest` / `CampaignOverviewResponse`
- `backend/lambdas/campaign_comparison/handler.py` — menggunakan `CampaignComparisonRequest` / `CampaignMetric`
- `backend/lambdas/similar_campaign/handler.py` — menggunakan `SimilarCampaignRequest` / `SimilarCampaignResponse`
- `backend/lambdas/export_service/handler.py` — menggunakan `ExportRequest` / `ExportResponse`
- `backend/glue_jobs/raw_to_clean.py` — mengacu pada `LeadRecord` sebagai skema target ETL

**Pengaruh ke komponen lain jika diubah:**
- Menambah field baru ke `LeadRecord` memerlukan update di ETL pipeline dan semua unit test
- Mengubah nama field yang sudah ada akan menyebabkan error di semua handler yang menggunakan field tersebut
- Mengubah isi `VALID_MEDIA_BLASTING` akan mengubah perilaku validasi di seluruh sistem secara serentak
- Mengubah tipe `wilayah` dari `int` ke `str` memerlukan perubahan di `athena_client.py` (konversi `str(w)`)

---

## Requirements yang Dipenuhi

| Requirement | Deskripsi |
|-------------|-----------|
| **1.2** | Implementasi shared data models yang digunakan oleh semua komponen backend |
| **1.1** (pendukung) | Struktur `LeadRecord` merepresentasikan skema data mentah kampanye |
| **2.1** (pendukung) | `CampaignComparisonRequest` membatasi perbandingan 2–5 kampanye sesuai spec |
| **3.1** (pendukung) | `TrendDataPoint` menyediakan struktur data untuk analisis tren waktu |
| **5.1** (pendukung) | `SimilarCampaignRequest.dimensions` membatasi dimensi pencocokan ke tiga yang valid |

---

## Catatan Penting

1. **`cif` adalah satu-satunya PII field** — desain document menyebut 4 field PII (nama_lengkap, nomor_rekening, dll.) tetapi field-field tersebut tidak ada di `LeadRecord`. Hanya `cif` yang masuk ke `PII_FIELDS` dan ditangani oleh `pii_filter.py`.

2. **`wilayah` adalah integer, bukan string** — saat digunakan di SQL `IN` clause di `athena_client.py`, harus dikonversi dulu: `[str(w) for w in request.wilayah]`.

3. **`Optional[list[...]] = None` vs `list[...] = field(default_factory=list)`** — field filter request menggunakan `None` sebagai default (bukan `[]`) agar handler dapat membedakan "tidak ada filter diberikan" dari "filter kosong". Filter kosong menghasilkan perilaku berbeda dengan tidak ada filter.

4. **`CampaignComparisonResponse.comparison_chart`** bertipe `dict` yang belum diketik kuat — strukturnya ditentukan oleh handler saat runtime. Ini adalah area yang bisa di-tighten lebih lanjut di iterasi berikutnya.

5. **Tidak ada validasi nilai enum di level dataclass** — validasi bahwa `media_blasting` hanya berisi nilai dari `VALID_MEDIA_BLASTING` dilakukan di layer handler, bukan di `__post_init__`. Satu pengecualian adalah `CampaignComparisonRequest` yang memvalidasi panjang list.

6. **`SimilarCampaignResult.dimension_count`** adalah convenience field yang nilainya redundan dengan `len(matching_dimensions)`. Ini disediakan untuk kemudahan serialisasi ke JSON tanpa perlu kalkulasi ulang di frontend.
