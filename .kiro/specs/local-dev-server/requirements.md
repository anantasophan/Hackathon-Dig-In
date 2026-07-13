# Requirements Document — Local Development Server

## Introduction

Fitur ini menyediakan local development server yang memungkinkan seluruh stack Campaign Insight Generator (frontend React + backend Python) dapat dijalankan sepenuhnya di laptop lokal **tanpa koneksi ke AWS sama sekali**. Server lokal mengekspos 8 endpoint API yang identik dengan Lambda handlers yang ada di AWS, menggunakan data dummy JSON yang representatif untuk domain kampanye bank (QRIS, leads nasabah, wilayah, dll). Lambda handlers yang sudah ada tidak boleh dimodifikasi — server lokal adalah komponen terpisah.

---

## Glossary

- **Local_Server**: Python FastAPI application yang berjalan di `http://localhost:8000` sebagai pengganti AWS API Gateway + Lambda di lingkungan lokal.
- **Mock_Data_Store**: Kumpulan data dummy JSON yang tersimpan di `backend/local_server/mock_data/` dan digunakan sebagai sumber data oleh Local_Server.
- **Lambda_Handler**: File `handler.py` di dalam `backend/lambdas/<name>/` yang merupakan kode existing yang tidak boleh diubah.
- **Frontend**: Aplikasi React TypeScript yang dikonfigurasi via `.env.local` untuk mengarah ke `http://localhost:8000`.
- **Endpoint**: Satu URL path + HTTP method yang diekspos oleh Local_Server.
- **CampaignOverview_Endpoint**: `GET /api/campaigns/overview`
- **CampaignComparison_Endpoint**: `POST /api/campaigns/comparison`
- **TimeAnalysis_Endpoint**: `GET /api/campaigns/time-analysis/{campaign_id}`
- **RegionalPerformance_Endpoint**: `GET /api/campaigns/regional/{campaign_id}`
- **CustomerCriteria_Endpoint**: `GET /api/campaigns/customer-criteria/{campaign_id}`
- **SimilarCampaign_Endpoint**: `POST /api/campaigns/similar`
- **Export_Endpoint**: `POST /api/export`
- **HealthCheck_Endpoint**: `GET /health`
- **flag_program**: Tipe program kampanye — nilai valid: `"PROGRAM BIAYA ADMIN"` atau `"PROGRAM QRIS"`.
- **media_blasting**: Kanal distribusi leads — nilai valid: `wa`, `digisales`, `telesales`, `email`, `push notif`, `sms`.
- **wilayah**: Kode region, integer 1–17.
- **jenis_leads**: Tujuan leads, misalnya `"Migrasi"`, `"Akuisisi"`.
- **take_up_flag**: Apakah nasabah mengambil produk — nilai `"YES"` atau `"NO"`.
- **cif**: Customer identifier (PII) — harus dikecualikan dari semua respons API.

---

## Requirements

### Requirement 1: Server Startup dan Health Check

**User Story:** Sebagai developer, saya ingin menjalankan local server dengan satu perintah sederhana, sehingga saya bisa mulai development tanpa konfigurasi yang rumit.

#### Acceptance Criteria

1. THE Local_Server SHALL dapat dijalankan dengan perintah `uvicorn local_server.main:app --reload --port 8000` dari direktori `backend/`.
2. THE Local_Server SHALL dapat dijalankan via npm script `npm run dev:backend` dari root project.
3. WHEN Local_Server berhasil start, THE Local_Server SHALL log pesan startup yang menyebutkan port 8000 dan daftar endpoint yang tersedia ke stdout.
4. THE HealthCheck_Endpoint SHALL mengembalikan HTTP 200 dengan body `{"status": "ok", "mode": "local-dev"}`.
5. WHEN Local_Server menerima request ke path yang tidak terdefinisi (termasuk path yang mungkin ditangani middleware atau catch-all routes), THE Local_Server SHALL mengembalikan HTTP 404 dengan body JSON `{"detail": "Not found"}`.
6. THE Local_Server SHALL menambahkan header CORS `Access-Control-Allow-Origin: *` pada setiap response, termasuk preflight OPTIONS.
7. THE Local_Server SHALL merespons preflight OPTIONS request ke semua endpoint dengan HTTP 200 dan header CORS yang lengkap.

