# Requirements Document

## Introduction

Campaign Insight Generator adalah dashboard analitik yang mengintegrasikan histori campaign pemasaran menjadi insight bisnis yang dapat dimanfaatkan kembali. Sistem ini membantu Divisi Bisnis (Campaign Owner) menyusun kriteria campaign berikutnya berdasarkan data historis, serta membantu Divisi Data dalam memantau efektivitas campaign. Tujuan utamanya adalah memangkas SLA penyediaan leads dari ±3 hari menjadi ≤1 hari dengan mengurangi revisi request melalui ketersediaan insight berbasis data.

---

## Glossary

- **Dashboard**: Antarmuka visual utama Campaign Insight Generator yang menampilkan ringkasan dan analisis campaign.
- **Campaign**: Program pemasaran yang dijalankan oleh Divisi Bisnis menggunakan leads yang disediakan oleh Divisi Data.
- **Campaign Owner**: Pengguna dari Divisi Bisnis yang bertanggung jawab atas pelaksanaan campaign.
- **Leads**: Data nasabah yang memenuhi kriteria target campaign dan disiapkan oleh Divisi Data.
- **Take Up**: Kondisi di mana nasabah yang menjadi target leads berhasil melakukan transaksi atau mengambil produk yang ditawarkan dalam campaign.
- **Take Up Rate**: Persentase leads yang melakukan take up dari total leads yang diberikan, dihitung dengan formula `(total take up ÷ total leads) × 100%`.
- **Monitoring_Report**: Laporan hasil campaign yang disiapkan oleh Divisi Data setelah campaign selesai.
- **SLA**: Service Level Agreement — target waktu penyediaan leads, saat ini ±3 hari, target ≤1 hari.
- **Region**: Wilayah geografis tempat campaign dilaksanakan (misalnya: Kantor Wilayah atau area distribusi tertentu).
- **Campaign_Filter**: Parameter yang digunakan pengguna untuk menyaring data campaign yang ditampilkan (berdasarkan periode, produk, region, channel, dll).
- **Similar_Campaign**: Campaign di masa lalu yang memiliki kesamaan pada dimensi tertentu (produk, segment, region, atau channel) dengan campaign yang sedang dievaluasi.
- **Divisi_Bisnis**: Unit bisnis di Kantor Pusat yang bertindak sebagai campaign owner dan pengguna utama dashboard.
- **Divisi_Data**: Unit yang bertanggung jawab atas penyediaan data leads dan monitoring.
- **PII**: Personally Identifiable Information — informasi yang dapat mengidentifikasi individu nasabah secara langsung, mencakup nama lengkap, nomor rekening, nomor identitas, dan alamat lengkap.

---

## Requirements

### Requirement 1: Campaign Overview

**User Story:** Sebagai Campaign Owner dari Divisi Bisnis, saya ingin melihat ringkasan performa seluruh campaign yang pernah dijalankan, agar saya dapat memahami gambaran besar efektivitas campaign secara keseluruhan.

#### Acceptance Criteria

1. WHEN Campaign Owner membuka Dashboard, THE Dashboard SHALL menampilkan ringkasan performa campaign dengan periode default 3 bulan terakhir yang mencakup total leads, total take up, dan take up rate agregat dihitung sebagai `(total take up ÷ total leads) × 100%` dari seluruh campaign dalam periode tersebut.
2. WHEN Campaign Owner menerapkan Campaign_Filter berdasarkan periode waktu, THE Dashboard SHALL memperbarui seluruh metrik Campaign Overview sesuai periode yang dipilih dalam waktu tidak lebih dari 5 detik.
3. WHEN Campaign Owner menerapkan Campaign_Filter berdasarkan produk atau sub-produk, THE Dashboard SHALL menampilkan hanya data campaign yang berkaitan dengan produk atau sub-produk tersebut dan memperbarui seluruh metrik Campaign Overview.
4. WHEN Campaign Owner menerapkan Campaign_Filter berdasarkan channel distribusi, THE Dashboard SHALL menampilkan data campaign yang dijalankan melalui channel tersebut dan memperbarui seluruh metrik Campaign Overview.
5. WHEN Campaign Owner menerapkan kombinasi dua atau lebih Campaign_Filter secara bersamaan, THE Dashboard SHALL menampilkan data yang memenuhi semua filter secara AND (irisan), bukan OR.
6. IF data campaign tidak tersedia untuk filter yang dipilih, THEN THE Dashboard SHALL menampilkan pesan yang menyatakan tidak ada data untuk filter tersebut beserta daftar filter yang sedang aktif.
7. WHEN Campaign Owner memilih periode pada Campaign_Filter, THE Dashboard SHALL menampilkan trend take up rate secara time-series dengan granularitas mingguan untuk periode ≤3 bulan dan granularitas bulanan untuk periode >3 bulan.

