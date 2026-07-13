# Dokumen Persyaratan: Local Development Backend Server

## Introduction

Fitur ini membangun sebuah server backend lokal menggunakan FastAPI yang dapat berjalan sepenuhnya tanpa koneksi AWS. Server ini menggantikan tujuh Lambda handler (API Gateway + Lambda + Athena/DynamoDB) dengan implementasi lokal yang setara, sehingga developer dan tim demo dapat menjalankan Campaign Insight Generator secara penuh di `localhost` tanpa dependensi cloud.

Server lokal menggunakan SQLite sebagai pengganti Athena, data seed sintetis yang realistis, dan autentikasi mock berbasis JWT lokal sebagai pengganti Cognito.

## Glosarium

- **Server Lokal**: Proses FastAPI yang berjalan di mesin pengembang pada port 8000 secara default.
- **SQLite_Client**: Modul yang mengeksekusi query SQL terhadap database SQLite lokal.
- **Seed_Generator**: Modul yang membuat dan mengisi tabel SQLite dengan data kampanye sintetis yang realistis.
- **Auth_Handler**: Modul yang menangani login dan validasi JWT tanpa Cognito.
- **JWT_Token**: JSON Web Token lokal yang digunakan sebagai pengganti token Cognito.
- **Endpoint**: Satu path URL HTTP yang ditangani oleh sebuah FastAPI router.
- **CORS**: Cross-Origin Resource Sharing — mekanisme browser yang mengizinkan `localhost:3000` memanggil `localhost:8000`.
- **flag_program**: Jenis program kampanye; nilai valid: `PROGRAM QRIS`, `PROGRAM BIAYA ADMIN`.
- **media_blasting**: Saluran distribusi leads; nilai valid: `wa`, `digisales`, `telesales`, `email`, `push notif`, `sms`.
- **wilayah**: Kode wilayah berupa integer 1–17.
- **jenis_leads**: Tujuan leads, misalnya `Migrasi`, `Aktivasi`, `Upgrade`.
- **take_up_flag**: Status konversi nasabah; nilai: `YES` atau `NO`.
- **cif**: Customer Identification File — kode unik nasabah, bersifat PII dan tidak boleh dikembalikan di respons API.
- **take_up_rate**: Persentase konversi = (total_take_up / total_leads) × 100.

---

## Requirements

### Requirement 1: Infrastruktur Server dan CORS

**User Story:** Sebagai developer frontend, saya ingin server backend lokal dapat berjalan dengan satu perintah dan menerima request dari `localhost:3000`, sehingga saya dapat mengembangkan frontend tanpa konfigurasi jaringan tambahan.

#### Kriteria Penerimaan

1. THE Server Lokal SHALL menyediakan titik masuk tunggal melalui file `local_dev/server.py` yang dapat dijalankan dengan perintah `uvicorn local_dev.server:app --reload`.
2. THE Server Lokal SHALL mengaktifkan CORS untuk origin `http://localhost:3000` pada seluruh endpoint, mengizinkan metode GET, POST, PUT, DELETE, OPTIONS, dan header `Authorization`, `Content-Type`.
3. WHEN Server Lokal menerima request OPTIONS (preflight), THE Server Lokal SHALL mengembalikan respons HTTP 200 dengan header CORS yang benar.
4. THE Server Lokal SHALL menjalankan semua tujuh endpoint di bawah prefix path `/api`.
5. THE Server Lokal SHALL menyediakan endpoint health-check `GET /health` yang mengembalikan `{"status": "ok"}` tanpa autentikasi.
6. IF `local_dev/campaign.db` belum ada saat server pertama kali dijalankan, THEN THE Seed_Generator SHALL membuat database SQLite dan mengisinya dengan data sampel secara otomatis sebelum server mulai menerima request.

---

### Requirement 2: Database SQLite dan Skema Data

**User Story:** Sebagai developer, saya ingin data kampanye disimpan dalam SQLite lokal dengan skema yang mencerminkan domain kampanye bank yang sesungguhnya, sehingga query lokal menghasilkan data yang realistis dan konsisten.

#### Kriteria Penerimaan

