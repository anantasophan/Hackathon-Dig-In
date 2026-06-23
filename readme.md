# DIGISALES INSIGHT GENERATOR (DIG-IN)

## Customer Insight Generator untuk Percepatan SLA Campaign dan Peningkatan Efektivitas Penjualan

---

# 1. Executive Summary

Saat ini proses distribusi leads kepada sales dilakukan melalui aplikasi DigiSales sebagai sarana pelaksanaan berbagai campaign pemasaran produk dan program bisnis.

Leads yang didistribusikan umumnya hanya berisi informasi dasar nasabah seperti CIF, nama nasabah, nomor telepon, outlet, segmen, dan nama program. Kondisi ini menyebabkan sales tidak memiliki pemahaman yang memadai mengenai karakteristik, kebutuhan, portofolio produk, maupun histori hubungan nasabah dengan bank.

Di sisi lain, ketika user bisnis membutuhkan informasi tambahan terkait target nasabah, tim pengelola data perlu melakukan proses enrichment dan analisis secara manual yang melibatkan berbagai sumber data. Proses tersebut menyebabkan SLA penyediaan leads berada pada rentang H+3 hingga H+5 hari kerja.

Untuk menjawab tantangan tersebut, diusulkan pengembangan **DigiSales Insight Generator (DIG-IN)**, yaitu sebuah engine yang secara otomatis melakukan customer enrichment dan menghasilkan Customer 360 Insight yang siap digunakan oleh sales maupun user bisnis.

Dengan adanya solusi ini, proses penyediaan leads dapat dilakukan lebih cepat, insight menjadi lebih konsisten, dan sales memperoleh informasi yang lebih komprehensif dalam melakukan pendekatan kepada nasabah.

---

# 2. Background

Divisi kami memiliki tanggung jawab untuk menyediakan target leads nasabah yang akan digunakan oleh sales dalam menjalankan berbagai campaign pemasaran melalui aplikasi DigiSales.

Saat ini data yang dikirimkan ke DigiSales antara lain:

* CIF
* Nama Nasabah
* Nomor HP
* Wilayah/Cabang/Outlet
* Program Campaign
* Produk yang ditawarkan
* Segmen Nasabah

Contoh data yang dikirim:

| Field         |
| ------------- |
| CIF           |
| Nama Customer |
| No HP         |
| Region        |
| Branch        |
| Outlet        |
| Program Name  |
| Product Name  |
| Segment       |

Meskipun target nasabah telah sesuai dengan kriteria campaign, informasi yang diterima sales masih sangat terbatas sehingga sales tidak memiliki gambaran menyeluruh mengenai kondisi nasabah.

Selain itu, ketika user bisnis membutuhkan informasi tambahan mengenai target campaign, proses pengumpulan data masih dilakukan secara manual dengan mengambil data dari berbagai sumber yang berbeda.

Kondisi tersebut menyebabkan:

* SLA penyediaan leads relatif panjang.
* Ketergantungan pada proses manual.
* Insight yang dihasilkan tidak konsisten antar campaign.
* Sales kesulitan melakukan personalisasi penawaran.

---

# 3. Problem Statement

## Problem 1 – Informasi Leads Terbatas

Leads yang diterima sales hanya berisi data dasar nasabah sehingga sales tidak mengetahui:

* Karakteristik nasabah
* Profil finansial
* Produk yang dimiliki
* Riwayat produk
* Aktivitas transaksi
* Potensi kebutuhan nasabah

---

## Problem 2 – Tidak Tersedia Customer 360 View

Informasi nasabah tersebar pada berbagai sumber data seperti:

* CIF Profile
* CASA
* Deposito
* Kredit
* Payroll
* Wealth Management
* Historical Campaign

Sehingga sales harus melakukan pencarian informasi secara mandiri.

---

## Problem 3 – Proses Enrichment Masih Manual

Ketika diperlukan informasi tambahan untuk campaign tertentu, tim data harus melakukan:

* Query tambahan
* Data cleansing
* Data enrichment
* Analisis karakteristik nasabah
* Penyusunan insight campaign

secara manual.

---

## Problem 4 – SLA Penyediaan Leads Belum Optimal

Kondisi saat ini:

* SLA normal: H+3 hari kerja
* Campaign dengan kebutuhan enrichment tambahan: H+5 hari kerja atau lebih

Dampak:

* Campaign terlambat dijalankan
* Time-to-market lebih lama
* Peluang bisnis berpotensi hilang

---

## Problem 5 – Belum Ada Rekomendasi Penawaran

Sales belum memperoleh rekomendasi:

* Produk yang paling relevan
* Potensi cross sell
* Potensi up sell
* Strategi pendekatan nasabah

---

# 4. Root Cause Analysis

Penyebab utama permasalahan adalah:

1. Data nasabah masih tersebar di berbagai sumber.
2. Belum terdapat engine customer enrichment otomatis.
3. Belum tersedia Customer 360 View yang terintegrasi.
4. Analisis campaign masih banyak dilakukan secara manual.
5. Belum terdapat mekanisme Next Best Offer yang terstandarisasi.

---

# 5. Project Overview

## Existing Process

Business User Request

↓

Tim Data Menyiapkan Leads

↓

Pengambilan Data Tambahan (Manual)

↓

Enrichment dan Analisis Manual