---

### Requirement 2: Campaign Overview Endpoint

**User Story:** Sebagai developer yang menguji halaman overview, saya ingin CampaignOverview_Endpoint mengembalikan data mock yang realistis dengan filter yang berfungsi, sehingga frontend dapat merender dashboard overview secara lokal.

#### Acceptance Criteria

1. WHEN request `GET /api/campaigns/overview` diterima tanpa query params, THE CampaignOverview_Endpoint SHALL mengembalikan HTTP 200 dengan body yang mengandung field `total_leads`, `total_take_up`, `take_up_rate`, `total_campaigns`, `trend`, dan `filters`.
2. WHEN query param `start_date` atau `end_date` diberikan dalam format bukan `yyyy-mm-dd`, THE CampaignOverview_Endpoint SHALL mengembalikan HTTP 400 dengan pesan error yang menjelaskan format yang benar.
3. WHEN query param `flag_program` diberikan, THE CampaignOverview_Endpoint SHALL menyaring Mock_Data_Store hanya ke records yang `flag_program`-nya cocok dan mengembalikan agregat yang mencerminkan filter tersebut.
4. WHEN query param `media_blasting` diberikan, THE CampaignOverview_Endpoint SHALL menyaring Mock_Data_Store hanya ke records dengan `media_blasting` yang cocok.
5. WHEN query param `wilayah` diberikan sebagai nilai integer yang dipisahkan koma, THE CampaignOverview_Endpoint SHALL menyaring Mock_Data_Store hanya ke records dengan `wilayah` yang cocok.
6. WHEN query param `jenis_leads` diberikan, THE CampaignOverview_Endpoint SHALL menyaring Mock_Data_Store hanya ke records dengan `jenis_leads` yang cocok.
7. WHEN kombinasi filter aktif tidak menghasilkan records, THE CampaignOverview_Endpoint SHALL mengembalikan HTTP 200 dengan pesan `"Tidak ada data untuk filter yang dipilih"` dan field `filters` yang berisi filter aktif tersebut.
8. THE field `trend` pada response SHALL selalu berisi minimal 4 data points berurutan secara kronologis dengan field `period_start`, `period_end`, `take_up_rate`, `total_leads`, `total_take_up` — Mock_Data_Store harus menyediakan data yang cukup untuk memenuhi requirement ini.
9. THE response SHALL tidak mengandung field `cif` atau nilai PII lainnya.

---

### Requirement 3: Campaign Comparison Endpoint

**User Story:** Sebagai developer yang menguji halaman perbandingan, saya ingin CampaignComparison_Endpoint menerima 2–5 campaign ID dan mengembalikan metrik perbandingan dari data mock, sehingga frontend dapat merender chart perbandingan secara lokal.

#### Acceptance Criteria

1. WHEN request `POST /api/campaigns/comparison` diterima dengan body `{"campaign_ids": ["C001", "C002"]}`, THE CampaignComparison_Endpoint SHALL mengembalikan HTTP 200 dengan field `campaigns` (list) dan `comparison_chart`.
2. WHEN body JSON tidak valid atau kosong, THE CampaignComparison_Endpoint SHALL mengembalikan HTTP 400 dengan pesan error.
3. WHEN `campaign_ids` berisi kurang dari 2 ID, THE CampaignComparison_Endpoint SHALL mengembalikan HTTP 400 dengan pesan yang menyatakan minimal 2 ID diperlukan.
4. WHEN `campaign_ids` berisi lebih dari 5 ID, THE CampaignComparison_Endpoint SHALL mengembalikan HTTP 400 dengan pesan yang menyatakan maksimal 5 ID diperbolehkan.
5. THE setiap item dalam field `campaigns` SHALL mengandung field `campaign_id`, `campaign_name`, `flag_program`, `total_leads`, `total_take_up`, `take_up_rate`, `total_transaction_value`, dan `duration_days`.
6. WHEN `group_by` diberikan dengan nilai `"flag_program"`, `"wilayah"`, atau `"media_blasting"`, THE CampaignComparison_Endpoint SHALL mengembalikan campaigns yang diurutkan berdasarkan atribut tersebut secara ascending.
7. THE `comparison_chart` SHALL mengandung field `labels` dan `datasets` yang kompatibel dengan format Chart.js.

