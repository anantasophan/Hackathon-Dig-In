# Campaign Insight Generator

### Transforming Historical Campaign Data into Actionable Business Intelligence

## 1. Current State

### Business Process

Saat ini Divisi Data memiliki peran sebagai penyedia data leads bagi
unit bisnis dalam pelaksanaan berbagai program pemasaran (campaign).
Permintaan leads berasal dari berbagai Divisi Bisnis di Kantor Pusat
yang bertindak sebagai campaign owner.

Leads yang telah disiapkan kemudian digunakan pada berbagai channel
distribusi, antara lain:

-   Relationship Manager (RM)
-   WhatsApp Blast
-   Mobile Banking (Push Notification / Pop-up Message)
-   Telemarketing
-   Channel lainnya sesuai kebutuhan program

Setelah campaign selesai dilaksanakan, Divisi Bisnis akan kembali
meminta data monitoring kepada Divisi Data untuk mengevaluasi hasil
campaign.

Dengan demikian, Divisi Data terlibat pada dua proses utama:

1.  Penyediaan data leads.
2.  Penyediaan monitoring hasil campaign.

## Current Business Flow

``` text
Business Division
        │
Menyusun Kriteria Campaign
        │
        ▼
Request Leads
        │
        ▼
Data Division
- Data Extraction
- Data Validation
- Lead Distribution
(SLA ± 3 Hari)
        │
        ▼
Campaign Execution
(RM / WA Blast / Mobile Banking / dll)
        │
Campaign berjalan
(1 minggu - 1 bulan)
        │
        ▼
Business Request Monitoring
        │
        ▼
Data Division
Generate Monitoring Report
        │
        ▼
Business Evaluation
        │
        ▼
Campaign Berikutnya
```

## 2. Existing Challenges

### 2.1 Campaign Knowledge Belum Terdokumentasi

Setiap campaign menghasilkan informasi penting seperti jumlah leads,
take up rate, nilai transaksi, karakteristik target, wilayah terbaik,
dan waktu terbaik terjadinya take up. Informasi tersebut masih tersebar
dalam berbagai file monitoring dan belum menjadi knowledge yang dapat
dimanfaatkan kembali.

### 2.2 Penyusunan Campaign Masih Bersifat Manual

Ketika Divisi Bisnis akan membuat campaign baru, penyusunan kriteria
target masih banyak bergantung pada diskusi dan pengalaman masing-masing
PIC sehingga sering terjadi perubahan kriteria, overlap antar campaign,
dan revisi request kepada Divisi Data.

### 2.3 Proses Iterasi Memperpanjang SLA

Perubahan kriteria setelah leads selesai diproses menyebabkan proses
extraction ulang sehingga meningkatkan effort manual dan memperpanjang
SLA.

### 2.4 Monitoring Bersifat Historis

Monitoring saat ini hanya digunakan sebagai laporan hasil campaign dan
belum dimanfaatkan sebagai insight untuk campaign berikutnya.

## 3. Root Cause Analysis

Belum terdapat mekanisme yang menghubungkan histori request, data leads,
dan hasil monitoring menjadi knowledge repository yang dapat digunakan
kembali.

## 4. Opportunity

Perusahaan telah memiliki histori campaign, data leads, monitoring,
karakteristik nasabah, hasil take up, nominal transaksi, wilayah,
produk, dan sub produk yang dapat diolah menjadi business insight.

## 5. Proposed Solution

### Campaign Insight Generator

Dashboard analitik yang mengintegrasikan histori campaign menjadi
insight bisnis untuk membantu penyusunan campaign berikutnya.

## 6. Key Features

-   Campaign Overview
-   Campaign Comparison
-   Time to Take Up Analysis
-   Regional Performance
-   Customer Criteria Analysis
-   Similar Campaign Comparison
-   AI Campaign Summary (Future Enhancement)

## 7. Future Business Flow

``` text
Business Division
        │
Melihat Insight Campaign Sebelumnya
        │
        ▼
Campaign Insight Generator
        │
Recommendation & Historical Insight
        │
        ▼
Request Leads
        │
        ▼
Data Division
Generate Leads
        │
        ▼
Campaign Execution
        │
        ▼
Monitoring
        │
        ▼
Insight otomatis kembali masuk ke Dashboard
```

## 8. Expected Benefits

### Operational

-   Mempercepat penyusunan kriteria campaign.
-   Mengurangi revisi request leads.
-   Mengurangi proses manual Divisi Data.
-   Mempercepat SLA penyediaan leads.

### Business

-   Membantu penyusunan target campaign berbasis data.
-   Memanfaatkan histori campaign.
-   Mengurangi trial and error.

### Strategic

-   Membangun knowledge repository.
-   Mendukung data-driven decision.
-   Meningkatkan efektivitas campaign.

## 9. Success Metrics

  KPI                         Current          Target
  --------------------------- ---------------- -------------------
  SLA Penyediaan Leads        ±3 Hari          ≤1 Hari\*
  Revisi Request Leads        Tinggi           Menurun
  Analisis Campaign           Manual           Dashboard
  Pemanfaatan Histori         Belum tersedia   Menjadi referensi
  Waktu Penyusunan Campaign   Manual           Lebih cepat

## 10. Vision

Campaign Insight Generator menjadi knowledge engine yang mengubah
histori campaign menjadi rekomendasi yang dapat digunakan untuk menyusun
campaign berikutnya secara lebih cepat, tepat, dan berbasis data.
