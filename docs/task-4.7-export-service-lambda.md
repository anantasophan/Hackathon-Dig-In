# Task 4.7 — Export Service Lambda

## Ringkasan Singkat

Export Service adalah Lambda handler yang menangani endpoint `POST /api/campaigns/export`. Komponen ini bertanggung jawab mengubah data kampanye beserta filter yang sedang aktif menjadi file siap unduh dalam format **PDF**, **Excel (.xlsx)**, atau **CSV**. File yang dihasilkan diunggah ke Amazon S3, lalu sistem menghasilkan *presigned URL* yang valid selama 15 menit agar pengguna dapat mengunduhnya langsung dari browser tanpa memerlukan akses permanen ke bucket S3. Komponen ini digunakan oleh semua role pengguna (`divisi_bisnis` dan `divisi_data`) yang ingin menyimpan snapshot laporan dari dashboard.

---

## Penjelasan Awam (Non-Technical)

Bayangkan Anda sedang melihat laporan performa kampanye di sebuah dashboard seperti Google Analytics. Anda sudah menyaring data hanya untuk **PROGRAM QRIS**, periode **Januari–Maret 2024**, dan wilayah **Jakarta**. Sekarang Anda ingin mencetak atau menyimpan laporan ini untuk dibagikan ke atasan.

Export Service adalah tombol **"Download Laporan"** di dashboard tersebut — tapi versi online yang jauh lebih canggih:

- Anda tinggal klik tombol dan pilih format: PDF untuk dipresentasikan, Excel untuk dianalisis lebih lanjut, atau CSV untuk diolah ulang di sistem lain.
- Sistem akan menyiapkan file tersebut di belakang layar (di server cloud), lalu memberikan Anda **link khusus sementara** untuk mengunduhnya — mirip seperti link berbagi file di Google Drive yang punya batas waktu.
- Link tersebut hanya berlaku **15 menit** — setelah itu kedaluwarsa demi keamanan. Jika terlambat, Anda bisa meminta link baru dengan klik Export lagi.
- Kalau prosesnya terlalu lama (lebih dari 30 detik), sistem akan berhenti sendiri dan memberitahu Anda, daripada menggantung tanpa kepastian.

Manfaat bagi pengguna bisnis:
- Laporan bisa langsung dibagikan ke stakeholder dalam format yang familier (Excel/PDF).
- Filter yang sudah Anda terapkan di dashboard ikut tersimpan dalam file, jadi penerima laporan tahu konteks datanya.
- Proses aman — file tidak bisa diakses oleh sembarang orang karena link-nya bersifat sementara dan unik.

---

## Penjelasan Teknis

### File yang Diimplementasi

- **`backend/lambdas/export_service/handler.py`** — Lambda handler utama
- Mengimpor model dari **`backend/shared/models.py`**: `ExportRequest`, `ExportResponse`, `ActiveFilter`

### Library/Framework yang Digunakan

| Library | Versi | Kegunaan |
|---------|-------|----------|
| `boto3` | AWS SDK | Upload S3, generate presigned URL |
| `csv` (stdlib) | — | Generasi file CSV |
| `io` (stdlib) | — | Buffer in-memory untuk file |
| `openpyxl` | opsional | Generasi file Excel (.xlsx) |
| `reportlab` | opsional | Generasi file PDF |
| `uuid` (stdlib) | — | Nama file unik di S3 |
| `time` (stdlib) | — | Timeout enforcement 30 detik |

### Pola Arsitektur yang Diterapkan

1. **API Gateway Lambda Proxy** — event masuk dari API Gateway dalam format proxy standar, response dikembalikan dalam format yang sama (`statusCode`, `headers`, `body`).
2. **Dispatch Pattern** — fungsi `_generate_file()` mendelegasikan ke generator spesifik (`_generate_csv`, `_generate_excel`, `_generate_pdf`) berdasarkan field `format` di request.
3. **Best-effort S3 Cleanup** — jika terjadi timeout *setelah* upload ke S3, kode mencoba menghapus objek tersebut agar tidak meninggalkan file "yatim" di bucket.
4. **Presigned URL Pattern** — file tidak diekspos langsung; akses hanya melalui URL sementara yang dibuat oleh `s3.generate_presigned_url()`.

