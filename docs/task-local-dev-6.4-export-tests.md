# Task 6.4 — Unit Tests untuk `routers/export.py` (TestClient)

## Ringkasan Singkat

Task ini membuat file unit test komprehensif untuk dua endpoint ekspor pada Local Development Server: `POST /api/export` (generate file CSV/Excel/PDF) dan `GET /exports/{filename}` (unduh file hasil ekspor). Test menggunakan `fastapi.testclient.TestClient` tanpa server sungguhan dan mencakup seluruh acceptance criteria Requirement 8.1–8.7.

---

## Penjelasan Awam (Non-Technical)

Bayangkan fitur ekspor seperti mesin fotokopi di kantor: pegawai menekan tombol, memilih format kertas (A4 / Letter / landscape), dan mesin menghasilkan salinan dokumen. Unit test di sini berperan sebagai petugas QA yang mencoba semua tombol satu per satu — tombol yang benar harus menghasilkan salinan, tombol yang salah (format tidak tersedia) harus menolak dengan pesan jelas, dan mesin tidak boleh crash jika tombol ditekan tanpa kertas di dalamnya.

Manfaat bagi tim:
- **Ketenangan pikiran** — setiap kali kode diubah, test otomatis memverifikasi bahwa ekspor masih bekerja
- **Dokumentasi hidup** — setiap test case menjelaskan perilaku yang diharapkan dengan bahasa natural
- **Deteksi regresi dini** — jika `_generate_csv` atau validator body diubah sembarangan, test langsung merah

---

## Penjelasan Teknis

### File yang Dibuat

| File | Keterangan |
|------|-----------|
| `backend/tests/unit/test_local_server_export.py` | File test baru — 50+ assertion dalam 5 kelas test |

### Library / Framework

- **pytest** — test runner dan fixture
- **fastapi.testclient.TestClient** — ASGI test client, tidak memerlukan server berjalan
- **re** (stdlib) — validasi pola URL `download_url` dengan regex

### Pola Arsitektur

- **Module-scoped fixture** `client` — `TestClient` dibungkus `with` statement sehingga lifespan (startup event) hanya berjalan sekali per modul, menjaga tes tetap cepat
- **Test class per skenario** — memudahkan pengelompokan dan pembacaan laporan pytest
- **Shared constant `_VALID_BODY`** — satu dict valid dipakai sebagai dasar semua variasi tes
- **Regex `_DOWNLOAD_URL_PATTERN`** — verifikasi format UUID dalam URL tanpa string matching rapuh

### Keputusan Desain

1. **Tidak di-mock** — test memanggil router sungguhan dan menyentuh filesystem (`exports/`). Ini memverifikasi integrasi nyata antara handler, `_generate_csv`/`_generate_excel`/`_generate_pdf`, dan `pathlib.Path`.
2. **GET setelah POST** — beberapa test CSV men-download file yang baru di-POST untuk memverifikasi isi metadata `#` secara end-to-end (Req 8.7).
3. **Edge case filters** — test memvalidasi bahwa `filters` sebagai bukan list ditolak, namun `filters` yang dihilangkan (tidak ada di body) diizinkan karena router default ke `[]`.

### Struktur Kelas Test

| Kelas | Endpoint | Skenario |
|-------|----------|---------|
| `TestPostExportCsv` | POST /api/export | format csv: 200, status, URL, metadata # |
| `TestPostExportExcel` | POST /api/export | format excel: 200, status, URL `.xlsx` |
| `TestPostExportPdf` | POST /api/export | format pdf: 200, status, URL `.pdf` |
| `TestPostExportInvalidFormat` | POST /api/export | format tidak valid → 400 |
| `TestPostExportEmptyBody` | POST /api/export | body kosong/tidak lengkap → 400 |
| `TestGetExportFile` | GET /exports/{filename} | file ada → 200; tidak ada → 404 |
| `TestPostExportFilters` | POST /api/export | variasi field `filters` |

---

## Struktur Kode

```python
# Fixture module-scoped
@pytest.fixture(scope="module")
def client() -> TestClient:
    with TestClient(app) as c:
        yield c

# Konstanta bersama
_VALID_BODY: dict = { "page": "...", "format": "csv", ... }
_DOWNLOAD_URL_PATTERN = re.compile(r"^/exports/[uuid]\.(csv|xlsx|pdf)$")

# 7 kelas test — masing-masing fokus pada satu skenario
class TestPostExportCsv: ...        # 8 test
class TestPostExportExcel: ...      # 5 test
class TestPostExportPdf: ...        # 5 test
class TestPostExportInvalidFormat:  # 6 test
class TestPostExportEmptyBody: ...  # 9 test
class TestGetExportFile: ...        # 9 test
class TestPostExportFilters: ...    # 4 test
```

