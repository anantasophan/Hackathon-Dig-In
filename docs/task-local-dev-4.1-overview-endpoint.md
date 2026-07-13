# Task 4.1 — Implementasi `GET /api/campaigns/overview`

## Ringkasan Singkat
Task ini mengimplementasikan endpoint `GET /api/campaigns/overview` pada local development server. Endpoint ini adalah titik masuk utama dashboard, mengembalikan ringkasan performa seluruh kampanye (total leads, total take-up, tingkat konversi, jumlah kampanye, dan data tren mingguan) dengan dukungan filter opsional berdasarkan program, kanal, wilayah, dan jenis leads.

## Penjelasan Awam (Non-Technical)
Bayangkan seorang manajer kampanye bank yang membuka halaman dashboard pagi hari. Dia ingin melihat sekaligus: "Berapa total nasabah yang sudah dihubungi? Berapa yang sudah ambil produk? Kampanye mana saja yang sedang berjalan?" — semua dalam satu tampilan ringkas.

Endpoint ini adalah "meja informasi" yang menjawab semua pertanyaan itu sekaligus. Manajer bisa juga menyaring: "Tampilkan hanya kampanye QRIS" atau "Hanya wilayah Jawa Barat" — dan angka-angka akan berubah otomatis sesuai filter yang dipilih.

Jika tidak ada data yang cocok dengan filter, server tetap menjawab dengan sopan: "Maaf, tidak ada data untuk filter yang Anda pilih" — bukan error.

## Penjelasan Teknis

### File yang Diverifikasi/Diimplementasikan
- `backend/local_server/routers/campaigns.py` — fungsi `campaign_overview` (handler utama)
- Helper functions: `_validate_date`, `_parse_string_list`, `_parse_int_list`, `_build_active_filters`

### Library yang Digunakan
- `fastapi.APIRouter`, `fastapi.HTTPException`, `fastapi.Query` — routing dan validasi FastAPI
- `fastapi.responses.JSONResponse` — kontrol eksplisit atas response JSON
- `shared.calculations.calculate_take_up_rate` — kalkulasi persentase konversi
- `shared.pii_filter.strip_pii` — membersihkan field PII sebelum response
- `shared.models.ActiveFilter` — struktur data untuk filter aktif

### Pola Arsitektur
1. **Validation First**: Date params divalidasi di awal sebelum query apapun
2. **Comma-separated list params**: Query params multi-value dikirim sebagai string CSV (`wilayah=1,3,5`), di-parse oleh helper `_parse_int_list` / `_parse_string_list`
3. **Pre-aggregated trend**: Data tren diambil dari `trend_data.json` (sudah dihitung di ETL), bukan dihitung ulang dari leads — mengikuti pola Lambda handler production
4. **Non-empty guard**: Jika leads kosong setelah filter, langsung return 200 dengan pesan (bukan 404 atau 500)

### Keputusan Desain Penting
- Trend di-deduplicate by `(period_start, period_end)` ketika banyak campaign digabungkan, untuk menghindari duplikasi entry mingguan
- `strip_pii(body)` dipanggil pada seluruh response body sebelum dikirim — termasuk nested dict dalam `trend`
- `calculate_take_up_rate` diproteksi dengan guard `if total_leads > 0` untuk menghindari `ValueError` saat tidak ada leads

### Edge Cases yang Ditangani
- `start_date`/`end_date` format salah → HTTP 400 dengan pesan deskriptif dalam Bahasa Indonesia
- Semua filter aktif tapi tidak ada data yang cocok → HTTP 200 dengan pesan `"Tidak ada data untuk filter yang dipilih"` dan daftar filter aktif
- Campaign IDs dari leads yang tidak ada di `trend_data.json` → `get_trend_data()` mengembalikan list kosong, tidak crash

## Struktur Kode

```python
@router.get("/campaigns/overview")
async def campaign_overview(
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
    flag_program: str | None = Query(default=None),
    media_blasting: str | None = Query(default=None),
    wilayah: str | None = Query(default=None),
    jenis_leads: str | None = Query(default=None),
) -> JSONResponse:
    """Return aggregate campaign metrics with optional filters."""

# Helper functions:
def _validate_date(raw: str | None, field_name: str) -> str | None
    """Validate yyyy-mm-dd format; raise HTTP 400 if invalid."""

def _parse_string_list(raw: str | None) -> list[str] | None
    """Parse comma-separated query param into list of strings."""

def _parse_int_list(raw: str | None) -> list[int] | None
    """Parse comma-separated query param into list of integers."""

def _build_active_filters(...) -> list[ActiveFilter]
    """Build ActiveFilter list from active query parameters."""
```

## Simulasi / Skenario