### Keputusan Desain Penting

- **MVP Scope**: File yang dihasilkan hanya berisi metadata filter dan placeholder row, bukan data Athena aktual. Fetch data Athena sengaja ditunda ke iterasi post-MVP agar kompleksitas awal terkendali (ada komentar `NOTE (MVP)` di header file).
- **`openpyxl` dan `reportlab` sebagai optional dependency** — di-import di dalam fungsi generator agar Lambda tidak gagal saat cold start jika library belum terpasang (ImportError dikembalikan sebagai HTTP 500).
- **Timeout monitoring ganda** — timeout dicek *dua kali*: setelah generate file dan setelah upload S3, untuk menangani kasus di mana upload berhasil tetapi terlalu lambat untuk menghasilkan presigned URL.
- **Nama file S3 menggunakan UUID** — mencegah tabrakan nama dan mempersulit enumeration oleh pihak yang tidak berwenang.

### Environment Variables

| Variabel | Default | Keterangan |
|----------|---------|------------|
| `EXPORT_BUCKET` | `"campaign-exports"` | Nama S3 bucket tujuan upload |

### Edge Cases yang Ditangani

- Body JSON tidak valid → HTTP 400
- Field wajib tidak ada di body → HTTP 400
- Format tidak dikenal → HTTP 400 dengan daftar format valid
- Generasi file gagal (exception umum) → HTTP 500
- Import library opsional gagal → HTTP 500 dengan pesan informatif
- Upload S3 gagal (`ClientError`) → HTTP 500
- Timeout >30 detik → HTTP 408, S3 object dihapus (best-effort)
- Presigned URL gagal dibuat → HTTP 500, S3 object dihapus

---

## Struktur Kode

```
backend/lambdas/export_service/handler.py
│
├── Konstanta
│   ├── _TIMEOUT_SECONDS = 30.0
│   ├── _PRESIGNED_URL_TTL_SECONDS = 900  (15 menit)
│   ├── _DEFAULT_EXPORT_BUCKET = "campaign-exports"
│   ├── _VALID_FORMATS = {"pdf", "excel", "csv"}
│   ├── _FORMAT_EXT — mapping format ke ekstensi file
│   └── _FORMAT_CONTENT_TYPE — mapping format ke MIME type
│
├── Response Helpers
│   ├── _ok(body) → dict          # 200 response
│   └── _error(status_code, msg)  # 400/408/500 response
│
├── File Generators
│   ├── _filter_summary(filters) → str
│   │   └── Mengubah list ActiveFilter menjadi string ringkasan,
│   │       e.g. "flag_program=PROGRAM QRIS; wilayah=1,3"
│   │
│   ├── _generate_csv(request) → bytes
│   │   ├── Menulis metadata sebagai comment (#) di baris pertama
│   │   ├── Header row: nama_program, flag_program, dll.
│   │   └── Placeholder row (MVP)
│   │
│   ├── _generate_excel(request) → bytes
│   │   ├── Sheet "Metadata": filter aktif, time range, source page
│   │   └── Sheet "Data": header kolom + placeholder row
│   │
│   ├── _generate_pdf(request) → bytes
│   │   ├── Title: "Campaign Insight Export"
│   │   ├── Tabel metadata dengan style (background abu-abu)
│   │   └── Tabel data dengan header row warna abu gelap
│   │
│   └── _generate_file(request) → bytes
│       └── Dispatcher ke CSV / Excel / PDF berdasarkan request.format
│
└── Lambda Entry Point
    └── lambda_handler(event, context) → dict
        ├── 1. Parse & validasi JSON body → ExportRequest
        ├── 2. Validasi format
        ├── 3. Start timer timeout
        ├── 4. Generate file bytes
        ├── 5. Cek timeout post-generate
        ├── 6. Upload ke S3
        ├── 7. Cek timeout post-upload
        ├── 8. Generate presigned URL
        └── 9. Return 200 dengan download_url
```

### Signature Fungsi Utama

