# Task 8.3 — CDK Data Stack: Athena Workgroup, Glue Jobs & Schedules

## Ringkasan Singkat

Task ini melengkapi `DataStack` (`backend/infrastructure/stacks/data_stack.py`) dengan
komponen analitik dan ETL: satu **Athena Workgroup** untuk mengisolasi query kampanye,
empat **Glue ETL Jobs** yang menjalankan pipeline transformasi data, dan empat
**Glue Triggers** berjadwal yang mengotomasi eksekusi pipeline setiap hari dan setiap minggu.

---

## Penjelasan Awam (Non-Technical)

Bayangkan sistem ini seperti pabrik pengolahan data:

- **Data mentah** (laporan leads, monitoring kampanye) masuk setiap hari ke gudang penyimpanan (S3 Raw Zone).
- **Mesin pengolah** (Glue Jobs) berjalan otomatis tengah malam untuk membersihkan, merangkum, dan menganalisis data tersebut.
- **Jam kerja mesin** diatur oleh **Trigger** — seperti alarm yang membunyikan bel setiap hari pukul 02:00, 03:00, 03:30, dan setiap Minggu pukul 04:00.
- **Athena Workgroup** adalah "ruang kerja query" yang disisihkan khusus untuk Campaign Insight Generator, agar tidak bercampur dengan query sistem lain dan mudah dipantau biayanya.

Manfaat bagi tim bisnis:
- Dashboard selalu menampilkan data yang sudah diproses — tidak perlu menunggu tim IT.
- Indeks "campaign serupa" diperbarui setiap minggu sehingga rekomendasi tetap relevan.
- Semua biaya query tercatat per workgroup, memudahkan kontrol anggaran.

---

## Penjelasan Teknis

### File yang Dimodifikasi

- `backend/infrastructure/stacks/data_stack.py` — ditambahkan:
  - `aws_athena as athena`, `aws_glue as glue`, `aws_iam as iam` imports
  - `athena.CfnWorkGroup` construct
  - `iam.Role` untuk Glue (`GlueJobRole`)
  - 4× `glue.CfnJob` constructs
  - 4× `glue.CfnTrigger` constructs

### Library / Framework

- **AWS CDK (Python)** — Infrastructure-as-Code
- `aws_cdk.aws_athena` — `CfnWorkGroup`, `CfnWorkGroup.WorkGroupConfigurationProperty`, `ResultConfigurationProperty`
- `aws_cdk.aws_glue` — `CfnJob`, `CfnJob.JobCommandProperty`, `CfnTrigger`, `CfnTrigger.ActionProperty`
- `aws_cdk.aws_iam` — `Role`, `ServicePrincipal`, `ManagedPolicy`

### Pola Arsitektur

- **Helper function `_create_glue_job`** — menghindari duplikasi; semua 4 job berbagi struktur yang sama (GlueETL, Python 3, Glue 4.0, max_retries=1, timeout=60 menit).
- **Naming convention**: semua resource mengikuti pola `campaign-<resource>-{env_name}` untuk mudah diidentifikasi per environment.
- **`start_on_creation=True`** pada semua trigger: trigger langsung aktif saat deploy sehingga tidak perlu aktivasi manual.

### Keputusan Desain

| Keputusan | Alasan |
|-----------|--------|
| `enforce_work_group_configuration=True` pada Athena | Memastikan semua query diarahkan ke S3 output path yang benar; mencegah query "liar" tanpa output path. |
| `publish_cloud_watch_metrics_enabled=True` | Memungkinkan monitoring query count, data scanned, dan biaya per workgroup di CloudWatch. |
| `glue_version="4.0"` | Mendukung PySpark terbaru dan Python 3; kompatibel dengan job script yang sudah ditulis di task 7.x. |
| `max_retries=1` | Satu kali retry cukup untuk kegagalan sementara (throttle, transient S3 error); mencegah loop berulang yang memboroskan biaya. |
| `timeout=60` menit | Pipeline transformasi harian diperkirakan selesai ≤ 30 menit; 60 menit batas aman. |
| IAM `AWSGlueServiceRole` managed policy | Policy AWS standar yang sudah mencakup CloudWatch Logs, S3, dan Glue Data Catalog access. |
| `data_lake_bucket.grant_read_write(glue_role)` | Memberikan akses Glue hanya ke bucket yang relevan (least-privilege). |

---

## Struktur Kode

### `DataStack.__init__` — resources baru (task 8.3)

```python
# Athena Workgroup
athena_workgroup = athena.CfnWorkGroup(self, "AthenaWorkgroup", ...)
self.athena_workgroup_name: str = athena_workgroup.name

# IAM Role
self.glue_role = iam.Role(self, "GlueJobRole", ...)
self.data_lake_bucket.grant_read_write(self.glue_role)

# Helper (closure)
def _create_glue_job(job_id, script_path, description, default_args=None) -> glue.CfnJob

# 4 Glue Jobs
raw_to_clean_job      = _create_glue_job("RawToCleanJob", "raw_to_clean.py", ...)
aggregate_metrics_job = _create_glue_job("AggregateMetricsJob", "aggregate_metrics.py", ...)
similarity_index_job  = _create_glue_job("SimilarityIndexJob", "similarity_index.py", ...)
regional_rollup_job   = _create_glue_job("RegionalRollupJob", "regional_rollup.py", ...)

# 4 Glue Triggers
glue.CfnTrigger(self, "RawToCleanTrigger",       schedule="cron(0 2 * * ? *)")   # Daily 02:00 UTC
glue.CfnTrigger(self, "AggregateMetricsTrigger",  schedule="cron(0 3 * * ? *)")   # Daily 03:00 UTC
glue.CfnTrigger(self, "RegionalRollupTrigger",    schedule="cron(30 3 * * ? *)")  # Daily 03:30 UTC
glue.CfnTrigger(self, "SimilarityIndexTrigger",   schedule="cron(0 4 ? * SUN *)") # Weekly Sun 04:00 UTC
```

