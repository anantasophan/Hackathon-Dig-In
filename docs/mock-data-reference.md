# Mock Data Reference — Local Dev Server

> Dokumen ini adalah referensi lengkap semua data yang tersedia di local dev server (`localhost:8000`).
> Gunakan panduan ini untuk mengisi filter di setiap halaman agar data muncul.

---

## Daftar Campaign (campaigns.json)

Ada **5 campaign** yang tersedia:

| ID | Nama Program | Flag Program | Jenis Leads | Media Blasting | Periode |
|----|-------------|--------------|-------------|----------------|---------|
| **C001** | Cashback QRIS Agustus 2024 | PROGRAM QRIS | Akuisisi | wa | 2024-08-01 s/d 2024-08-31 |
| **C002** | Migrasi Biaya Admin Q3 2024 | PROGRAM BIAYA ADMIN | Migrasi | telesales | 2024-07-01 s/d 2024-09-30 |
| **C003** | Digisales QRIS Nasabah Mass | PROGRAM QRIS | Akuisisi | digisales | 2024-09-01 s/d 2024-09-30 |
| **C004** | WA Blast Biaya Admin Emerald | PROGRAM BIAYA ADMIN | Migrasi | wa | 2024-10-01 s/d 2024-10-31 |
| **C005** | Email QRIS Nasabah Affluent | PROGRAM QRIS | Retensi | email | 2024-11-01 s/d 2024-11-30 |

---

## Panduan Filter Per Halaman

### Campaign Overview

Isi filter berikut agar data muncul:

| Field | Nilai yang Valid |
|-------|----------------|
| **Periode Dari** | `2024-07-01` (atau sebelumnya) |
| **Periode Sampai** | `2024-11-30` (atau sesudahnya) |
| **Flag Program** | `PROGRAM QRIS` dan/atau `PROGRAM BIAYA ADMIN` |
| **Jenis Leads** | `Akuisisi`, `Migrasi`, `Retensi` (ketik manual, pisah koma) |
| **Media Blasting** | `wa`, `telesales`, `digisales`, `email` |
| **Wilayah** | 1, 3, 5, 7, 9, 11, 13 (wilayah yang ada datanya) |

> **Tip cepat**: Ubah tanggal dari ke `2024-07-01` dan sampai ke `2024-11-30`, centang semua Flag Program dan Media Blasting, lalu klik Apply — semua 5 campaign akan muncul.

---

### Perbandingan Campaign

Masukkan **2–5 Campaign ID** dari daftar berikut:

```
C001, C002, C003, C004, C005
```

Contoh kombinasi yang menarik:
- `C001` vs `C002` — QRIS vs Biaya Admin
- `C001` vs `C003` — dua campaign QRIS berbeda channel
- `C002` vs `C004` — dua campaign Migrasi Biaya Admin

---

### Time to Take Up

Gunakan **Campaign ID** yang sama: `C001`, `C002`, `C003`, `C004`, atau `C005`.

Data time-to-take-up per campaign (dalam hari):

| Campaign | Contoh Waktu Take Up (hari) |
|----------|---------------------------|
| C001 | 2, 4, 5, 7, 9, 11, 14, 19, 21, 24 |
| C002 | 2, 5, 7, 14, 21 |
| C003 | 3, 5, 8, 12, 15 |
| C004 | 4, 6, 9, 11, 18 |
| C005 | 2, 6, 10, 14, 20 |

---

### Performa Regional

Gunakan **Campaign ID** dari daftar, lalu pilih **Wilayah**:

| Campaign | Wilayah yang Ada Datanya |
|----------|--------------------------|
| C001 | 1, 3, 5, 7, 9, 11 |
| C002 | 1, 3, 5, 7, 9, 11, 13 |
| C003 | 1, 3, 5, 7, 9, 11, 13 |
| C004 | 1, 3, 5, 7, 9, 11, 13 |
| C005 | 1, 3, 5, 7, 9, 11, 13 |

Contoh input:
- Campaign ID: `C001`
- Wilayah: pilih `Wilayah 1` atau `Wilayah 3`

---

### Kriteria Nasabah

Gunakan **Campaign ID**: `C001`, `C002`, `C003`, `C004`, atau `C005`.

---

### Campaign Serupa

Masukkan **Campaign ID** referensi, lalu centang dimensi yang ingin dicocokkan:

| Dimensi | Artinya |
|---------|---------|
| `flag_program` | Cocokkan berdasarkan jenis program (QRIS / Biaya Admin) |
| `jenis_leads` | Cocokkan berdasarkan tujuan leads (Akuisisi / Migrasi / Retensi) |
| `media_blasting` | Cocokkan berdasarkan channel distribusi |

Pasangan campaign serupa yang sudah ada di data:

| Referensi | Serupa Dengan | Dimensi Cocok | Skor |
|-----------|--------------|---------------|------|
| C001 | C003 | flag_program, jenis_leads | 0.83 |
| C001 | C005 | flag_program | 0.60 |
| C001 | C004 | media_blasting | 0.55 |
| C002 | C004 | flag_program, jenis_leads | 0.87 |
| C003 | C001 | flag_program, jenis_leads | 0.83 |
| C003 | C005 | flag_program | 0.58 |
| C004 | C002 | flag_program, jenis_leads | 0.87 |
| C004 | C001 | media_blasting | 0.55 |
| C005 | C001 | flag_program | 0.60 |
| C005 | C003 | flag_program | 0.58 |