1. THE SQLite_Client SHALL membuat tabel `leads` dengan kolom: `cif` (TEXT), `nama_program` (TEXT), `jenis_leads` (TEXT), `media_blasting` (TEXT), `periode_start` (TEXT), `flag_program` (TEXT), `wilayah` (INTEGER), `cabang` (INTEGER), `outlet` (INTEGER), `segment_crs` (TEXT), `segment_by_aum` (TEXT), `segment_wondr` (TEXT), `segment_div_owner` (TEXT), `range_usia` (TEXT), `range_saldo_tab` (REAL), `avg_aum_3_bln` (REAL), `potensi_money` (REAL), `take_up_flag` (TEXT DEFAULT 'NO'), `take_up_date` (TEXT), `time_to_take_up_days` (INTEGER), `total_transaction_value` (REAL).
2. THE SQLite_Client SHALL membuat tabel `campaigns` dengan kolom: `campaign_id` (TEXT PRIMARY KEY), `nama_program` (TEXT), `flag_program` (TEXT), `jenis_leads` (TEXT), `media_blasting` (TEXT), `wilayah` (INTEGER), `start_date` (TEXT), `end_date` (TEXT), `total_leads` (INTEGER), `total_take_up` (INTEGER), `take_up_rate` (REAL), `total_transaction_value` (REAL), `duration_days` (INTEGER).
3. THE Seed_Generator SHALL mengisi tabel `leads` dengan minimal 5.000 baris data sintetis yang mencakup semua kombinasi: `flag_program` (`PROGRAM QRIS`, `PROGRAM BIAYA ADMIN`), `media_blasting` (`wa`, `digisales`, `telesales`), dan `wilayah` 1–17.
4. THE Seed_Generator SHALL mengisi tabel `campaigns` dengan minimal 20 kampanye unik yang mencakup berbagai `flag_program`, `media_blasting`, rentang tanggal berbeda, dan `wilayah` yang beragam.
5. THE Seed_Generator SHALL menghasilkan nilai `take_up_rate` antara 5%–40% per kampanye, dengan distribusi yang realistis (tidak semua kampanye identik).
6. THE Seed_Generator SHALL memastikan kolom `cif` diisi dengan nilai unik per baris tetapi TIDAK dikembalikan di respons API manapun.
7. WHEN `Seed_Generator` dijalankan ulang, THE Seed_Generator SHALL menghapus dan membuat ulang data yang ada sehingga state database deterministik.

---

### Requirement 3: Autentikasi Mock

**User Story:** Sebagai developer frontend, saya ingin login menggunakan username dan password sederhana dan menerima JWT token, sehingga saya dapat menguji alur autentikasi tanpa akun AWS Cognito.

#### Kriteria Penerimaan

1. THE Auth_Handler SHALL menyediakan endpoint `POST /api/auth/login` yang menerima body JSON `{"username": string, "password": string}`.
2. WHEN kredensial `{"username": "admin", "password": "admin123"}` dikirim ke endpoint login, THE Auth_Handler SHALL mengembalikan respons HTTP 200 berisi `{"access_token": "<jwt>", "token_type": "bearer", "expires_in": 3600}`.
3. WHEN kredensial `{"username": "demo", "password": "demo123"}` dikirim ke endpoint login, THE Auth_Handler SHALL mengembalikan respons HTTP 200 berisi access token yang valid.
4. WHEN kredensial yang tidak valid dikirim ke endpoint login, THE Auth_Handler SHALL mengembalikan respons HTTP 401 berisi `{"detail": "Username atau password tidak valid"}`.
5. THE Auth_Handler SHALL menyediakan endpoint `GET /api/auth/session` yang memvalidasi JWT token dari header `Authorization: Bearer <token>` dan mengembalikan `{"username": string, "role": "admin", "expires_at": string}`.
6. WHEN request ke endpoint terproteksi tidak menyertakan header `Authorization`, THE Server Lokal SHALL mengembalikan HTTP 401.
7. WHEN JWT token yang kedaluwarsa atau tidak valid dikirim ke endpoint terproteksi, THE Server Lokal SHALL mengembalikan HTTP 401.
8. THE Auth_Handler SHALL menandatangani JWT menggunakan algoritma HS256 dengan secret key yang dikonfigurasi melalui variabel lingkungan `LOCAL_JWT_SECRET` (default: `local-dev-secret`).

---

### Requirement 4: Endpoint Campaign Overview

**User Story:** Sebagai pengguna dashboard, saya ingin melihat metrik ringkasan kampanye secara agregat, sehingga saya dapat memahami performa keseluruhan dalam rentang waktu tertentu.