---

## Simulasi / Skenario

### Skenario 1 — Happy Path CSV (Req 8.1, 8.4, 8.7)

**Input:**
```json
POST /api/export
{
  "page": "campaign_overview",
  "format": "csv",
  "filters": [{"field": "flag_program", "values": ["PROGRAM QRIS"]}],
  "time_range_start": "2024-08-01",
  "time_range_end": "2024-08-31"
}
```

**Proses:** router memvalidasi body → memanggil `_generate_csv()` → menulis file ke `exports/{uuid}.csv` → mengembalikan URL

**Output (200):**
```json
{
  "status": "completed",
  "download_url": "/exports/3f2504e0-4f89-11d3-9a0c-0305e82c3301.csv"
}
```

**GET /exports/3f2504e0-....csv → 200**, konten:
```
# source: campaign_overview
# period: 2024-08-01 to 2024-08-31
# filters: flag_program=PROGRAM QRIS
nama_program,flag_program,...
N/A (MVP placeholder),...
```

### Skenario 2 — Format Tidak Valid (Req 8.5)

**Input:**
```json
POST /api/export
{ "page": "...", "format": "docx", "filters": [], ... }
```

**Output (400):**
```json
{
  "detail": "Unsupported export format 'docx'. Must be one of: csv, excel, pdf"
}
```

### Skenario 3 — File Tidak Ditemukan (Req 8.4)

**Input:** `GET /exports/nonexistent_file_12345.csv`

**Output (404):**
```json
{ "detail": "Export file not found" }
```

---

## Keterkaitan dengan Komponen Lain

- **Bergantung pada:** `local_server/routers/export.py` — router yang di-test; `local_server/main.py` — app entry point; `shared/models.py` — `ExportRequest`, `ActiveFilter`
- **Digunakan oleh:** CI pipeline pytest, developer lokal yang menjalankan `python -m pytest tests/unit/test_local_server_export.py`
- **Pengaruh ke:** Jika `_generate_csv` atau `_generate_excel` diubah, test metadata CSV (`TestPostExportCsv.test_csv_file_contains_metadata_comment`) akan merah

---

## Requirements yang Dipenuhi

| Requirement | Isi | Kelas Test yang Memvalidasi |
|-------------|-----|-----------------------------|
| 8.1 | POST format=csv → 200, status=completed | `TestPostExportCsv` |
| 8.2 | POST format=excel → 200, status=completed | `TestPostExportExcel` |
| 8.3 | POST format=pdf → 200, status=completed | `TestPostExportPdf` |
| 8.4 | download_url pattern `/exports/{filename}.{ext}`; GET → 200; GET nonexistent → 404 | `TestPostExportCsv/Excel/Pdf`, `TestGetExportFile` |
| 8.5 | Format tidak valid → 400 + detail | `TestPostExportInvalidFormat` |
| 8.6 | Body kosong/tidak lengkap → 400 | `TestPostExportEmptyBody` |
| 8.7 | CSV berisi blok metadata `#source`, `#period`, `#filters` | `TestPostExportCsv` |

---

## Catatan Penting

1. **Python tidak tersedia di PATH** — verifikasi dilakukan via `get_diagnostics` (Pylance), bukan `python -m pytest`. Untuk menjalankan test secara nyata: `cd backend && python -m pytest tests/unit/test_local_server_export.py -v`
2. **Test menyentuh filesystem** — file ekspor ditulis ke `backend/local_server/exports/`. Direktori ini sudah ada (`.gitkeep`). Test tidak membersihkan file yang dibuat — ini disengaja agar test GET setelah POST bekerja dalam satu sesi.
3. **openpyxl dan reportlab wajib terinstall** — test Excel dan PDF akan gagal dengan `ImportError` jika library tidak tersedia. Keduanya ada di `requirements-dev.txt`.
4. **Regex UUID** — `_DOWNLOAD_URL_PATTERN` memverifikasi format UUID v4 standar (8-4-4-4-12 hex). Jika implementasi mengubah UUID generator, pattern ini perlu disesuaikan.
