# Task 6.2 — POST /api/export Endpoint

## Ringkasan Singkat

Task ini menambahkan route handler `POST /api/export` ke `backend/local_server/routers/export.py`. Endpoint menerima permintaan ekspor data (format CSV, Excel, atau PDF), memvalidasi input, menghasilkan file menggunakan helper functions yang sudah ada dari task 6.1, menyimpan file ke direktori lokal `exports/`, dan mengembalikan URL download yang dapat langsung digunakan.

---

## Penjelasan Awam (Non-Technical)

Bayangkan tombol "Ekspor Data" di dashboard kampanye. Saat pengguna mengkliknya dan memilih format (misalnya Excel), browser mengirim permintaan ke server. Server kemudian:

1. Mengecek apakah permintaan valid (format yang diminta dikenal? field wajib ada?)
2. Membuat file sesuai format yang diminta
3. Menyimpan file di folder khusus di komputer lokal
4. Memberikan alamat URL kepada browser sehingga file bisa langsung diunduh

Analoginya seperti mesin fotokopi kantor: Anda tekan tombol format (A4/A3), mesin mencetak, dan menghasilkan nomor antrian untuk mengambil salinan Anda. Tanpa koneksi ke cloud/AWS sama sekali — semua terjadi di laptop developer.

---

## Penjelasan Teknis

### File yang Dimodifikasi

- `backend/local_server/routers/export.py` — ditambahkan:
  - Import baru: `HTTPException`, `Request`, `FileResponse`, `JSONResponse` dari FastAPI
  - Route handler `export_data` pada `POST /api/export`
  - Route handler `serve_export` pada `GET /exports/{filename}` (task 6.3, diimplementasikan bersamaan)

### Pola Arsitektur

Karena `ExportRequest` adalah Python `dataclass` (bukan Pydantic `BaseModel`), FastAPI tidak bisa otomatis mem-parse dan memvalidasi body request. Oleh karena itu handler memproses body secara manual:

```python
# Tidak bisa: async def export_data(body: ExportRequest)  ← dataclass bukan Pydantic
# Harus pakai: Request.body() + Request.json() manual
body_bytes = await request.body()
raw = await request.json()
```

### Alur Validasi

```
Body kosong?                → 400 "Request body is required."
Bukan JSON valid?           → 400 "Request body must be valid JSON."
Body bukan dict/kosong?     → 400 "Request body is required."
field 'page' tidak ada?     → 400 "Field 'page' is required..."
field 'format' tidak ada?   → 400 "Field 'format' is required..."
format bukan csv/excel/pdf? → 400 "Unsupported export format '...'. Must be one of: csv, excel, pdf"
field 'time_range_start'?   → 400 "Field 'time_range_start' is required..."
field 'time_range_end'?     → 400 "Field 'time_range_end' is required..."
field 'filters' bukan list? → 400 "Field 'filters' must be a JSON array."
```

### Alur Eksekusi Sukses

```python
ExportRequest(page, format, filters, time_range_start, time_range_end)
    ↓
_generate_file(export_request)   # dispatch ke _generate_csv/_generate_excel/_generate_pdf
    ↓
_EXPORTS_DIR.mkdir(exist_ok=True)
target_path.write_bytes(file_bytes)  # simpan ke exports/{uuid}.{ext}
    ↓
{"status": "completed", "download_url": "/exports/{uuid}.{ext}"}
```

### Error Handling

- `OSError` saat menulis file → HTTP 500 dengan detail pesan sistem
- Semua error validasi → HTTP 400 via `HTTPException`

### Keputusan Desain

- **`_EXPORTS_DIR.mkdir(parents=True, exist_ok=True)`** dipanggil setiap request untuk memastikan direktori selalu ada, bahkan jika dihapus secara manual saat server berjalan.
- **UUID v4** sebagai nama file → tidak ada collision antar ekspor, tidak ada informasi yang bocor ke klien.
- Route didefinisikan sebagai `@router.post("/api/export")` (bukan `/export`) karena router di-include ke `app` **tanpa prefix** di `main.py`, sehingga path penuh menjadi `/api/export`.