```python
def lambda_handler(event: dict, context: Any) -> dict[str, Any]:
    """Entry point. Menerima POST body, generate file, return presigned URL."""

def _generate_csv(request: ExportRequest) -> bytes:
    """Generate CSV dengan metadata comment block di header."""

def _generate_excel(request: ExportRequest) -> bytes:
    """Generate Excel .xlsx dengan dua sheet: Metadata dan Data."""

def _generate_pdf(request: ExportRequest) -> bytes:
    """Generate PDF dengan reportlab; tabel metadata + tabel data."""

def _filter_summary(filters: list[ActiveFilter]) -> str:
    """Konversi filter aktif ke string ringkasan (untuk header file)."""

def _generate_file(request: ExportRequest) -> bytes:
    """Dispatcher: pilih generator berdasarkan request.format."""
```

---

## Simulasi / Skenario

### Skenario 1 — Export CSV Berhasil (Happy Path)

**Konteks**: Pengguna sedang di halaman *Regional Performance*, telah memfilter `PROGRAM QRIS`, periode `2024-01-01` s/d `2024-03-31`, dan klik tombol "Export CSV".

**Request (POST /api/campaigns/export)**:
```json
{
  "page": "regional_performance",
  "format": "csv",
  "filters": [
    {"field": "flag_program", "values": ["PROGRAM QRIS"]},
    {"field": "wilayah",      "values": [1, 3, 5]}
  ],
  "time_range_start": "2024-01-01",
  "time_range_end":   "2024-03-31"
}
```

**Proses di Lambda**:
1. Body di-parse → `ExportRequest` dibuat
2. Timer dimulai (`start_time = time.monotonic()`)
3. `_generate_csv()` dipanggil:
   - Metadata comment: `# Source: regional_performance, Period: 2024-01-01 to 2024-03-31, Filters: flag_program=PROGRAM QRIS; wilayah=1,3,5`
   - Header row ditulis
   - Placeholder row ditulis
4. Elapsed ≈ 0.1 detik → tidak timeout
5. File diupload ke S3 dengan key `f3a2b1c0-xxxx.csv`
6. Presigned URL dibuat, valid 15 menit

**Response (HTTP 200)**:
```json
{
  "status": "completed",
  "download_url": "https://campaign-exports.s3.amazonaws.com/f3a2b1c0-xxxx.csv?X-Amz-Expires=900&...",
  "error_message": null
}
```

**Isi File CSV yang Diunduh**:
```
# Source: regional_performance, Period: 2024-01-01 to 2024-03-31, Filters: flag_program=PROGRAM QRIS; wilayah=1,3,5
nama_program,flag_program,media_blasting,jenis_leads,wilayah,total_leads,total_take_up,take_up_rate
N/A (MVP placeholder),N/A,N/A,N/A,N/A,0,0,0.00%
```

---

### Skenario 2 — Skenario Timeout (>30 Detik)

**Konteks**: Pengguna mengekspor file Excel besar yang entah kenapa lambat diproses (misalnya library `openpyxl` membutuhkan waktu lebih lama dari biasanya, atau jaringan S3 sedang lambat).

**Proses di Lambda**:
1. File Excel berhasil di-generate dalam 5 detik
2. Upload ke S3 memakan waktu 26 detik (koneksi lambat)
3. Timeout dicek setelah upload: elapsed = 31 detik → **melebihi 30 detik**
4. Lambda memanggil `s3.delete_object(Bucket=bucket, Key=s3_key)` — **S3 object dihapus** (best-effort)
5. Response 408 dikembalikan

**Response (HTTP 408)**:
```json
{
  "status": "timeout",
  "download_url": null,
  "error_message": "Export timed out after 30 seconds. Please retry or reduce the scope of the export."
}
```

**Catatan**: S3 object yang sudah terupload dihapus agar tidak meninggalkan file "yatim" yang tidak bisa diakses pengguna.

---

### Skenario 3 — Format Tidak Valid

**Request**:
```json
{
  "page": "campaign_overview",
  "format": "powerpoint",
  "filters": [],
  "time_range_start": "2024-01-01",
  "time_range_end": "2024-03-31"
}
```

**Response (HTTP 400)**:
```json
{
  "message": "Unsupported export format 'powerpoint'. Must be one of: csv, excel, pdf."
}
```

---

### Skenario 4 — Metadata CSV Header Format

