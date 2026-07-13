# Task 6.1 — Helper Functions Export: `_generate_csv`, `_generate_excel`, `_generate_pdf`

## Ringkasan Singkat

Task ini mengimplementasikan tiga fungsi pembantu (helper) untuk membuat file ekspor dalam format CSV, Excel (.xlsx), dan PDF. Ketiga fungsi ini merupakan adaptasi dari Lambda handler ekspor yang sudah ada, namun tanpa ketergantungan pada AWS S3 atau boto3 — file disimpan langsung ke disk lokal. Fungsi-fungsi ini menjadi fondasi dari fitur ekspor di local development server.

---

## Penjelasan Awam (Non-Technical)

Bayangkan Anda sedang bekerja di Excel dan ingin menyimpan laporan ke dalam berbagai format: CSV untuk dikirim ke tim data, Excel untuk dianalisa lebih lanjut, dan PDF untuk dilampirkan ke email kepada pimpinan. Ketiga fungsi ini melakukan hal yang persis sama — menerima informasi tentang kampanye (nama halaman, rentang waktu, filter aktif) lalu menghasilkan file dalam format yang diminta.

Di lingkungan produksi (AWS), file tersebut diunggah ke S3 dan diakses via link sementara. Di server lokal ini, file cukup disimpan di folder `exports/` dan langsung bisa diakses oleh browser.

**Manfaat bisnis:** Developer yang bekerja di laptop bisa menguji alur ekspor secara penuh — dari klik tombol "Export" di frontend hingga mengunduh file — tanpa perlu koneksi internet atau akun AWS.

---

## Penjelasan Teknis

### File yang Dibuat/Dimodifikasi

- **`backend/local_server/routers/export.py`** — Menggantikan stub kosong sebelumnya dengan implementasi lengkap helper functions + empty router.

### Library yang Digunakan

- **`csv`** (stdlib) — untuk menulis baris CSV
- **`io`** (stdlib) — `StringIO` dan `BytesIO` sebagai buffer in-memory
- **`openpyxl`** (lazy import di dalam fungsi) — untuk membuat workbook `.xlsx`
- **`reportlab`** (lazy import di dalam fungsi) — untuk membuat dokumen `.pdf`
- **`fastapi.APIRouter`** — router kosong; endpoint POST/GET ditambahkan di task 6.2/6.3

### Keputusan Desain

1. **Lazy imports untuk openpyxl dan reportlab** — di-import di dalam fungsi, bukan di level modul. Ini mencegah `ImportError` saat modul di-load jika library belum ter-install. Pola ini sama persis dengan Lambda handler aslinya.

2. **Tidak ada boto3/S3** — satu-satunya perbedaan struktural dari Lambda handler. Fungsi generator murni menghasilkan `bytes`, tanpa side effect ke infrastruktur cloud.

3. **`_filter_summary()`** — helper kecil yang mengubah list `ActiveFilter` menjadi string ringkas untuk ditulis ke metadata file ekspor. Identik dengan implementasi di Lambda handler.

4. **CSV metadata sebagai komentar `#`** — baris `# source:`, `# period:`, dan `# filters:` ditulis sebelum header kolom. Baris komentar ini tidak akan diinterpretasikan sebagai data oleh parser CSV standar, namun bisa dibaca manusia.

5. **Konstanta `_EXPORTS_DIR`** — menggunakan `pathlib.Path(__file__).parent.parent / "exports"` agar path selalu relatif terhadap lokasi file ini, bukan working directory saat server dijalankan.

### Struktur Kode

```python
# Konstanta
_VALID_FORMATS: frozenset[str]       # {"pdf", "excel", "csv"}
_FORMAT_EXT: dict[str, str]          # {"pdf": "pdf", "excel": "xlsx", "csv": "csv"}
_EXPORTS_DIR: pathlib.Path           # .../local_server/exports/

# Helper
_filter_summary(filters) -> str      # Ringkasan filter untuk metadata

# Generator
_generate_csv(request) -> bytes      # UTF-8 CSV dengan metadata komentar #
_generate_excel(request) -> bytes    # .xlsx dua sheet: Metadata + Data
_generate_pdf(request) -> bytes      # PDF dengan tabel metadata + tabel data

# Dispatcher
_generate_file(request) -> bytes     # Memanggil generator sesuai request.format

# Router
router = APIRouter()                 # Kosong; diisi di task 6.2 dan 6.3
```