---

## Struktur Kode

```python
# Route handler utama
@router.post("/api/export")
async def export_data(request: Request) -> JSONResponse:
    """Parse body manual → validasi → generate file → simpan → return URL."""

# Route handler file serving (task 6.3)
@router.get("/exports/{filename}", include_in_schema=False)
async def serve_export(filename: str) -> FileResponse:
    """Serve file dari direktori exports/, 404 jika tidak ada."""
```

---

## Simulasi / Skenario

### Skenario 1: Ekspor CSV berhasil

**Request:**
```json
POST /api/export
{
  "page": "overview",
  "format": "csv",
  "filters": [{"field": "flag_program", "values": ["PROGRAM QRIS"]}],
  "time_range_start": "2024-08-01",
  "time_range_end": "2024-10-31"
}
```

**Proses:**
1. Validasi: semua field ada, format "csv" valid
2. `_generate_csv(request)` → menghasilkan bytes CSV dengan metadata header `# source: overview`
3. File disimpan ke `backend/local_server/exports/a3f9bc12-...-4d2e.csv`
4. Return response

**Response:**
```json
{
  "status": "completed",
  "download_url": "/exports/a3f9bc12-...-4d2e.csv"
}
```

---

### Skenario 2: Format tidak valid → 400

**Request:**
```json
POST /api/export
{"page": "overview", "format": "xml", "filters": [], "time_range_start": "2024-08-01", "time_range_end": "2024-10-31"}
```

**Response:**
```json
{
  "detail": "Unsupported export format 'xml'. Must be one of: csv, excel, pdf"
}
```

---

### Skenario 3: Body kosong → 400

**Request:**
```
POST /api/export
(body kosong)
```

**Response:**
```json
{
  "detail": "Request body is required."
}
```

---

## Keterkaitan dengan Komponen Lain

- **Bergantung pada:**
  - `_generate_csv`, `_generate_excel`, `_generate_pdf`, `_generate_file` — dari task 6.1 di file yang sama
  - `shared.models.ExportRequest`, `ActiveFilter` — dataclass request/response
  - `_EXPORTS_DIR`, `_VALID_FORMATS`, `_FORMAT_EXT` — konstanta dari task 6.1

- **Digunakan oleh:**
  - Frontend Export component — memanggil `POST /api/export` lalu redirect ke `download_url`
  - `GET /exports/{filename}` — melanjutkan alur download setelah mendapat URL

- **Pengaruh ke:**
  - Folder `backend/local_server/exports/` — file baru dibuat setiap ekspor berhasil
  - `GET /exports/{filename}` — URL yang dikembalikan langsung merujuk ke endpoint ini

---

## Requirements yang Dipenuhi

- **8.1** — `POST /api/export` dengan format `csv` → 200 + `status: "completed"` + `download_url`
- **8.2** — Format `excel` → file `.xlsx` dapat diunduh
- **8.3** — Format `pdf` → file `.pdf` dapat diunduh
- **8.4** — `download_url` berupa path lokal `/exports/{filename}` (bukan S3 presigned URL)
- **8.5** — Format tidak valid → 400 dengan pesan yang menyebutkan format tidak valid
- **8.6** — Body kosong atau bukan JSON → 400

---

## Catatan Penting

- **Python tidak tersedia di PATH sistem** — verifikasi dilakukan dengan `get_diagnostics` (Pylance). Diagnostics mengembalikan "No diagnostics found" → file valid secara sintaksis dan semantik.
- Format "excel" membutuhkan `openpyxl` dan format "pdf" membutuhkan `reportlab` — keduanya sudah ada di `requirements-dev.txt`.
- File ekspor **tidak otomatis dihapus** — untuk MVP ini developer perlu membersihkan folder `exports/` secara manual. File-file ini sudah di-gitignore (`*.csv`, `*.xlsx`, `*.pdf`).
- Jika `_EXPORTS_DIR` tidak bisa dibuat (misalnya permissions issue), endpoint mengembalikan HTTP 500 bukan crash.