↓

Inject Leads ke DigiSales

↓

Sales Melakukan Penawaran

SLA: H+3 sampai H+5

---

## Future Process

Business User Request

↓

Insight Generator

↓

Auto Customer Enrichment

↓

Generate Customer 360 Insight

↓

Inject Leads + Insight ke DigiSales

↓

Sales Melakukan Penawaran

Target SLA: H+1 atau Same Day

---

# 6. Proposed Solution

## DigiSales Insight Generator (DIG-IN)

Sebuah engine otomatis yang mengintegrasikan berbagai sumber data nasabah dan menghasilkan insight yang siap digunakan oleh sales.

---

## Insight 1 – Customer Profile

Contoh:

* Segmen Emerald
* Usia 42 tahun
* Payroll Aktif
* Lama Menjadi Nasabah 8 Tahun

---

## Insight 2 – Product Portfolio

Contoh:

* Tabungan Aktif
* Deposito Aktif
* Kredit Tidak Ada
* Asuransi Tidak Ada

---

## Insight 3 – Financial Behavior

Contoh:

* Average Balance Rp250 Juta
* Frekuensi Transaksi Tinggi
* Payroll Rp18 Juta/Bulan
* Trend AUM Meningkat

---

## Insight 4 – Historical Product

Contoh:

* Pernah Memiliki Deposito
* Pernah Mengikuti Program Investasi
* Belum Memiliki Produk Asuransi

---

## Insight 5 – Next Best Offer

Contoh:

Potensi Produk:

* BNI Life
* Deposito
* Kartu Kredit Premium

---

## Insight 6 – Customer Story

Contoh:

"Nasabah payroll aktif dengan rata-rata saldo Rp250 juta dan belum memiliki produk asuransi. Memiliki potensi tinggi untuk penawaran proteksi keluarga dan perencanaan keuangan jangka panjang."

---

# 7. Objectives

## Objective Utama

Membangun Customer Insight Generator yang mampu mengotomatisasi proses customer enrichment untuk mempercepat SLA campaign dan meningkatkan efektivitas penjualan melalui DigiSales.

---

## Objective Khusus

### 1. Mempercepat SLA Penyediaan Leads

Dari:

* H+3 sampai H+5 hari

Menjadi:

* H+1 hari
* Same Day untuk campaign tertentu

---

### 2. Mengurangi Proses Manual

Mengurangi aktivitas manual:

* Query berulang
* Enrichment campaign
* Analisis karakteristik nasabah

---

### 3. Menyediakan Customer 360 View

Memberikan informasi yang lebih lengkap kepada sales dalam satu tampilan.

---

### 4. Meningkatkan Kualitas Penawaran

Mendorong personalisasi penawaran berdasarkan profil dan kebutuhan nasabah.

---

### 5. Meningkatkan Potensi Cross-Sell dan Up-Sell

Melalui rekomendasi produk yang lebih tepat sasaran.

---

# 8. Expected Benefits

## Internal Benefits

### Efisiensi SLA

Current State:

* H+3 sampai H+5

Future State:

* H+1 atau Same Day

Percepatan SLA hingga 60%-80%.

---

### Efisiensi Operasional

* Mengurangi pekerjaan manual tim data.
* Mengurangi kebutuhan ad-hoc query.
* Standardisasi insight antar campaign.

---

## Sales Benefits

* Memahami profil nasabah lebih cepat.
* Pendekatan lebih personal.
* Waktu analisis nasabah lebih singkat.

---

## Business Benefits

* Campaign lebih cepat berjalan.
* Peningkatan conversion rate.
* Peningkatan cross-sell.
* Peningkatan fee based income.
* Peningkatan customer engagement.

---

# 9. Key Performance Indicator (KPI)

## KPI Operasional

| KPI                      | Current     | Target |
| ------------------------ | ----------- | ------ |
| SLA Penyediaan Leads     | H+3 s.d H+5 | H+1    |
| Proses Enrichment Manual | 100%        | <20%   |
| Waktu Persiapan Campaign | 3-5 Hari    | 1 Hari |

---

## KPI Sales

| KPI                 | Target           |
| ------------------- | ---------------- |
| Contact Rate        | +10%             |
| Conversion Rate     | +10% sampai +20% |
| Cross Sell Rate     | Meningkat        |
| Produktivitas Sales | Meningkat        |

---

## KPI Bisnis

| KPI                       | Target    |
| ------------------------- | --------- |
| Volume Penjualan Campaign | Meningkat |
| Fee Based Income          | Meningkat |
| Product per CIF           | Meningkat |
| Customer Engagement       | Meningkat |

---

# 10. Success Criteria

Project dianggap berhasil apabila:

* SLA campaign berhasil dipercepat minimal 60%.
* Customer Insight terbentuk otomatis pada setiap leads.
* Sales memperoleh Customer 360 View dalam DigiSales.
* Conversion campaign meningkat dibanding baseline sebelumnya.
* Beban pekerjaan manual tim data berkurang secara signifikan.

---

# Closing Statement

DIG-IN tidak hanya berfungsi sebagai alat enrichment data, tetapi menjadi fondasi transformasi dari "Lead Distribution" menjadi "Insight-Driven Sales Enablement", sehingga campaign dapat dijalankan lebih cepat, lebih cerdas, dan lebih efektif.