---

### Requirement 4: Time Analysis Endpoint

**User Story:** Sebagai developer yang menguji halaman analisis waktu, saya ingin TimeAnalysis_Endpoint mengembalikan histogram dan statistik dari data mock, sehingga frontend dapat merender distribusi waktu take-up secara lokal.

#### Acceptance Criteria

1. WHEN request `GET /api/campaigns/time-analysis/{campaign_id}` diterima dengan `campaign_id` yang valid, THE TimeAnalysis_Endpoint SHALL mengembalikan HTTP 200 dengan field `campaign_id`, `histogram`, `stats`, `channel_filter`, dan `region_filter`.
2. WHEN `campaign_id` kosong atau tidak disertakan, THE TimeAnalysis_Endpoint SHALL mengembalikan HTTP 400.
3. THE field `histogram` SHALL berisi tepat 7 bins dengan `range_start` dan `range_end` mengikuti pola [0-7, 7-14, 14-21, 21-30, 30-60, 60-90, 90+].
4. THE field `stats` SHALL mengandung `min_days`, `max_days`, `mean_days`, `median_days`, dan `total_take_up` — nilai statistik tersebut SHALL non-negatif dan `max_days` SHALL lebih besar atau sama dengan `min_days`.
5. WHEN query param `channel` diberikan, THE TimeAnalysis_Endpoint SHALL memfilter data mock berdasarkan `media_blasting` yang cocok sebelum menghitung histogram dan statistik.
6. WHEN query param `region` diberikan, THE TimeAnalysis_Endpoint SHALL memfilter data mock berdasarkan `wilayah` yang cocok sebelum menghitung histogram dan statistik.
7. WHEN campaign_id tidak ditemukan dalam Mock_Data_Store atau tidak memiliki data take-up, THE TimeAnalysis_Endpoint SHALL mengembalikan HTTP 200 dengan pesan `"Belum ada data take up untuk campaign ini"`.

---

### Requirement 5: Regional Performance Endpoint

**User Story:** Sebagai developer yang menguji halaman performa regional, saya ingin RegionalPerformance_Endpoint mengembalikan data per-wilayah dari data mock, sehingga frontend dapat merender peta dan ranking regional secara lokal.

#### Acceptance Criteria

1. WHEN request `GET /api/campaigns/regional/{campaign_id}` diterima, THE RegionalPerformance_Endpoint SHALL mengembalikan HTTP 200 dengan field `campaign_id`, `regions`, `selected_region_trend`, dan `flag_program_filter`.
2. THE field `regions` SHALL berisi list per-wilayah yang masing-masing mengandung `wilayah`, `leads_count`, `take_up_count`, `take_up_rate`, dan `avg_transaction_value`.
3. THE field `regions` SHALL diurutkan berdasarkan `take_up_rate` secara descending.
4. WHEN query param `flag_program` diberikan, THE RegionalPerformance_Endpoint SHALL menyaring data mock ke records dengan `flag_program` yang cocok.
5. WHEN query param `selected_region` diberikan sebagai integer tetapi tidak ada data trend mingguan untuk wilayah tersebut, THE RegionalPerformance_Endpoint SHALL mengisi `selected_region_trend` dengan list kosong `[]`.
6. WHEN query param `selected_region` diberikan sebagai integer dan data tersedia, THE RegionalPerformance_Endpoint SHALL mengisi `selected_region_trend` dengan maksimal 8 data points mingguan untuk wilayah tersebut.
6. WHEN query param `selected_region` tidak diberikan atau Mock_Data_Store tidak memiliki data untuk campaign tersebut, THE RegionalPerformance_Endpoint SHALL mengembalikan HTTP 200 dengan `regions` berupa list kosong dan pesan `"Data regional tidak tersedia untuk campaign ini"`.

---

### Requirement 6: Customer Criteria Endpoint