---

## Simulasi / Skenario

### Skenario 1 — Ekspor CSV (Happy Path)

**Input:**
```python
request = ExportRequest(
    page="campaign_overview",
    format="csv",
    filters=[ActiveFilter(field="flag_program", values=["PROGRAM QRIS"])],
    time_range_start="2024-08-01",
    time_range_end="2024-08-31",
)
```

**Proses:** `_generate_csv(request)` menulis ke `StringIO`, lalu encode ke UTF-8.

**Output (isi file):**
```
# source: campaign_overview
# period: 2024-08-01 to 2024-08-31
# filters: flag_program=PROGRAM QRIS
nama_program,flag_program,media_blasting,...
N/A (MVP placeholder),N/A,...
```

### Skenario 2 — Ekspor Excel

**Input:** sama seperti di atas dengan `format="excel"`

**Proses:** `_generate_excel(request)` membuat `Workbook` openpyxl dengan dua sheet — "Metadata" berisi baris `Source Page`, `Time Range Start`, dll, dan "Data" berisi placeholder row.

**Output:** bytes `.xlsx` yang bisa dibuka di Microsoft Excel atau LibreOffice Calc.

### Skenario 3 — Library Tidak Ter-install

**Input:** `format="pdf"` tapi `reportlab` belum diinstall

**Proses:** `_generate_pdf()` mencoba `from reportlab.lib import colors` → gagal → raise `ImportError` dengan pesan yang jelas: `"Export format 'pdf' requires reportlab. Run: pip install reportlab>=4.2.0"`.

**Output:** Endpoint menangkap `ImportError` ini (di task 6.2) dan mengembalikan HTTP 500 dengan pesan yang informatif.

---

## Keterkaitan dengan Komponen Lain

- **Bergantung pada:**
  - `shared.models.ExportRequest` dan `shared.models.ActiveFilter` — tipe data request
  - `openpyxl` (opsional, lazy) — untuk format Excel
  - `reportlab` (opsional, lazy) — untuk format PDF

- **Digunakan oleh:**
  - Task 6.2 — `POST /api/export` endpoint yang akan memanggil `_generate_file()` lalu menyimpan hasilnya ke `_EXPORTS_DIR`
  - Task 6.4 — unit tests yang akan memanggil generator functions secara langsung

- **Pengaruh ke:**
  - Perubahan pada `ExportRequest` di `shared/models.py` akan mempengaruhi signature fungsi-fungsi ini

---

## Requirements yang Dipenuhi

- **Req 8.1** — CSV/Excel/PDF dapat dihasilkan oleh server
- **Req 8.2** — Metadata (source, period, active filters) disertakan dalam setiap format file
- **Req 8.3** — Format yang dihasilkan sesuai (`bytes` yang bisa disimpan dan di-serve)
- **Req 8.7** — File CSV menyertakan baris metadata komentar `#` di bagian atas

---

## Catatan Penting

- **Lazy imports** adalah wajib — jangan pindahkan `import openpyxl` atau `import reportlab` ke level modul, karena akan menyebabkan `ImportError` saat server dijalankan di lingkungan tanpa library tersebut.
- **Placeholder data** — isi baris data adalah placeholder ("N/A (MVP placeholder)"). Di produksi, baris ini akan diganti dengan data nyata dari Athena. Ini adalah batasan MVP yang disengaja.
- **`_EXPORTS_DIR`** — path ini digunakan oleh task 6.2 untuk menyimpan file. Pastikan folder `exports/` sudah ada (terjamin oleh `.gitkeep`).
- File ini tidak mengandung endpoint apapun — POST dan GET endpoint ditambahkan di task 6.2 dan 6.3.
