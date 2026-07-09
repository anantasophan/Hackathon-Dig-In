# Database Design — Campaign Insight Generator

> Dokumen ini menjelaskan desain database dari dua sudut pandang: **bisnis** (kenapa data ini ada dan apa maknanya) dan **teknis** (bagaimana data disimpan, diproses, dan diakses). Dilengkapi simulasi alur data ketika platform berjalan.

---

## Daftar Isi

1. [Filosofi: Kenapa Bukan Database Relasional?](#1-filosofi-kenapa-bukan-database-relasional)
2. [Sisi Bisnis: Apa yang Disimpan dan Kenapa](#2-sisi-bisnis-apa-yang-disimpan-dan-kenapa)
3. [Sisi Teknis: Struktur Penyimpanan](#3-sisi-teknis-struktur-penyimpanan)
4. [Entity Relationship (Logical)](#4-entity-relationship-logical)
5. [Alur Data — ETL Pipeline](#5-alur-data--etl-pipeline)
6. [Simulasi: Platform Berjalan](#6-simulasi-platform-berjalan)
7. [Catatan Penting & Keterbatasan](#7-catatan-penting--keterbatasan)

---

## 1. Filosofi: Kenapa Bukan Database Relasional?

Sistem ini **sengaja tidak menggunakan RDBMS** (PostgreSQL, MySQL, dll). Ini keputusan arsitektur, bukan keterbatasan.

| Karakteristik Data Campaign | Implikasinya |
|-----------------------------|--------------|
| Data hanya **ditambah**, tidak pernah diubah/dihapus | Tidak butuh UPDATE/DELETE — cocok untuk data lake |
| **Analitik**, bukan transaksional | Query aggregasi (SUM, COUNT, AVG) lebih optimal di Athena |
| Volume **historis besar** (semua campaign masa lalu) | S3 + Parquet jauh lebih murah dari RDS untuk skala ini |
| **Bursty read** (ramai jam kerja, sepi di luar jam kerja) | Serverless (Athena, Lambda) auto-scale tanpa idle cost |

**Kesimpulan**: Sistem ini adalah **analytics platform**, bukan sistem operasional. Pola aksesnya adalah "baca banyak, tulis sekali" — persis cocok untuk data lake pattern.

---

## 2. Sisi Bisnis: Apa yang Disimpan dan Kenapa

### 2.1 Data Leads

**Apa ini secara bisnis?**
Leads adalah daftar nasabah yang diberikan Divisi Data kepada Divisi Bisnis untuk di-approach dalam sebuah campaign. Setiap baris = satu nasabah yang ditargetkan.

**Kenapa disimpan?**
- Untuk mengetahui **siapa yang ditarget** (profil, segmen, wilayah)
- Untuk mengetahui **siapa yang akhirnya take up** (transaksi terjadi)
- Sebagai bahan evaluasi: apakah kriteria leads yang diberikan tepat sasaran?

**Field bisnis yang penting:**

| Field | Makna Bisnis |
|-------|-------------|
| `cif` | ID unik nasabah — ini PII, tidak pernah ditampilkan di dashboard |
| `nama_program` | Nama campaign, misalnya "Cashback QRIS Agustus 2024" |
| `flag_program` | Jenis program: `PROGRAM QRIS` atau `PROGRAM BIAYA ADMIN` |
| `jenis_leads` | Tujuan leads: misalnya "Migrasi", "Akuisisi", "Retensi" |
| `media_blasting` | Channel distribusi: WA, email, telesales, digisales, dll |
| `wilayah` | Kode wilayah kantor (1–17, sesuai struktur regional bank) |
| `segment_by_aum` | Segmentasi nasabah berdasarkan aset: MASS, AFFLUENT, EMERALD, dll |
| `range_usia` | Generasi: Gen Z, Gen Y, Gen X, Baby Boomer, Gen Alpha |
| `potensi_money` | Estimasi nilai transaksi maksimal yang mungkin terealisasi |
| `take_up_flag` | Apakah nasabah akhirnya transaksi? (`YES` / `NO`) |
| `take_up_date` | Tanggal transaksi terjadi (kosong jika tidak take up) |
| `time_to_take_up_days` | Berapa hari dari distribusi leads sampai transaksi |
| `total_transaction_value` | Nilai transaksi aktual yang terealisasi |


### 2.2 Data Agregat Campaign

**Apa ini secara bisnis?**
Ringkasan performa campaign yang sudah dihitung oleh sistem secara otomatis setiap hari. Campaign Owner tidak perlu menunggu query berat — data sudah siap.

**Kenapa disimpan terpisah?**
Menghitung `take_up_rate` dari jutaan baris leads setiap kali user membuka dashboard akan lambat. Glue ETL menghitungnya sekali per malam, hasilnya disimpan sebagai agregat siap pakai.

| Field | Makna Bisnis |
|-------|-------------|
| `period_start` / `period_end` | Periode ringkasan (mingguan atau bulanan) |
| `granularity` | `weekly` untuk periode ≤3 bulan, `monthly` untuk >3 bulan |
| `total_leads` | Total leads yang didistribusikan dalam periode ini |
| `total_take_up` | Total nasabah yang berhasil transaksi |
| `take_up_rate` | Persentase konversi: `(take_up / leads) × 100%` |
| `campaign_count` | Jumlah campaign yang aktif dalam periode ini |

### 2.3 Data Performa Regional

**Apa ini secara bisnis?**
Performa campaign dipecah per wilayah, per minggu. Berguna untuk Campaign Owner melihat wilayah mana yang paling responsif dan memutuskan alokasi leads di campaign berikutnya.

### 2.4 Data Kesamaan Campaign (Similarity Index)

**Apa ini secara bisnis?**
Sistem mencatat kampanye mana yang "mirip" berdasarkan 3 dimensi:
- **Flag Program** (jenis produk yang sama)
- **Jenis Leads** (tujuan leads yang sama)
- **Media Blasting** (channel distribusi yang sama)

Ini memungkinkan fitur "Similar Campaign" — Campaign Owner bisa belajar dari campaign terdahulu yang punya profil serupa.

### 2.5 Audit Log

**Apa ini secara bisnis?**
Rekam jejak siapa yang mengakses dashboard, kapan, dan halaman apa. Ini kewajiban compliance — jika ada pertanyaan "siapa yang melihat data campaign X?", jawabannya ada di sini.

### 2.6 User Session

**Apa ini secara bisnis?**
Manajemen login. Session otomatis kadaluarsa setelah 8 jam untuk keamanan data nasabah, sesuai kebijakan perusahaan.

---

## 3. Sisi Teknis: Struktur Penyimpanan

Sistem menggunakan **4 teknologi penyimpanan** dengan peran berbeda:

```
┌─────────────────────────────────────────────────────────────────┐
│  AMAZON S3 (Data Lake)          ← Penyimpanan utama data        │
│  Query engine: Amazon Athena    ← SQL di atas file S3           │
├─────────────────────────────────────────────────────────────────┤
│  AMAZON DYNAMODB                ← Metadata operasional          │
├─────────────────────────────────────────────────────────────────┤
│  AMAZON COGNITO                 ← Identitas & autentikasi       │
└─────────────────────────────────────────────────────────────────┘
```

### 3.1 S3 Data Lake — Zona-Zona Penyimpanan

```
s3://campaign-datalake/
├── raw/                          ← Data mentah dari sumber (CSV/JSON)
│   ├── leads/                    ← File leads per batch upload
│   └── monitoring_reports/       ← File monitoring report dari Divisi Data
│
├── clean/                        ← Setelah ETL: deduplicated, normalized
│   ├── leads/                    ← Partisi by campaign_id
│   │   └── campaign_id=CAMP001/
│   │       └── data.parquet
│   └── campaigns/                ← Partisi by year/month
│       └── year=2024/month=08/
│           └── data.parquet
│
└── aggregated/                   ← Pre-computed, siap query cepat
    ├── overview/                 ← campaign_overview_agg (harian)
    └── regional/                 ← regional_performance_agg (harian)

s3://campaign-exports/            ← File export sementara (15 menit presigned URL)
```


### 3.2 Tabel Athena (Schema)

#### Tabel `leads` — Data Leads Individual

```sql
-- Partisi by campaign_id untuk efisiensi query per campaign
CREATE EXTERNAL TABLE leads (
    -- Identitas (PII — tidak pernah muncul di API response)
    cif                   STRING,       -- Customer ID (PII)

    -- Atribut Campaign
    nama_program          STRING,       -- Nama campaign
    jenis_leads           STRING,       -- Tujuan leads (Migrasi, Akuisisi, dll)
    media_blasting        STRING,       -- Channel: wa|digisales|telesales|email|push notif|sms
    periode_start         DATE,         -- Tanggal distribusi leads
    flag_program          STRING,       -- PROGRAM QRIS | PROGRAM BIAYA ADMIN

    -- Atribut Geografis
    wilayah               INT,          -- Kode wilayah 1-17
    cabang                INT,          -- Kode cabang 1-324
    outlet                INT,          -- 0=KC, 1-99=outlet

    -- Atribut Nasabah
    segment_crs           STRING,       -- Segmen by jenis pekerjaan
    segment_by_aum        STRING,       -- UPPERMASS|EMERALD|MASS|AFFLUENT|PRIVATE|HIGH AFFLUENT
    segment_wondr         STRING,       -- Segmen permanen by usia/income
    segment_div_owner     STRING,       -- CRS | WEM (Perorangan)
    range_usia            STRING,       -- BABY BOOMER|GEN X|GEN Y|GEN Z|GEN ALPHA
    range_saldo_tab       DOUBLE,       -- Range saldo tabungan
    avg_aum_3_bln         DOUBLE,       -- Rata-rata AUM 3 bulan
    potensi_money         DOUBLE,       -- Estimasi nilai potensi transaksi

    -- Hasil Campaign (join dari monitoring_report, nullable)
    take_up_flag          STRING,       -- YES | NO (default NO)
    take_up_date          DATE,         -- Tanggal take up (NULL jika tidak take up)
    time_to_take_up_days  INT,          -- Selisih hari periode_start → take_up_date
    total_transaction_value DOUBLE      -- Nilai transaksi aktual (NULL jika tidak take up)
)
PARTITIONED BY (campaign_id STRING)
STORED AS PARQUET
LOCATION 's3://campaign-datalake/clean/leads/';
```

#### Tabel `campaign` — Master Campaign

```sql
CREATE EXTERNAL TABLE campaign (
    campaign_id              STRING,    -- ID unik campaign (nama_program + periode)
    campaign_name            STRING,    -- nama_program
    flag_program             STRING,    -- Jenis program
    jenis_leads              STRING,    -- Tujuan leads
    media_blasting           STRING,    -- Channel utama
    wilayah                  INT,       -- Kode wilayah
    start_date               DATE,      -- Tanggal mulai campaign
    end_date                 DATE,      -- Tanggal selesai campaign
    total_leads              BIGINT,    -- Total leads didistribusikan
    total_take_up            BIGINT,    -- Total konversi
    take_up_rate             DOUBLE,    -- Persentase konversi
    total_transaction_value  DOUBLE     -- Total nilai transaksi terealisasi
)
PARTITIONED BY (year INT, month INT)
STORED AS PARQUET
LOCATION 's3://campaign-datalake/clean/campaigns/';
```

#### Tabel `campaign_overview_agg` — Agregat Overview

```sql
-- Pre-computed oleh Glue job setiap hari jam 03:00
CREATE EXTERNAL TABLE campaign_overview_agg (
    period_start            DATE,
    period_end              DATE,
    granularity             STRING,    -- weekly | monthly
    product                 STRING,    -- flag_program
    channel                 STRING,    -- media_blasting
    region                  STRING,    -- wilayah (sebagai string)
    total_leads             BIGINT,
    total_take_up           BIGINT,
    take_up_rate            DOUBLE,
    total_transaction_value DOUBLE,
    campaign_count          INT
)
STORED AS PARQUET
LOCATION 's3://campaign-datalake/aggregated/overview/';
```

#### Tabel `regional_performance_agg` — Agregat Regional

```sql
-- Pre-computed oleh Glue job setiap hari jam 03:30
CREATE EXTERNAL TABLE regional_performance_agg (
    campaign_id             STRING,
    region                  STRING,    -- wilayah
    week_start              DATE,
    leads_count             BIGINT,
    take_up_count           BIGINT,
    take_up_rate            DOUBLE,
    avg_transaction_value   DOUBLE
)
STORED AS PARQUET
LOCATION 's3://campaign-datalake/aggregated/regional/';
```


### 3.3 DynamoDB Tables

#### `CampaignSimilarityIndex`

```
Primary Key:
  PK: campaign_id        (String) — campaign referensi
  SK: similar_campaign_id (String) — campaign yang mirip

Attributes:
  matching_dimensions    List<String>  — ["media_blasting", "flag_program"]
  dimension_count        Number        — 2 (jumlah dimensi yang cocok)
  similarity_score       Number        — 0.0–1.0
  take_up_rate           Number        — take up rate campaign mirip (%)

GSI: DimensionCountIndex
  PK: campaign_id
  SK: dimension_count    — untuk query "cari yang paling mirip"
```

**Contoh isi tabel:**
```json
{
  "campaign_id": "CAMP-QRIS-AUG24",
  "similar_campaign_id": "CAMP-QRIS-MAY24",
  "matching_dimensions": ["flag_program", "media_blasting"],
  "dimension_count": 2,
  "similarity_score": 0.67,
  "take_up_rate": 12.5
}
```

#### `AuditLog`

```
Primary Key:
  PK: user_id            (String) — ID pengguna Cognito
  SK: timestamp          (String) — ISO 8601, e.g. "2024-08-15T09:23:11Z"

Attributes:
  page_accessed          String  — "campaign_overview" | "comparison" | dll
  action                 String  — "view" | "export" | "filter_applied"
  request_params         Map     — filter yang aktif saat itu
  ip_address             String
  expiry_timestamp       Number  — TTL: otomatis dihapus setelah retensi berakhir
```

#### `UserSessions`

```
Primary Key:
  PK: session_id         (String) — UUID

Attributes:
  user_id                String  — ID pengguna Cognito
  role                   String  — "divisi_bisnis" | "divisi_data"
  login_timestamp        String  — ISO 8601
  expiry_timestamp       Number  — epoch + 28800 detik (8 jam)
  is_active              Boolean
```

---

## 4. Entity Relationship (Logical)

Karena tidak ada foreign key fisik, relasi ini bersifat **logical** — join dilakukan oleh Glue ETL, bukan di runtime.

```
COGNITO USER
    │
    │ 1 user memiliki banyak session
    ▼
UserSessions ──────────────── AuditLog
(session_id PK)               (user_id, timestamp PK)


DATA LAKE (S3 + Athena)

leads ──────────────────────── campaign
  │  nama_program = campaign_name   │
  │  [join key — bukan FK fisik]    │
  │                                 │
  │ Glue ETL joins & aggregates     │
  ▼                                 ▼
campaign_overview_agg       regional_performance_agg
(by period, product,        (by campaign_id, region,
 channel, region)            week_start)


campaign ──────────────────── CampaignSimilarityIndex
  │  campaign_id                    │
  │  [computed by Glue weekly]      │
  └─────────────────────────────────┘
```

**Kardinalitas:**

| Hubungan | Tipe |
|----------|------|
| 1 Campaign → banyak Leads | 1:N |
| 1 Campaign → banyak CampaignSimilarityIndex entries | 1:N |
| 1 Campaign → banyak regional_performance_agg rows | 1:N |
| 1 User → banyak AuditLog entries | 1:N |
| 1 User → banyak UserSessions (tapi hanya 1 aktif) | 1:N |


---

## 5. Alur Data — ETL Pipeline

```
SUMBER DATA                    GLUE ETL (PySpark)              STORAGE

Divisi Data upload             ┌─────────────────┐
file leads CSV/JSON   ────────►│ raw_to_clean.py │─────────► S3: clean/leads/
                               │ (daily 02:00)   │           (Parquet, by campaign_id)
Divisi Data upload             │ - Deduplicate   │
monitoring report     ────────►│ - Normalize     │─────────► S3: clean/campaigns/
                               │ - Join leads +  │           (Parquet, by year/month)
                               │   monitoring    │
                               └─────────────────┘
                                        │
                                        ▼
                               ┌─────────────────┐
                               │aggregate_metrics│─────────► S3: aggregated/overview/
                               │ (daily 03:00)   │           campaign_overview_agg
                               │ - Sum by period │
                               │ - weekly/monthly│
                               └─────────────────┘
                                        │
                                        ▼
                               ┌─────────────────┐
                               │regional_rollup  │─────────► S3: aggregated/regional/
                               │ (daily 03:30)   │           regional_performance_agg
                               │ - Sum by region │
                               │ - Weekly trend  │
                               └─────────────────┘
                                        │
                                        ▼
                               ┌─────────────────┐
                               │similarity_index │─────────► DynamoDB:
                               │ (weekly Sun     │           CampaignSimilarityIndex
                               │  04:00)         │
                               │ - Match dims    │
                               │ - Score pairs   │
                               └─────────────────┘
```

---

## 6. Simulasi: Platform Berjalan

### Skenario A: Campaign Owner Membuka Dashboard Overview

```
Waktu: Senin, 9 Agustus 2024, pukul 09:15

1. BROWSER
   → User (Divisi Bisnis) buka dashboard
   → React app load, cek JWT token di localStorage

2. COGNITO
   → Validasi token: masih valid (login 2 jam lalu, belum 8 jam)
   → Claims: role = "divisi_bisnis"

3. API GATEWAY → Lambda: campaign_overview
   Request: GET /api/campaigns/overview
            ?start_date=2024-05-08
            &end_date=2024-08-08
            &media_blasting=wa,digisales

4. LAMBDA (campaign_overview/handler.py)
   → Parse query params → CampaignOverviewRequest(
       start_date="2024-05-08",
       end_date="2024-08-08",
       media_blasting=["wa", "digisales"]
     )
   → AthenaClient.build_campaign_overview_query(request)
   
   SQL yang dihasilkan:
   ┌─────────────────────────────────────────────────────────────┐
   │ SELECT period_start, period_end, granularity,               │
   │        total_leads, total_take_up, take_up_rate, ...        │
   │ FROM campaign_overview_agg                                  │
   │ WHERE period_start >= '2024-05-08'                          │
   │   AND period_end <= '2024-08-08'                            │
   │   AND channel IN ('wa', 'digisales')                        │
   │ ORDER BY period_start ASC                                   │
   └─────────────────────────────────────────────────────────────┘
   
   → execute_query() → Athena starts query execution
   → Poll setiap 1 detik, selesai dalam ~3 detik
   → Hasil: 13 baris (13 minggu karena 92 hari → monthly? 
     No: 92 hari > 90 → granularity = monthly → 3 baris)

5. LAMBDA — Proses Response
   → Hitung total: sum(total_leads), sum(total_take_up)
   → Hitung overall take_up_rate:
     calculate_take_up_rate(total_leads=45230, total_take_up=3817)
     → (3817 / 45230) × 100 = 8.44%
   → Build trend list: 3 TrendDataPoint (Juni, Juli, Agustus)
   → strip_pii(response) — tidak ada PII di response ini
   → Return CampaignOverviewResponse

6. AUDIT LOG
   → DynamoDB write: {
       user_id: "usr_robin_123",
       timestamp: "2024-08-09T09:15:23Z",
       page_accessed: "campaign_overview",
       action: "view",
       request_params: {media_blasting: ["wa", "digisales"]}
     }

7. BROWSER
   → Dashboard render: Total Leads: 45.230 | Take Up: 3.817 | Rate: 8.44%
   → Line chart: 3 titik tren bulanan
   ✅ Selesai dalam < 5 detik
```

### Skenario B: Export Data ke Excel

```
Waktu: Senin, 9 Agustus 2024, pukul 10:30

1. USER klik tombol "Export" di halaman Regional Performance
   → Pilih format: Excel

2. API GATEWAY → Lambda: export_service
   Request: POST /api/export
   Body: {
     page: "regional_performance",
     format: "excel",
     filters: [{field: "product", values: ["PROGRAM QRIS"]}],
     time_range_start: "2024-05-08",
     time_range_end: "2024-08-08"
   }

3. LAMBDA (export_service/handler.py)
   → Parse ExportRequest
   → 30-second timer mulai
   → Query data regional dari Athena
   → Generate Excel file dengan openpyxl:
     - Sheet 1: Data regional (wilayah, leads, take_up, rate)
     - Metadata header: Filter: PROGRAM QRIS | Periode: 2024-05-08 s/d 2024-08-08
                        Sumber: Regional Performance
   → Upload ke s3://campaign-exports/export_abc123.xlsx
   → Generate presigned URL (valid 15 menit)

4. RESPONSE
   → ExportResponse(
       status="completed",
       download_url="https://s3.amazonaws.com/campaign-exports/export_abc123.xlsx?..."
     )

5. BROWSER
   → Notifikasi in-app: "File siap diunduh"
   → Auto-download dimulai
   ✅ User mendapat file Excel dengan data + metadata
```

### Skenario C: Malam Hari — ETL Berjalan Otomatis

```
Waktu: Selasa, 3 Agustus 2024, pukul 02:00–04:00

02:00 — Glue: raw_to_clean.py
  → Baca file leads baru dari s3://campaign-datalake/raw/leads/
  → Deduplicate by cif + nama_program + periode_start
  → Normalize: standarisasi format tanggal, uppercase segment values
  → Join dengan monitoring_report (isi take_up_flag, take_up_date)
  → Hitung time_to_take_up_days = (take_up_date - periode_start).days
  → Tulis ke s3://campaign-datalake/clean/leads/ partisi by campaign_id
  → Update tabel campaign master

03:00 — Glue: aggregate_metrics.py
  → Baca clean/leads/ + clean/campaigns/
  → Aggregate by (period, product, channel, region):
    - Pilih granularity: weekly/monthly berdasarkan range
    - Hitung SUM(leads), SUM(take_up), take_up_rate, campaign_count
  → Overwrite s3://campaign-datalake/aggregated/overview/

03:30 — Glue: regional_rollup.py
  → Aggregate by (campaign_id, wilayah, week_start):
    - SUM leads_count, take_up_count
    - AVG avg_transaction_value
  → Overwrite s3://campaign-datalake/aggregated/regional/

04:00 (Minggu) — Glue: similarity_index.py
  → Untuk setiap pasang campaign, hitung berapa dimensi yang sama:
    - Sama flag_program? +1
    - Sama jenis_leads? +1
    - Sama media_blasting? +1
  → Hitung similarity_score = dimension_count / 3
  → Tulis ke DynamoDB CampaignSimilarityIndex
  
  Contoh output:
  CAMP-QRIS-AUG24 ↔ CAMP-QRIS-JUL24: dimension_count=2, score=0.67
  CAMP-QRIS-AUG24 ↔ CAMP-BIAYA-JUN24: dimension_count=1, score=0.33

→ Keesokan paginya, dashboard sudah menampilkan data terbaru
```


---

## 7. Catatan Penting & Keterbatasan

### 7.1 Tidak Ada `campaign_id` Surrogate Key di Leads

Data leads saat ini diidentifikasi oleh `nama_program` (nama campaign), bukan oleh surrogate key unik. Ini berarti:
- Jika nama program yang sama dipakai di dua periode berbeda, mereka akan dianggap **satu campaign**
- Saat implementasi Glue ETL, perlu dibuat `campaign_id` sintetis: misalnya `hash(nama_program + periode_start)`

### 7.2 `take_up_flag` adalah String, Bukan Boolean

Di Python model, `take_up_flag = "YES"` atau `"NO"` — bukan `True`/`False`. Di query Athena, kondisinya adalah `take_up_flag = 'YES'`, bukan `take_up_flag = true`.

### 7.3 PII: Dua Sumber Kebenaran

Ada inkonsistensi antara dua module:
- `pii_filter.py` melindungi: `nama_lengkap`, `nomor_rekening`, `nomor_identitas`, `alamat_lengkap`
- `models.py` hanya mendefinisikan `PII_FIELDS = {"cif"}` sebagai PII

**Alasannya**: Data yang masuk ke sistem ini sudah di-anonymize di level upstream (hanya `cif` yang ada, bukan nama lengkap). `pii_filter.py` dirancang defensif untuk jika ada data upstream yang belum bersih masuk ke sistem.

### 7.4 Tidak Ada Real-time Data

Data di dashboard selalu **D-1** (kemarin). ETL berjalan malam hari. Tidak ada streaming/real-time ingestion. Ini acceptable karena campaign analysis adalah backward-looking activity.

### 7.5 Presigned URL Export Expire dalam 15 Menit

File export di S3 hanya bisa didownload dalam 15 menit setelah dibuat. Jika user tidak langsung download, mereka perlu generate ulang.

---

*Dokumen ini dibuat berdasarkan implementasi aktual di `backend/shared/models.py`, `backend/shared/athena_client.py`, dan spec di `.kiro/specs/campaign-insight-generator/`. Terakhir diperbarui: Juli 2026.*