Ketika filter aktif berisi multiple values, format metadata di header CSV:

```
# Source: campaign_overview, Period: 2024-01-01 to 2024-06-30, Filters: flag_program=PROGRAM QRIS,PROGRAM BIAYA ADMIN; media_blasting=wa,telesales
```

Format: `field=value1,value2; field2=value3` — menggunakan koma sebagai separator nilai, titik koma sebagai separator antar field.

---

## Keterkaitan dengan Komponen Lain

### Bergantung pada:
- **`shared/models.py`** — `ExportRequest`, `ExportResponse`, `ActiveFilter` digunakan untuk parsing dan response
- **Amazon S3** — bucket `campaign-exports` (dikonfigurasi via env var `EXPORT_BUCKET`)
- **`openpyxl`** (opsional) — diperlukan untuk format Excel
- **`reportlab`** (opsional) — diperlukan untuk format PDF

### Digunakan oleh:
- **API Gateway** — menerima `POST /api/campaigns/export` dan meneruskan ke Lambda ini
- **Frontend** — komponen Export (Task 11.7) memanggil endpoint ini dan membuka `download_url` di tab baru

### Pengaruh ke komponen lain jika komponen ini berubah:
- Jika format `ExportResponse` berubah (misal: menambah field baru), frontend perlu update cara membaca response
- Jika `_FORMAT_EXT` atau `_FORMAT_CONTENT_TYPE` berubah, nama file yang diunduh akan berubah
- Jika `_PRESIGNED_URL_TTL_SECONDS` berubah, durasi validitas link berubah — perlu diinformasikan ke pengguna di UI
- Jika `_TIMEOUT_SECONDS` berubah, Lambda timeout di CDK stack juga harus disesuaikan

---

## Requirements yang Dipenuhi

| Req ID | Deskripsi |
|--------|-----------|
| **8.1** | Sistem mendukung ekspor dalam format PDF, Excel, dan CSV |
| **8.2** | File ekspor mengandung metadata: halaman sumber, time range, dan filter aktif |
| **8.3** | File diunggah ke S3 dan dikembalikan sebagai presigned URL valid 15 menit |
| **8.4** | Proses ekspor yang melebihi 30 detik dikembalikan sebagai HTTP 408 |
| **8.5** | Kegagalan generasi file atau upload S3 dikembalikan sebagai HTTP 500 |

---

## Catatan Penting

### Limitasi yang Diketahui (MVP)

1. **Data placeholder, bukan data aktual**: File yang diekspor hanya berisi metadata filter dan satu baris placeholder `N/A (MVP placeholder)`. Fetch data dari Athena belum diimplementasikan — ini disebut jelas di komentar header file dengan label `NOTE (MVP)`.

2. **Dependency opsional tidak di-bundle secara default**: `openpyxl` dan `reportlab` tidak ada di `requirements.txt` standar. Jika Lambda Layer tidak menyertakannya, format Excel dan PDF akan menghasilkan HTTP 500.

### Asumsi yang Dibuat

- API Gateway sudah dikonfigurasi dengan **Cognito authorizer** sehingga autentikasi ditangani sebelum Lambda ini dipanggil (tidak ada `require_auth()` di handler ini).
- S3 bucket `campaign-exports` sudah ada dan Lambda memiliki IAM permission `s3:PutObject`, `s3:DeleteObject`, dan `s3:GetObject` terhadap bucket tersebut.
- Request body dikirim sebagai JSON string (bukan binary), sesuai standar API Gateway Lambda proxy.

### Todo untuk Pengembangan Berikutnya

- [ ] Implementasi fetch data aktual dari Athena via `AthenaClient` sebelum generate file
- [ ] Tambah `@audit_log(page=request.page, action="export")` agar setiap aksi export tercatat di audit log
- [ ] Tambah `@require_auth` wrapper atau panggil `require_auth()` eksplisit jika autentikasi per-Lambda diperlukan
- [ ] Pertimbangkan async export untuk file besar: return `job_id` → polling endpoint `/api/export/status/{job_id}`
- [ ] Tambah validasi format tanggal `time_range_start` / `time_range_end`
- [ ] Implementasi rate limiting agar satu user tidak bisa spam export