**User Story:** Sebagai developer yang menguji halaman kriteria nasabah, saya ingin CustomerCriteria_Endpoint mengembalikan distribusi atribut demografis dari data mock, sehingga frontend dapat merender breakdown nasabah secara lokal.

#### Acceptance Criteria

1. WHEN request `GET /api/campaigns/customer-criteria/{campaign_id}` diterima, THE CustomerCriteria_Endpoint SHALL mengembalikan HTTP 200 dengan field `campaign_id`, `distributions`, `available_attributes`, dan `unavailable_attributes`.
2. THE field `distributions` SHALL berisi distribusi untuk minimal 3 atribut pelanggan yang relevan dengan domain bank (misalnya `segment_by_aum`, `range_usia`, `media_blasting`).
3. THE setiap item dalam `distributions` SHALL mengandung field `attribute`, `available`, `items`, dan `unavailable_reason`.
4. THE setiap item dalam `items` SHALL mengandung field `label`, `count`, `percentage`, `take_up_count`, dan `take_up_percentage`.
5. WHEN `campaign_id` kosong, THE CustomerCriteria_Endpoint SHALL mengembalikan HTTP 400 dengan pesan `"Parameter 'campaign_id' wajib diisi."`.
6. WHEN Mock_Data_Store tidak memiliki records untuk `campaign_id` tersebut, THE CustomerCriteria_Endpoint SHALL mengembalikan HTTP 200 dengan pesan `"Tidak ada data karakteristik nasabah untuk campaign ini."`.
7. THE response SHALL tidak mengandung field `cif` atau nilai PII lainnya.

---

### Requirement 7: Similar Campaign Endpoint

**User Story:** Sebagai developer yang menguji fitur rekomendasi, saya ingin SimilarCampaign_Endpoint mengembalikan daftar campaign serupa dari data mock berdasarkan dimensi yang diminta, sehingga frontend dapat merender rekomendasi secara lokal.

#### Acceptance Criteria

1. WHEN request `POST /api/campaigns/similar` diterima dengan body yang valid, THE SimilarCampaign_Endpoint SHALL mengembalikan HTTP 200 dengan field `similar_campaigns` dan `learning_summary`.
2. WHEN body tidak mengandung `reference_campaign_id`, THE SimilarCampaign_Endpoint SHALL mengembalikan HTTP 400 dengan pesan `"reference_campaign_id is required and must be non-empty."`.
3. WHEN `dimensions` kosong atau tidak disertakan, THE SimilarCampaign_Endpoint SHALL mengembalikan HTTP 400 dengan pesan `"dimensions is required and must contain at least one value."`.
4. WHEN `dimensions` mengandung nilai selain `"media_blasting"`, `"jenis_leads"`, atau `"flag_program"`, THE SimilarCampaign_Endpoint SHALL mengembalikan HTTP 400 yang menyebutkan nilai tidak valid dan nilai yang diperbolehkan.
5. THE field `similar_campaigns` SHALL berisi campaign-campaign yang berbagi minimal satu dimensi dengan reference campaign, diurutkan berdasarkan `dimension_count` descending kemudian `take_up_rate` descending sebagai tiebreaker.
6. WHEN parameter `limit` diberikan, THE SimilarCampaign_Endpoint SHALL membatasi jumlah hasil maksimal `min(limit, 20)`.
7. WHEN tidak ada campaign serupa ditemukan, THE SimilarCampaign_Endpoint SHALL mengembalikan HTTP 200 dengan `similar_campaigns` berupa list kosong dan pesan `"Tidak ada campaign serupa ditemukan. Coba perluas dimensi pencarian."`.

---

### Requirement 8: Export Endpoint

**User Story:** Sebagai developer yang menguji fitur ekspor, saya ingin Export_Endpoint menghasilkan file CSV/Excel/PDF yang dapat diunduh secara lokal tanpa memerlukan S3, sehingga saya bisa memverifikasi alur ekspor end-to-end di lokal.

#### Acceptance Criteria