> **Tip**: Gunakan `C001` dengan dimensi `flag_program` + `jenis_leads` → akan menemukan C003 (skor 0.83).

---

## Detail Data Leads (leads.json)

Setiap lead memiliki field berikut:

| Field | Nilai yang Ada di Data |
|-------|----------------------|
| `campaign_id` | C001, C002, C003, C004, C005 |
| `flag_program` | PROGRAM QRIS, PROGRAM BIAYA ADMIN |
| `jenis_leads` | Akuisisi, Migrasi, Retensi |
| `media_blasting` | wa, telesales, digisales, email |
| `wilayah` | 1, 3, 5, 7, 9, 11, 13 |
| `segment_by_aum` | MASS, UPPERMASS, AFFLUENT, HIGH AFFLUENT, EMERALD, PRIVATE |
| `range_usia` | GEN Y, GEN X, GEN Z, BABY BOOMER, GEN ALPHA |
| `segment_div_owner` | CRS, WEM (Perorangan) |
| `take_up_flag` | YES, NO |

### Statistik Take Up per Campaign

| Campaign | Total Leads | Take Up | Take Up Rate |
|----------|------------|---------|-------------|
| C001 | 30 | 6 | ~20% |
| C002 | 30 | 7 | ~23% |
| C003 | 29 | 6 | ~21% |
| C004 | 30 | 6 | ~20% |
| C005 | 30 | 8 | ~27% |

---

## Data Trend Mingguan (trend_data.json)

Data trend per campaign dalam periode 4 minggu:

### C001 — Cashback QRIS Agustus 2024

| Periode | Leads | Take Up | Rate |
|---------|-------|---------|------|
| 01–07 Agt | 8 | 2 | 25.0% |
| 08–14 Agt | 7 | 2 | 28.6% |
| 15–21 Agt | 8 | 1 | 12.5% |
| 22–31 Agt | 7 | 1 | 14.3% |

### C002 — Migrasi Biaya Admin Q3 2024

| Periode | Leads | Take Up | Rate |
|---------|-------|---------|------|
| 01–07 Jul | 8 | 2 | 25.0% |
| 08–14 Jul | 7 | 1 | 14.3% |
| 15–21 Jul | 6 | 2 | 33.3% |
| 22–31 Jul | 9 | 2 | 22.2% |

### C003 — Digisales QRIS Nasabah Mass

| Periode | Leads | Take Up | Rate |
|---------|-------|---------|------|
| 01–07 Sep | 7 | 2 | 28.6% |
| 08–14 Sep | 8 | 1 | 12.5% |
| 15–21 Sep | 7 | 2 | 28.6% |
| 22–30 Sep | 7 | 1 | 14.3% |

### C004 — WA Blast Biaya Admin Emerald

| Periode | Leads | Take Up | Rate |
|---------|-------|---------|------|
| 01–07 Okt | 8 | 2 | 25.0% |
| 08–14 Okt | 7 | 2 | 28.6% |
| 15–21 Okt | 8 | 1 | 12.5% |
| 22–31 Okt | 7 | 1 | 14.3% |

### C005 — Email QRIS Nasabah Affluent

| Periode | Leads | Take Up | Rate |
|---------|-------|---------|------|
| 01–07 Nov | 8 | 2 | 25.0% |
| 08–14 Nov | 7 | 2 | 28.6% |
| 15–21 Nov | 8 | 1 | 12.5% |
| 22–30 Nov | 7 | **3** | **42.9%** ← tertinggi |

---

## Data Regional Mingguan (regional_weekly.json)

Data per wilayah per minggu untuk setiap campaign. Wilayah yang ada: **1, 3, 5, 7, 9, 11, 13**.

Contoh snapshot C001 (Agustus 2024):

| Wilayah | Minggu | Leads | Take Up | Rate |
|---------|--------|-------|---------|------|
| 1 | 01 Agt | 3 | 1 | 33.3% |
| 3 | 01 Agt | 2 | 1 | 50.0% |
| 5 | 01 Agt | 2 | 1 | 50.0% |
| 7 | 15 Agt | 1 | 1 | **100%** ← tertinggi |
| 9 | semua | 9 | 0 | 0% ← tidak ada take up |
| 11 | 01 Agt | 2 | 1 | 50.0% |

---

## Ringkasan Nilai Valid untuk Setiap Filter

```
Flag Program  : PROGRAM QRIS | PROGRAM BIAYA ADMIN
Jenis Leads   : Akuisisi | Migrasi | Retensi
Media Blasting: wa | telesales | digisales | email
Wilayah       : 1 | 3 | 5 | 7 | 9 | 11 | 13
Campaign IDs  : C001 | C002 | C003 | C004 | C005
Rentang Tanggal: 2024-07-01 s/d 2024-11-30
```

> **Catatan**: Wilayah 2, 4, 6, 8, 10, 12, 14, 15, 16, 17 tidak ada datanya di mock — filter ke wilayah-wilayah tersebut akan menghasilkan empty state.
