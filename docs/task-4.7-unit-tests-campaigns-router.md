# Task 4.7 — Unit Tests untuk `routers/campaigns.py` (TestClient)

## Ringkasan Singkat

File pengujian unit ini berisi test lengkap untuk keenam endpoint kampanye pada Local Development
Server. Menggunakan `fastapi.testclient.TestClient` untuk menguji perilaku HTTP secara end-to-end
tanpa memerlukan server yang berjalan. Digunakan oleh QA engineer dan developer untuk memastikan
semua endpoint kampanye berjalan sesuai spesifikasi sebelum deployment.

## Penjelasan Awam (Non-Technical)

Bayangkan Anda memiliki kasir baru di bank. Sebelum kasir itu melayani nasabah sungguhan, Anda
perlu menguji apakah dia bisa menjawab pertanyaan dengan benar — "Berapa total leads bulan ini?",
"Bandingkan kampanye A dan B", dll. File test ini berperan sebagai "penguji" yang mengajukan
ratusan pertanyaan ke server dan memastikan setiap jawaban tepat dan formatnya benar.

**Manfaat bagi pengguna bisnis:**
- Menjamin data kampanye yang ditampilkan di dashboard akurat
- Memastikan filter tanggal/wilayah/program bekerja dengan tepat
- Mencegah bug terselubung yang bisa menyebabkan data salah tampil ke manajemen

## Penjelasan Teknis

**File yang dibuat:**
- `backend/tests/unit/test_local_server_campaigns.py` (852 baris)

**Framework:** `pytest` + `fastapi.testclient.TestClient`

**Pola arsitektur:**
- Satu `@pytest.fixture(scope="module")` untuk TestClient agar ASGI lifespan hanya berjalan sekali
- Setiap endpoint dikelompokkan dalam satu class (`TestCampaignOverview`, `TestCampaignComparison`, dll.)
- Sub-sections dalam class menggunakan komentar `# ----` untuk memisahkan happy path vs error cases

**Keputusan desain penting:**
- Menggunakan `scope="module"` bukan `scope="function"` — lebih cepat karena app hanya diinisialisasi sekali
- Import dari `local_server.main` (bukan router langsung) agar middleware CORS dan route prefix `/api` ikut teruji
- Test tidak menggunakan mock — data nyata dari `mock_data/*.json` dipakai langsung
- Toleransi floating-point pada persentase histogram: `abs(total - 100.0) < 0.1`

## Struktur Kode

```python
# Fixture bersama
@pytest.fixture(scope="module")
def client() -> TestClient: ...

class TestCampaignOverview:        # GET /api/campaigns/overview
class TestCampaignComparison:      # POST /api/campaigns/comparison
class TestTimeAnalysis:            # GET /api/campaigns/time-analysis/{id}
class TestRegionalPerformance:     # GET /api/campaigns/regional/{id}
class TestCustomerCriteria:        # GET /api/campaigns/customer-criteria/{id}
class TestSimilarCampaign:         # POST /api/campaigns/similar
```

## Simulasi / Skenario

### Skenario 1 — Happy Path: Overview tanpa filter

```
Input:  GET /api/campaigns/overview
Proses: Server memuat semua leads dari mock_data/leads.json
Output: {
  "total_leads": 149,
  "total_take_up": 32,
  "take_up_rate": 21.48,
  "total_campaigns": 5,
  "trend": [...],
  "filters": []
}
Assert: status 200, semua field hadir, take_up_rate ∈ [0, 100], trend ≥ 4 titik
```

### Skenario 2 — Error Case: Tanggal invalid

```
Input:  GET /api/campaigns/overview?start_date=not-a-date
Proses: _validate_date() gagal parsing → HTTPException 400
Output: {"detail": "Parameter tanggal tidak valid: ..."}
Assert: status 400, "detail" ada di body
```

### Skenario 3 — Edge Case: > 5 IDs pada Comparison

```
Input:  POST /api/campaigns/comparison
        {"campaign_ids": ["C001","C002","C003","C004","C005","C006"]}
Proses: len(campaign_ids) > 5 → HTTPException 400
Output: {"detail": "campaign_ids must contain at most 5 campaign identifiers, got 6."}
Assert: status 400, "detail" ada di body
```

## Keterkaitan dengan Komponen Lain

- **Bergantung pada:** `local_server/main.py` (app instance), `local_server/mock_store.py` (data),
  `local_server/mock_data/*.json` (fixture data), `shared/calculations.py`, `shared/sorting.py`
- **Digunakan oleh:** CI pipeline, developer saat mengembangkan fitur baru pada router campaigns
- **Pengaruh ke:** Jika mock data berubah (jumlah records, nilai field), beberapa assertion numerik
  (seperti `total_campaigns == 5`) perlu diperbarui

## Requirements yang Dipenuhi

- **2.1–2.9** — Campaign Overview: no params, invalid date, flag_program, media_blasting, wilayah, date range, empty result
- **3.1–3.7** — Campaign Comparison: 2 IDs, < 2 IDs → 400, > 5 IDs → 400, group_by sort, metric fields, chart shape
- **4.1–4.7** — Time Analysis: 7-bin histogram, stats, empty campaign, channel filter, region filter
- **5.1–5.6** — Regional Performance: descending sort, selected_region trend, empty regions, flag_program filter
- **6.1–6.7** — Customer Criteria: 5 distribusi, available/unavailable attrs, empty campaign, percentage sum
- **7.1–7.7** — Similar Campaign: valid request, invalid dimensions → 400, sort order, limit cap, empty reference → 400

## Catatan Penting

- **Python tidak tersedia di PATH** — jalankan test dengan menginstall Python dari python.org terlebih dahulu,
  lalu `cd backend && python -m pytest tests/unit/test_local_server_campaigns.py -v`
- **Toleransi floating-point** digunakan untuk perbandingan persentase (< 0.5% margin)
- Test `test_flag_program_filter_no_match_returns_empty_regions` bergantung pada fakta bahwa C002
  adalah "PROGRAM BIAYA ADMIN" — jika mock data berubah, test ini perlu disesuaikan
- Test `test_no_params_total_campaigns_equals_five` hardcode nilai 5 sesuai jumlah campaign di mock data