### Skenario 1 — Dashboard Tanpa Filter (Happy Path)
```
Request:  GET /api/campaigns/overview
Process:  - Tidak ada filter → get_leads() mengembalikan semua ~150 records
          - total_leads=150, total_take_up=30 (asumsi ~20%), take_up_rate=20.0
          - distinct campaign IDs: {C001, C002, C003, C004, C005} → total_campaigns=5
          - Tren dari semua 5 campaign digabung, deduplicate, sort kronologis
Output:   HTTP 200
          {
            "total_leads": 150,
            "total_take_up": 30,
            "take_up_rate": 20.0,
            "total_campaigns": 5,
            "trend": [...12+ entries mingguan...],
            "filters": []
          }
```

### Skenario 2 — Filter Program QRIS + Wilayah 1,3
```
Request:  GET /api/campaigns/overview?flag_program=PROGRAM+QRIS&wilayah=1,3
Process:  - fp_list=["PROGRAM QRIS"], wil_list=[1, 3]
          - store.get_leads() mengembalikan hanya leads QRIS di wilayah 1 atau 3
          - Misalnya 45 records, 9 take-up → take_up_rate=20.0
          - active_filters: [{field:"flag_program", values:["PROGRAM QRIS"]}, 
                             {field:"wilayah", values:["1","3"]}]
Output:   HTTP 200
          {
            "total_leads": 45,
            "total_take_up": 9,
            "take_up_rate": 20.0,
            "total_campaigns": 3,
            "trend": [...campaign C001, C003, C005 trend entries...],
            "filters": [{"field":"flag_program","values":["PROGRAM QRIS"]},
                        {"field":"wilayah","values":["1","3"]}]
          }
```

### Skenario 3 — Filter yang Tidak Cocok (Edge Case)
```
Request:  GET /api/campaigns/overview?media_blasting=push+notif&wilayah=15
Process:  - store.get_leads() mengembalikan [] (tidak ada data push notif di wilayah 15)
Output:   HTTP 200
          {
            "message": "Tidak ada data untuk filter yang dipilih",
            "filters": [{"field":"media_blasting","values":["push notif"]},
                        {"field":"wilayah","values":["15"]}]
          }
```

### Skenario 4 — Format Tanggal Salah (Error Case)
```
Request:  GET /api/campaigns/overview?start_date=01-08-2024
Process:  - _validate_date("01-08-2024", "start_date") → date.fromisoformat() gagal
Output:   HTTP 400
          {
            "detail": "Parameter tanggal tidak valid: '01-08-2024' untuk 'start_date'. 
                       Gunakan format yyyy-mm-dd."
          }
```

## Keterkaitan dengan Komponen Lain

**Bergantung pada:**
- `local_server/mock_store.py` — singleton `store` untuk query leads dan trend data
- `shared/calculations.py` — `calculate_take_up_rate()` untuk kalkulasi persentase
- `shared/pii_filter.py` — `strip_pii()` untuk membersihkan field sensitif
- `shared/models.py` — `ActiveFilter` dataclass untuk struktur filter response

**Digunakan oleh:**
- Frontend Campaign Overview page — memanggil endpoint ini saat halaman dimuat atau filter berubah
- `test_local_server_campaigns.py` — unit tests untuk endpoint ini

**Pengaruh ke:**
- Jika `mock_store.py` diubah (misalnya mengganti field name), handler ini perlu disesuaikan
- Jika `trend_data.json` tidak menyediakan ≥4 entries per campaign, Requirement 2.8 tidak terpenuhi

## Requirements yang Dipenuhi
- **Requirement 2.1** — mengembalikan HTTP 200 dengan field `total_leads`, `total_take_up`, `take_up_rate`, `total_campaigns`, `trend`, `filters`
- **Requirement 2.2** — format date invalid → HTTP 400 dengan pesan deskriptif
- **Requirement 2.3** — filter `flag_program` diterapkan (AND logic)
- **Requirement 2.4** — filter `media_blasting` diterapkan
- **Requirement 2.5** — filter `wilayah` diterapkan (integer)
- **Requirement 2.6** — filter `jenis_leads` diterapkan
- **Requirement 2.7** — kombinasi filter tanpa hasil → HTTP 200 dengan pesan + active filters
- **Requirement 2.8** — `trend` berisi ≥4 data points (dijamin oleh `trend_data.json`)
- **Requirement 2.9** — `strip_pii()` dipanggil → tidak ada `cif` di response

## Catatan Penting

**Limitasi:**
- Trend data adalah pre-aggregated dari `trend_data.json`, bukan dihitung ulang dari leads yang difilter — artinya trend tidak mencerminkan filter `flag_program`/`wilayah` yang diterapkan (konsisten dengan perilaku Lambda production yang menggunakan Athena aggregation table terpisah)
- Deduplication trend berdasarkan `(period_start, period_end)` mungkin menghilangkan entry jika dua campaign punya periode yang overlap persis

**Asumsi:**
- `campaign_id` ada di setiap lead record (field `campaign_id` di leads.json)
- `trend_data.json` menyediakan ≥4 entries untuk setiap campaign ID

**Todo:**
- Saat `selected_granularity` (weekly/monthly) dibutuhkan frontend, tambahkan `select_granularity()` dari `shared.calculations`