---

### Requirement 2: Campaign Comparison

**User Story:** Sebagai Campaign Owner dari Divisi Bisnis, saya ingin membandingkan performa antar campaign yang berbeda, agar saya dapat mengidentifikasi campaign mana yang paling efektif dan menggunakan pembelajaran tersebut untuk menyusun campaign berikutnya.

#### Acceptance Criteria

1. WHEN Campaign Owner memilih dua atau lebih campaign untuk dibandingkan, THE Dashboard SHALL menampilkan tabel perbandingan yang memuat metrik: total leads, total take up, take up rate, total nilai transaksi, dan durasi campaign dalam hari kalender untuk setiap campaign yang dipilih.
2. WHEN Campaign Owner memilih campaign untuk dibandingkan, THE Dashboard SHALL menampilkan bar chart berdampingan yang membandingkan kelima metrik utama (total leads, total take up, take up rate, total nilai transaksi, durasi campaign) antar campaign yang dipilih.
3. THE Dashboard SHALL memungkinkan Campaign Owner memilih minimal 2 dan maksimal 5 campaign untuk dibandingkan dalam satu tampilan.
4. WHEN Campaign Owner memilih atribut perbandingan (produk, region, atau channel), THE Dashboard SHALL mengelompokkan dan menyortir hasil perbandingan berdasarkan atribut yang dipilih secara ascending.
5. IF Campaign Owner mencoba memilih campaign ke-6 atau lebih, THEN THE Dashboard SHALL memblokir pilihan tersebut, menampilkan pesan batas maksimal 5 campaign, dan mempertahankan 5 campaign yang sudah dipilih sebelumnya.

---

### Requirement 3: Time to Take Up Analysis

**User Story:** Sebagai Campaign Owner dari Divisi Bisnis, saya ingin mengetahui pola waktu dari distribusi leads hingga terjadinya take up, agar saya dapat menentukan durasi dan waktu optimal pelaksanaan campaign berikutnya.

#### Acceptance Criteria

1. WHEN Campaign Owner membuka halaman Time to Take Up Analysis untuk sebuah campaign, THE Dashboard SHALL menampilkan histogram distribusi waktu dalam hari kalender dari tanggal leads didistribusikan hingga tanggal take up terjadi.
2. WHEN Campaign Owner memilih sebuah campaign pada halaman Time to Take Up Analysis, THE Dashboard SHALL menampilkan nilai median, rata-rata, minimum, dan maksimum waktu take up dalam hari kalender untuk campaign tersebut.
3. WHEN Campaign Owner memilih satu channel distribusi pada halaman Time to Take Up Analysis, THE Dashboard SHALL menampilkan histogram dan statistik distribusi waktu take up yang spesifik untuk channel tersebut.
4. WHEN Campaign Owner memilih satu Region pada halaman Time to Take Up Analysis, THE Dashboard SHALL menampilkan histogram dan statistik distribusi waktu take up yang spesifik untuk region tersebut.
5. IF tidak ada data take up yang tercatat untuk campaign yang dipilih, THEN THE Dashboard SHALL menampilkan pesan yang menyatakan belum ada data take up untuk campaign tersebut.
6. IF Campaign Owner menerapkan filter channel atau region dan tidak ada data take up untuk kombinasi tersebut, THEN THE Dashboard SHALL menampilkan pesan yang menyatakan tidak ada data take up untuk filter tersebut dan menyarankan Campaign Owner mengubah filter.

---

### Requirement 4: Regional Performance

**User Story:** Sebagai Campaign Owner dari Divisi Bisnis, saya ingin melihat performa campaign per wilayah/region, agar saya dapat mengidentifikasi region yang paling responsif dan menyesuaikan strategi distribusi leads pada campaign berikutnya.

#### Acceptance Criteria