#### Kriteria Penerimaan

1. THE Server Lokal SHALL menyediakan endpoint `GET /api/campaigns/overview` yang menerima query parameter opsional: `start_date` (yyyy-mm-dd), `end_date` (yyyy-mm-dd), `flag_program` (csv), `media_blasting` (csv), `wilayah` (csv integer), `jenis_leads` (csv).
2. WHEN endpoint overview dipanggil, THE SQLite_Client SHALL mengembalikan agregat: `total_leads`, `total_take_up`, `take_up_rate`, `total_campaigns`, dan daftar `trend` per periode dengan field: `period_start`, `period_end`, `take_up_rate`, `total_leads`, `total_take_up`.
3. WHEN parameter `start_date` atau `end_date` tidak disertakan, THE Server Lokal SHALL menggunakan default 90 hari terakhir dari tanggal hari ini.
4. WHEN parameter filter diberikan (misalnya `flag_program=PROGRAM QRIS`), THE SQLite_Client SHALL memfilter hasil hanya untuk data yang sesuai.
5. IF tidak ada data yang cocok dengan filter yang diberikan, THEN THE Server Lokal SHALL mengembalikan HTTP 200 berisi `{"message": "Tidak ada data untuk filter yang dipilih", "filters": [...]}`.
6. THE Server Lokal SHALL menyertakan field `filters` di respons yang mendeskripsikan filter aktif yang sedang diterapkan.
7. THE Server Lokal SHALL TIDAK mengembalikan nilai field `cif` dalam respons overview.

---

### Requirement 5: Endpoint Campaign Comparison

**User Story:** Sebagai analis kampanye, saya ingin membandingkan 2 hingga 5 kampanye secara berdampingan, sehingga saya dapat mengevaluasi performa relatif antar kampanye.

#### Kriteria Penerimaan

1. THE Server Lokal SHALL menyediakan endpoint `POST /api/campaigns/comparison` yang menerima body JSON `{"campaign_ids": [string], "group_by": string | null}`.
2. WHEN `campaign_ids` berisi kurang dari 2 ID, THE Server Lokal SHALL mengembalikan HTTP 400 berisi pesan error yang menjelaskan bahwa minimal 2 kampanye harus dipilih.
3. WHEN `campaign_ids` berisi lebih dari 5 ID, THE Server Lokal SHALL mengembalikan HTTP 400 berisi pesan error yang menjelaskan bahwa maksimal 5 kampanye yang dapat dibandingkan.
4. WHEN request comparison valid diterima, THE SQLite_Client SHALL mengembalikan daftar `campaigns` berisi metrik per kampanye: `campaign_id`, `campaign_name`, `flag_program`, `total_leads`, `total_take_up`, `take_up_rate`, `total_transaction_value`, `duration_days`.
5. THE Server Lokal SHALL menyertakan field `comparison_chart` di respons dengan struktur yang kompatibel untuk Chart.js: `{"labels": [...], "datasets": [...]}`.
6. WHEN parameter `group_by` diisi (salah satu dari `flag_program`, `wilayah`, `media_blasting`), THE SQLite_Client SHALL mengurutkan kampanye berdasarkan atribut tersebut secara ascending.

---

### Requirement 6: Endpoint Time Analysis

**User Story:** Sebagai analis kampanye, saya ingin melihat distribusi waktu konversi nasabah (histogram hari ke take-up) untuk sebuah kampanye, sehingga saya dapat memahami kapan nasabah biasanya merespons.

#### Kriteria Penerimaan

1. THE Server Lokal SHALL menyediakan endpoint `GET /api/campaigns/time-analysis/{campaign_id}` yang menerima path parameter `campaign_id` dan query parameter opsional `channel` dan `region`.
2. WHEN endpoint time analysis dipanggil dengan campaign_id yang valid, THE SQLite_Client SHALL mengembalikan histogram dengan 7 bin tetap: `[0-7, 7-14, 14-21, 21-30, 30-60, 60-90, 90+]` dimana setiap bin berisi `range_start`, `range_end`, `count`, dan `percentage`.
3. WHEN endpoint time analysis dipanggil dengan campaign_id yang valid, THE SQLite_Client SHALL mengembalikan statistik deskriptif: `min_days`, `max_days`, `mean_days`, `median_days`, `total_take_up`.
4. WHEN parameter `channel` diberikan, THE SQLite_Client SHALL memfilter data hanya untuk `media_blasting` yang sesuai.
5. WHEN parameter `region` diberikan, THE SQLite_Client SHALL memfilter data hanya untuk `wilayah` yang sesuai.
6. IF tidak ada data take-up untuk `campaign_id` yang diberikan, THEN THE Server Lokal SHALL mengembalikan HTTP 200 berisi `{"message": "Belum ada data take up untuk campaign ini", "campaign_id": "<id>"}`.
7. IF `campaign_id` kosong atau tidak disertakan, THEN THE Server Lokal SHALL mengembalikan HTTP 400.

