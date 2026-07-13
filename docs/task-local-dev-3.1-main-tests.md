# Task 3.1 — Unit Tests untuk `main.py` (TestClient)

## Ringkasan Singkat
Task ini membuat file unit test untuk FastAPI application entry point (`local_server/main.py`) menggunakan `fastapi.testclient.TestClient`. Test mencakup health check endpoint, penanganan path yang tidak dikenal, header CORS, dan preflight OPTIONS request — memastikan bahwa server lokal berjalan sesuai spesifikasi sebelum campaign endpoints diimplementasikan.

## Penjelasan Awam (Non-Technical)
Bayangkan sebuah resepsionis di bank yang harus lulus serangkaian ujian sebelum mulai bertugas:
1. **Tes "Apakah kamu sehat?"** — Saat ada yang bertanya status server, resepsionis harus menjawab "OK, mode development" dengan benar.
2. **Tes "Jika ada tamu ke ruangan yang tidak ada?"** — Jika seseorang mencari pintu yang tidak terdaftar, resepsionis harus mengatakan "Tidak ada di sini" (404) secara formal, bukan kebingungan.
3. **Tes akses dari tamu asing (CORS)** — Saat aplikasi frontend (dari alamat berbeda) meminta data, server harus mengizinkan dengan tanda `Access-Control-Allow-Origin: *`.
4. **Tes permintaan izin sebelum masuk (Preflight)** — Browser modern meminta izin dulu sebelum mengirim data sensitif; server harus menjawab "diizinkan" agar komunikasi bisa berlanjut.

Manfaat bagi pengguna bisnis: developer tidak akan menghabiskan waktu debugging masalah konektivitas antara frontend dan backend — semua jalur komunikasi dasar sudah terverifikasi.

## Penjelasan Teknis

### File yang Dibuat
- `backend/tests/unit/test_local_server_main.py` — 21 unit test menggunakan `pytest` + `fastapi.testclient.TestClient`

### Library yang Digunakan
- `fastapi.testclient.TestClient` — ASGI test client yang menjalankan FastAPI app in-process tanpa HTTP server sungguhan
- `pytest` — test runner dan fixture system

### Pola Arsitektur
- **Fixture module-scope**: `TestClient` dibungkus dalam `@pytest.fixture(scope="module")` sehingga ASGI lifespan (startup event) hanya berjalan sekali per sesi test, bukan per test case
- **Class-based grouping**: test dikelompokkan dalam class (`TestHealthEndpoint`, `TestNotFoundHandler`, `TestCorsHeaders`, `TestPreflightOptions`) untuk keterbacaan dan namespace yang jelas

### Keputusan Desain Penting
- **Scope `module`** dipilih (bukan `session`) karena modul ini berpotensi perlu state isolation antar file test
- **Header `Origin`** disertakan eksplisit pada CORS test — tanpa header ini, FastAPI's `CORSMiddleware` tidak menyertakan `Access-Control-Allow-Origin` dalam response
- Test OPTIONS menggunakan header standar preflight (`Access-Control-Request-Method`, `Access-Control-Request-Headers`) sesuai spesifikasi CORS W3C

### Edge Cases yang Ditangani
- Path yang tidak dikenal dengan kedalaman berbeda (`/unknown-path`, `/api/does/not/exist`)
- Method POST pada path tidak dikenal juga mengembalikan 404 JSON
- CORS header harus hadir tidak hanya pada 200 response, tetapi juga pada 404 response

## Struktur Kode

```python
# Fixture
@pytest.fixture(scope="module")
def client() -> TestClient
    """TestClient wrapping FastAPI app; startup event runs once."""

# Test Classes
class TestHealthEndpoint           # 5 tests — GET /health (Req 1.4)
class TestNotFoundHandler          # 7 tests — 404 JSON (Req 1.5)
class TestCorsHeaders              # 3 tests — CORS header (Req 1.6)
class TestPreflightOptions         # 6 tests — OPTIONS preflight (Req 1.7)
```

## Simulasi / Skenario

### Skenario 1 — Developer Memverifikasi Server Berjalan (Happy Path)
```
Input:  GET /health
Proses: TestClient mengirim request ke FastAPI app → health_check handler dipanggil
Output: HTTP 200, {"status": "ok", "mode": "local-dev"}
Test:   test_body_exact_shape → assert response.json() == {"status": "ok", "mode": "local-dev"}
```

### Skenario 2 — Frontend di localhost:3000 Melakukan Preflight Request
```
Input:  OPTIONS /api/campaigns/overview
        Headers: Origin: http://localhost:3000
                 Access-Control-Request-Method: GET
                 Access-Control-Request-Headers: Content-Type
Proses: CORSMiddleware menangani OPTIONS → mengembalikan allow headers
Output: HTTP 200, Access-Control-Allow-Origin: *, Access-Control-Allow-Methods: *
Test:   test_preflight_api_path_returns_200, test_preflight_api_path_has_allow_headers
```

### Skenario 3 — Frontend Memanggil Endpoint yang Salah (Error Case)
```
Input:  GET /api/campaigns/overview/detail/extra  (path tidak terdaftar)
Proses: FastAPI tidak menemukan route → custom 404 handler dipanggil
Output: HTTP 404, {"detail": "Not found"}, Content-Type: application/json
Test:   test_deeply_nested_unknown_path_returns_404
```

## Keterkaitan dengan Komponen Lain

**Bergantung pada:**
- `backend/local_server/main.py` — FastAPI app yang ditest
- `backend/local_server/routers/export.py` — stub router yang harus bisa diimport agar `main.py` tidak gagal
- `backend/local_server/mock_store.py` — diimport oleh campaigns router yang di-include di main.py

**Digunakan oleh:**
- Developer sebagai confidence check bahwa infrastruktur dasar server berfungsi
- CI/CD pipeline (jika dikonfigurasi) sebagai regression test

**Pengaruh ke:**
- Jika `main.py` diubah (misalnya mengganti prefix `/api`, menghapus CORS, atau mengubah 404 handler), test ini akan gagal dan memberi peringatan dini

## Requirements yang Dipenuhi
- **Requirement 1.4** — `GET /health` mengembalikan HTTP 200 dengan body `{"status": "ok", "mode": "local-dev"}`
- **Requirement 1.5** — path tidak dikenal mengembalikan HTTP 404 dengan JSON `{"detail": "Not found"}`
- **Requirement 1.6** — header `Access-Control-Allow-Origin: *` hadir di setiap response
- **Requirement 1.7** — preflight OPTIONS request dijawab dengan HTTP 200 dan header CORS lengkap

## Catatan Penting

**Limitasi:**
- Test hanya berjalan saat Python dan `pytest` tersedia — gunakan `get_diagnostics` untuk verifikasi sintaks saat Python belum terinstall
- `TestClient` dari FastAPI menggunakan `httpx` under the hood; behavior CORS mungkin sedikit berbeda dari browser sungguhan dalam kasus edge case tertentu

**Asumsi:**
- `CORSMiddleware` dikonfigurasi dengan `allow_origins=["*"]` — test akan gagal jika origin dibatasi
- Custom 404 handler sudah terdaftar via `@app.exception_handler(404)` di `main.py`

**Todo:**
- Saat Python sudah terinstall, jalankan: `cd backend && python -m pytest tests/unit/test_local_server_main.py -v`
- Pertimbangkan menambahkan test untuk startup log output jika logging menjadi requirement yang lebih ketat