1. WHEN Campaign Owner membuka halaman Regional Performance untuk sebuah campaign, THE Dashboard SHALL menampilkan data performa untuk setiap Region dengan minimal 1 lead, mencakup jumlah leads, jumlah take up, dan take up rate dihitung sebagai `(jumlah take up ÷ jumlah leads) × 100%`.
2. WHEN Campaign Owner membuka halaman Regional Performance untuk sebuah campaign, THE Dashboard SHALL menampilkan tabel atau chart perbandingan performa antar Region yang diurutkan berdasarkan take up rate dari tertinggi ke terendah, dengan posisi pertama adalah Region dengan take up rate tertinggi.
3. WHEN Campaign Owner memilih sebuah Region secara spesifik, THE Dashboard SHALL menampilkan detail performa Region tersebut termasuk tren take up rate mingguan untuk 8 periode terakhir yang tersedia.
4. WHEN Campaign Owner menerapkan Campaign_Filter berdasarkan produk pada halaman Regional Performance, THE Dashboard SHALL menghitung ulang jumlah leads, jumlah take up, dan take up rate untuk setiap Region berdasarkan campaign produk yang difilter.
5. IF data regional tidak tersedia untuk campaign yang dipilih, THEN THE Dashboard SHALL menampilkan pesan yang menjelaskan bahwa data regional untuk campaign tersebut tidak tersedia.

---

### Requirement 5: Customer Criteria Analysis

**User Story:** Sebagai Campaign Owner dari Divisi Bisnis, saya ingin menganalisis karakteristik nasabah yang melakukan take up, agar saya dapat menyempurnakan kriteria target leads untuk campaign berikutnya dan mengurangi revisi request kepada Divisi Data.

#### Acceptance Criteria

1. WHEN Campaign Owner membuka halaman Customer Criteria Analysis untuk sebuah campaign, THE Dashboard SHALL menampilkan distribusi persentase karakteristik demografis nasabah yang melakukan take up, mencakup minimal: segmen nasabah, rentang usia, dan wilayah domisili.
2. WHEN Campaign Owner membuka halaman Customer Criteria Analysis untuk sebuah campaign, THE Dashboard SHALL menampilkan distribusi persentase karakteristik finansial nasabah yang melakukan take up, mencakup minimal: produk yang dimiliki dan kategori saldo/nilai transaksi.
3. WHEN Campaign Owner membuka halaman Customer Criteria Analysis untuk sebuah campaign, THE Dashboard SHALL menampilkan perbandingan persentase per kelompok karakteristik antara nasabah yang melakukan take up dan nasabah yang tidak melakukan take up dari total leads campaign yang sama.
4. WHEN Campaign Owner memilih sebuah atribut karakteristik nasabah, THE Dashboard SHALL menampilkan breakdown take up rate dihitung sebagai `(jumlah take up ÷ jumlah leads) × 100%` untuk setiap nilai dalam atribut karakteristik yang dipilih.
5. IF data karakteristik nasabah tidak tersedia atau hanya tersedia sebagian untuk campaign yang dipilih, THEN THE Dashboard SHALL menampilkan pesan yang menjelaskan atribut mana yang tidak tersedia dan menampilkan data untuk atribut yang tersedia.

---

### Requirement 6: Similar Campaign Comparison

**User Story:** Sebagai Campaign Owner dari Divisi Bisnis, saya ingin melihat perbandingan antara campaign yang sedang saya rencanakan dengan campaign serupa yang pernah dijalankan di masa lalu, agar saya dapat menggunakan pembelajaran dari campaign terdahulu sebagai referensi untuk menyusun kriteria campaign baru.

#### Acceptance Criteria