---

### Requirement 7: Endpoint Regional Performance

**User Story:** Sebagai analis regional, saya ingin melihat performa per wilayah untuk sebuah kampanye beserta tren 8 minggu terakhir, sehingga saya dapat mengidentifikasi wilayah yang membutuhkan perhatian.

#### Kriteria Penerimaan

1. THE Server Lokal SHALL menyediakan endpoint `GET /api/campaigns/regional/{campaign_id}` yang menerima path parameter `campaign_id` dan query parameter opsional `flag_program` dan `selected_region`.
2. WHEN endpoint regional dipanggil dengan campaign_id yang valid, THE SQLite_Client SHALL mengembalikan daftar `regions` yang diurutkan berdasarkan `take_up_rate` secara descending, dimana setiap entri berisi: `wilayah`, `leads_count`, `take_up_count`, `take_up_rate`, `avg_transaction_value`.
3. WHEN parameter `selected_region` diberikan, THE SQLite_Client SHALL mengembalikan field `selected_region_trend` berisi daftar maksimal 8 titik data mingguan dengan field: `week_start`, `leads_count`, `take_up_count`, `take_up_rate`.
4. WHEN parameter `flag_program` diberikan, THE SQLite_Client SHALL memfilter data hanya untuk `flag_program` yang sesuai.
5. IF tidak ada data regional untuk `campaign_id` yang diberikan, THEN THE Server Lokal SHALL mengembalikan HTTP 200 berisi `{"campaign_id": "<id>", "message": "Data regional tidak tersedia untuk campaign ini", "regions": [], "selected_region_trend": null}`.

---

### Requirement 8: Endpoint Customer Criteria

**User Story:** Sebagai analis kampanye, saya ingin melihat distribusi karakteristik demografis dan finansial nasabah untuk sebuah kampanye, sehingga saya dapat memahami profil nasabah yang merespons kampanye.

#### Kriteria Penerimaan

1. THE Server Lokal SHALL menyediakan endpoint `GET /api/campaigns/customer-criteria/{campaign_id}` yang menerima path parameter `campaign_id`.
2. WHEN endpoint customer criteria dipanggil, THE SQLite_Client SHALL mengembalikan distribusi untuk lima atribut: `customer_segment`, `age_group`, `domicile_region`, `product_holding`, `balance_category`.
3. WHEN distribusi untuk sebuah atribut tersedia, THE SQLite_Client SHALL mengembalikan daftar `items` dimana setiap item berisi: `label`, `count`, `percentage`, `take_up_count`, `take_up_percentage`.
4. IF sebuah atribut tidak memiliki data (semua nilai null/kosong), THEN THE Server Lokal SHALL mengembalikan distribusi tersebut dengan `"available": false` dan field `unavailable_reason` berisi pesan deskriptif.
5. THE Server Lokal SHALL TIDAK mengembalikan nilai field `cif` dalam respons customer criteria.
6. IF tidak ada data untuk `campaign_id` yang diberikan, THEN THE Server Lokal SHALL mengembalikan HTTP 200 berisi `{"campaign_id": "<id>", "message": "Tidak ada data karakteristik nasabah untuk campaign ini"}`.

---

### Requirement 9: Endpoint Similar Campaign

**User Story:** Sebagai analis kampanye, saya ingin menemukan kampanye historis yang serupa dengan kampanye referensi berdasarkan dimensi yang saya pilih, sehingga saya dapat belajar dari performa kampanye sebelumnya.

#### Kriteria Penerimaan