### Atribut Publik yang Ditambahkan

| Atribut | Tipe | Deskripsi |
|---------|------|-----------|
| `self.athena_workgroup_name` | `str` | Nama workgroup Athena; dipakai oleh ApiStack/Lambda |
| `self.glue_role` | `iam.Role` | IAM role Glue; bisa di-grant akses resource tambahan dari stack lain |

---

## Simulasi / Skenario

### Skenario 1 — Pipeline Harian (Happy Path)

```
02:00 UTC — RawToCleanTrigger menyala
    → Glue job "campaign-rawtoclean-dev" berjalan
    → Membaca s3://campaign-datalake-dev/raw/
    → Menulis Parquet ke s3://campaign-datalake-dev/clean/

03:00 UTC — AggregateMetricsTrigger menyala
    → Glue job "campaign-aggregatemetrics-dev" berjalan
    → Membaca s3://campaign-datalake-dev/clean/
    → Menulis agregat ke s3://campaign-datalake-dev/aggregated/overview/

03:30 UTC — RegionalRollupTrigger menyala
    → Glue job "campaign-regionalrollup-dev" berjalan
    → Membaca s3://campaign-datalake-dev/clean/
    → Menulis agregat ke s3://campaign-datalake-dev/aggregated/regional/
```

### Skenario 2 — Pipeline Mingguan (Similarity Index)

```
Minggu 04:00 UTC — SimilarityIndexTrigger menyala
    → Glue job "campaign-similarityindex-dev" berjalan
    → Membaca clean zone
    → Menghitung skor kemiripan antar campaign
    → Menulis ke DynamoDB tabel CampaignSimilarityIndex
```

### Skenario 3 — Athena Query dari Lambda

```python
# Lambda similar_campaign/handler.py menggunakan workgroup ini:
athena_client = AthenaClient(
    database="campaign_db",
    workgroup="campaign-insight-dev",   # dari self.athena_workgroup_name
    output_location="s3://campaign-datalake-dev/athena-results/",
)
results = athena_client.query("SELECT * FROM campaign WHERE ...")
```

### Skenario 4 — Job Gagal dan Retry

```
02:00 UTC — RawToCleanJob mulai
02:05 UTC — S3 throttle error → job gagal
    → Glue otomatis retry (max_retries=1)
02:07 UTC — Retry berhasil
    → Log "SUCCEEDED" di CloudWatch
```

---

## Keterkaitan dengan Komponen Lain

- **Bergantung pada:**
  - `DataStack` task 8.1 — S3 buckets sudah ada sebelum Glue/Athena dikonfigurasi
  - Glue scripts di `backend/glue_jobs/` (task 7.x) — harus diupload ke `s3://.../glue-scripts/` sebelum trigger aktif

- **Digunakan oleh:**
  - `ApiStack` (task 8.2) — Lambda functions membutuhkan `athena_workgroup_name` untuk mengarahkan query
  - Lambda handlers (`similar_campaign`, `campaign_overview`, dll.) — melalui AthenaClient

- **Pengaruh ke:**
  - Jika `data_lake_bucket` diganti nama → semua `script_location`, `TempDir`, dan Athena `output_location` harus diperbarui (sudah di-derive otomatis via `self.data_lake_bucket.bucket_name`)

---

## Requirements yang Dipenuhi

| Requirement | Penjelasan |
|-------------|------------|
| **6.1** | Similar Campaign feature membutuhkan `SimilarityIndexJob` yang berjalan mingguan untuk membangun indeks kemiripan campaign di DynamoDB. |
| **7.4** | Audit log completeness didukung oleh infrastruktur DynamoDB yang sudah ada (task 8.1) dan Glue pipeline yang memastikan data tersedia untuk query Athena. |

---

## Catatan Penting

1. **Script Glue harus di-upload manual / via CI/CD**: CDK mendefinisikan job dengan path script, tetapi tidak mengupload file `.py` ke S3. Tim perlu memastikan `backend/glue_jobs/*.py` tersalin ke `s3://campaign-datalake-{env}/glue-scripts/` sebelum trigger pertama berjalan.

2. **Nama job di-derive dari job_id**: `"RawToCleanJob"` → `"campaign-rawtoclean-{env}"` (suffix `"Job"` dihapus, sisanya di-lowercase). Ini konsisten tapi perlu diperhatikan saat debugging di AWS Console.

3. **`start_on_creation=True`**: Trigger langsung aktif saat pertama kali di-deploy. Jika deployment dilakukan siang hari, trigger berikutnya akan berjalan sesuai jadwal cron; tidak ada eksekusi langsung saat deploy.

4. **Athena result location**: Query results disimpan di `s3://campaign-datalake-{env}/athena-results/`. Tidak ada lifecycle rule untuk path ini — jika volume besar, pertimbangkan menambahkan lifecycle rule di task berikutnya.

5. **CDK import warnings**: `aws_glue` dan `aws_athena` menggunakan L1 constructs (Cfn*). Pylance mungkin menampilkan warning tentang deprecated properties pada versi CDK tertentu — ini expected dan tidak memblokir synth.