1. WHEN Campaign Owner memilih sebuah campaign sebagai referensi, THE Dashboard SHALL menampilkan daftar maksimal 20 Similar_Campaign yang diurutkan berdasarkan jumlah dimensi yang cocok secara descending, dengan take up rate sebagai tiebreaker untuk kampanye dengan jumlah dimensi cocok yang sama.
2. WHEN Campaign Owner memilih dimensi kesamaan secara spesifik dari empat dimensi yang tersedia (produk, segmen nasabah, Region, atau channel distribusi), THE Dashboard SHALL memperbarui daftar Similar_Campaign sesuai dimensi yang dipilih dan mengosongkan pilihan Similar_Campaign yang sebelumnya dipilih.
3. WHEN Campaign Owner memilih sebuah Similar_Campaign dari daftar, THE Dashboard SHALL menampilkan perbandingan side-by-side yang mencakup: (a) metrik performa: take up rate, jumlah leads, jumlah take up, total nilai transaksi; (b) karakteristik nasabah take up: distribusi usia, segmen, dan produk; (c) distribusi regional dalam persentase; (d) distribusi waktu take up dalam hari.
4. WHEN Campaign Owner memilih sebuah Similar_Campaign dari daftar, THE Dashboard SHALL menampilkan ringkasan pembelajaran yang mencakup: take up rate dalam format dua desimal persen, segmen nasabah dengan take up terbanyak, dan Region dengan jumlah take up absolut tertinggi.
5. IF tidak ditemukan Similar_Campaign berdasarkan dimensi yang dipilih, THEN THE Dashboard SHALL menampilkan pesan yang menyatakan tidak ada campaign serupa ditemukan dan menyarankan agar Campaign Owner memperluas dimensi pencarian.

---

### Requirement 7: Akses dan Keamanan Data

**User Story:** Sebagai anggota Divisi Data, saya ingin memastikan bahwa data campaign dan karakteristik nasabah hanya dapat diakses oleh pengguna yang berwenang, agar kerahasiaan data nasabah terjaga sesuai kebijakan perusahaan.

#### Acceptance Criteria

1. WHEN pengguna mengakses Dashboard, THE Dashboard SHALL memverifikasi identitas pengguna melalui mekanisme autentikasi sebelum menampilkan data apapun.
2. WHILE pengguna aktif menggunakan Dashboard, THE Dashboard SHALL mempertahankan sesi autentikasi pengguna selama tidak melebihi 8 jam sejak login; setelah batas waktu tersebut sesi berakhir otomatis dan pengguna diarahkan ke halaman login.
3. IF pengguna tidak terautentikasi mencoba mengakses halaman Dashboard, THEN THE Dashboard SHALL mengalihkan pengguna ke halaman login dan menampilkan pesan yang menjelaskan bahwa akses memerlukan autentikasi.
4. THE Dashboard SHALL mencatat log akses setiap pengguna beserta user ID, timestamp, dan halaman yang diakses untuk keperluan audit.
5. WHEN pengguna dengan peran Divisi_Bisnis mengakses Dashboard, THE Dashboard SHALL menampilkan data campaign tanpa menampilkan PII nasabah secara individual, di mana PII mencakup nama lengkap, nomor rekening, nomor identitas, dan alamat lengkap.
6. WHEN pengguna dengan peran Divisi_Data mengakses Dashboard, THE Dashboard SHALL menampilkan semua data analitik campaign termasuk metrik agregat nasabah, namun tetap tidak menampilkan PII nasabah secara individual.

---

### Requirement 8: Ekspor dan Distribusi Data

**User Story:** Sebagai Campaign Owner dari Divisi Bisnis, saya ingin mengekspor data insight dari dashboard, agar saya dapat menggunakannya dalam presentasi, dokumentasi campaign brief, atau berbagi dengan stakeholder yang relevan.

#### Acceptance Criteria

1. WHEN Campaign Owner memilih opsi ekspor pada halaman yang menyediakan fitur ekspor, THE Dashboard SHALL menghasilkan file ekspor dalam format yang dipilih (minimal: PDF dan Excel/CSV) yang berisi data yang difilter oleh Campaign_Filter aktif pada halaman tersebut.
2. WHEN Campaign Owner mengekspor data, THE Dashboard SHALL menyertakan metadata dalam file ekspor yang mencakup: nama filter aktif, rentang waktu yang dipilih, dan nama halaman asal ekspor.
3. WHEN proses ekspor file selesai dalam waktu kurang dari 30 detik, THE Dashboard SHALL menampilkan notifikasi in-app dan memulai unduhan file secara otomatis.
4. IF proses ekspor tidak selesai dalam 30 detik, THEN THE Dashboard SHALL membatalkan proses ekspor dan menampilkan pesan timeout beserta opsi untuk mencoba kembali.
5. IF proses ekspor gagal karena alasan teknis selain timeout, THEN THE Dashboard SHALL menampilkan pesan error yang menjelaskan penyebab kegagalan, membatalkan sesi ekspor, dan menyediakan opsi retry untuk pengguna.