1. THE Server Lokal SHALL menyediakan endpoint `POST /api/campaigns/similar` yang menerima body JSON `{"reference_campaign_id": string, "dimensions": [string], "limit": integer | null}`.
2. WHEN request similar campaign valid diterima, THE SQLite_Client SHALL mencari kampanye lain yang cocok berdasarkan dimensi yang diminta (`media_blasting`, `jenis_leads`, dan/atau `flag_program`) dengan membandingkan nilai field tersebut pada tabel `campaigns`.
3. WHEN hasil ditemukan, THE Server Lokal SHALL mengembalikan daftar `similar_campaigns` yang diurutkan berdasarkan jumlah dimensi yang cocok secara descending, kemudian `take_up_rate` secara descending.
4. THE Server Lokal SHALL membatasi hasil maksimal 20 kampanye, atau nilai `limit` jika lebih kecil dari 20.
5. WHEN dimensi yang tidak valid dikirim (bukan salah satu dari `media_blasting`, `jenis_leads`, `flag_program`), THE Server Lokal SHALL mengembalikan HTTP 400 berisi pesan error yang menyebutkan dimensi yang tidak valid.
6. IF tidak ada kampanye serupa ditemukan, THEN THE Server Lokal SHALL mengembalikan HTTP 200 berisi `{"similar_campaigns": [], "message": "Tidak ada campaign serupa ditemukan. Coba perluas dimensi pencarian."}`.

---

### Requirement 10: Endpoint Export

**User Story:** Sebagai pengguna dashboard, saya ingin mengekspor data kampanye dalam format CSV, Excel, atau PDF, sehingga saya dapat melaporkan hasil analisis kepada pimpinan secara offline.

#### Kriteria Penerimaan

1. THE Server Lokal SHALL menyediakan endpoint `POST /api/export` yang menerima body JSON `{"page": string, "format": "pdf" | "excel" | "csv", "filters": [...], "time_range_start": string, "time_range_end": string}`.
2. WHEN format `csv` diminta, THE Server Lokal SHALL menghasilkan file CSV dengan baris metadata di atas (source, period, filters) diikuti baris header dan baris data dari tabel `campaigns`.
3. WHEN format `excel` diminta, THE Server Lokal SHALL menghasilkan file `.xlsx` dengan dua sheet: `Metadata` (filter aktif) dan `Data` (data kampanye).
4. WHEN format `pdf` diminta, THE Server Lokal SHALL menghasilkan file PDF dengan bagian metadata dan bagian data kampanye.
5. WHEN file berhasil dibuat, THE Server Lokal SHALL mengembalikan HTTP 200 berisi `{"status": "completed", "download_url": "<path lokal atau data URL>"}`.
6. WHEN format yang tidak valid dikirim (bukan `pdf`, `excel`, atau `csv`), THE Server Lokal SHALL mengembalikan HTTP 400 berisi pesan error yang menyebutkan format yang didukung.
7. THE Server Lokal SHALL TIDAK memerlukan S3 untuk export — file ditulis ke folder `local_dev/exports/` dan URL yang dikembalikan adalah path lokal yang dapat diakses melalui endpoint file statis FastAPI.

---

### Requirement 11: Kompatibilitas Kontrak API

**User Story:** Sebagai developer frontend, saya ingin server lokal mengembalikan respons dengan struktur JSON yang identik dengan Lambda handler produksi, sehingga tidak ada perubahan kode frontend yang diperlukan saat beralih antara lokal dan AWS.

#### Kriteria Penerimaan

1. THE Server Lokal SHALL mengembalikan respons JSON dengan field yang identik (nama dan tipe data) dengan respons Lambda handler produksi untuk setiap endpoint.
2. THE Server Lokal SHALL menggunakan HTTP status code yang sama dengan Lambda handler produksi: 200 untuk sukses, 400 untuk input tidak valid, 401 untuk tidak terautentikasi, 408 untuk timeout, 500 untuk error server.
3. THE Server Lokal SHALL menggunakan path URL yang identik dengan API Gateway produksi: `/api/campaigns/overview`, `/api/campaigns/comparison`, `/api/campaigns/time-analysis/{id}`, `/api/campaigns/regional/{id}`, `/api/campaigns/customer-criteria/{id}`, `/api/campaigns/similar`, `/api/export`.
4. THE Server Lokal SHALL menerima format request yang identik (query parameters, body JSON) dengan Lambda handler produksi.
5. THE Server Lokal SHALL TIDAK mengembalikan field `cif` dalam respons manapun, konsisten dengan perilaku PII filter produksi.