1. WHEN request `POST /api/export` diterima dengan body valid dan `format: "csv"`, THE Export_Endpoint SHALL mengembalikan HTTP 200 dengan body yang mengandung field `status: "completed"` dan `download_url` berupa URL valid.
2. WHEN request `POST /api/export` diterima dengan body valid dan `format: "excel"`, THE Export_Endpoint SHALL mengembalikan HTTP 200 dengan body yang mengandung `status: "completed"` dan `download_url` yang dapat diakses untuk mengunduh file `.xlsx`.
3. WHEN request `POST /api/export` diterima dengan body valid dan `format: "pdf"`, THE Export_Endpoint SHALL mengembalikan HTTP 200 dengan body yang mengandung `status: "completed"` dan `download_url` yang dapat diakses untuk mengunduh file `.pdf`.
4. THE `download_url` untuk mode lokal SHALL berupa path relatif seperti `/exports/{filename}` yang dapat diakses via `GET /exports/{filename}` pada Local_Server (menggantikan presigned S3 URL).
5. WHEN `format` bernilai selain `"pdf"`, `"excel"`, atau `"csv"`, THE Export_Endpoint SHALL mengembalikan HTTP 400 dengan pesan yang menyebutkan format yang tidak valid.
6. WHEN body request kosong atau bukan JSON valid, THE Export_Endpoint SHALL mengembalikan HTTP 400.
7. THE file CSV yang dihasilkan SHALL menyertakan baris metadata (source, period, filters) di bagian atas file sebagai komentar `#`.

---

### Requirement 9: Mock Data Store

**User Story:** Sebagai developer, saya ingin data dummy yang digunakan oleh local server bersifat realistis dan representatif untuk domain kampanye bank, sehingga saya bisa memverifikasi logika frontend dengan data yang menyerupai kondisi produksi.

#### Acceptance Criteria

1. THE Mock_Data_Store SHALL menyediakan minimal 5 campaign ID unik (`C001`–`C005`) dengan `nama_program` yang representatif untuk domain bank (contoh: `"Cashback QRIS Agustus 2024"`, `"Migrasi Biaya Admin Q3"`).
2. THE setiap campaign dalam Mock_Data_Store SHALL memiliki records leads dengan variasi pada: `flag_program`, `media_blasting`, `wilayah` (minimal 3 wilayah berbeda), `jenis_leads`, `segment_by_aum`, `range_usia`, dan `take_up_flag`.
3. THE Mock_Data_Store SHALL tidak mengandung field `cif` atau nilai PII lainnya dalam data yang dikembalikan melalui API.
4. THE data dummy untuk CampaignOverview_Endpoint SHALL menghasilkan `take_up_rate` antara 5% dan 35% — rentang yang realistis untuk kampanye bank Indonesia.
5. THE Mock_Data_Store SHALL menyediakan data untuk SimilarCampaign_Endpoint berupa minimal 3 pasang campaign yang berbagi setidaknya satu dimensi (`media_blasting`, `jenis_leads`, atau `flag_program`).
6. THE Mock_Data_Store SHALL menyediakan data time-analysis dengan distribusi `time_to_take_up_days` yang realistis — mayoritas take-up dalam 0–30 hari pertama.

---

### Requirement 10: Isolasi dari Kode Production

**User Story:** Sebagai developer, saya ingin memastikan local server tidak mengubah Lambda handlers yang ada, sehingga penambahan fitur ini tidak menimbulkan risiko pada kode production.

#### Acceptance Criteria

1. THE Local_Server SHALL ditempatkan di direktori `backend/local_server/` yang terpisah dari `backend/lambdas/`.
2. THE Local_Server SHALL tidak mengimport atau memodifikasi `Lambda_Handler` manapun secara langsung.
3. THE Local_Server MAY mengimport modul dari `backend/shared/` (calculations, models, pii_filter, filters, sorting) untuk reuse logika bisnis yang murni (non-AWS).
4. THE Local_Server SHALL tidak mengimport `shared/athena_client.py` atau `shared/auth.py` — modul yang memiliki dependency ke AWS SDK.
5. WHERE project menggunakan npm, THE npm script `dev:backend` di `package.json` root SHALL tersedia untuk menjalankan Local_Server.
6. THE requirements untuk Local_Server (FastAPI, uvicorn) SHALL ditambahkan ke `backend/requirements-dev.txt`, bukan ke `backend/requirements.txt` (production dependencies).
