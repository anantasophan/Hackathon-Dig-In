# Panduan Testing — Campaign Insight Generator

> Pastikan kedua server sudah berjalan sebelum mulai:
> - **Backend**: `cd backend && uvicorn local_server.main:app --reload --port 8000`
> - **Frontend**: `cd frontend && npm start`
>
> Buka browser ke **http://localhost:3000**

---

## Persiapan: Login

Karena local dev menggunakan bypass auth, kamu akan langsung masuk ke dashboard tanpa perlu login.
Jika muncul halaman login Cognito, gunakan akun dev lokal atau lewati jika ada tombol skip.

---

## 1. Campaign Overview

**Lokasi**: Sidebar → Campaign Overview

### Test 1.1 — Data muncul normal

| Field | Nilai yang diisi |
|-------|----------------|
| Periode Dari | `2024-07-01` |
| Periode Sampai | `2024-11-30` |
| Flag Program | ✅ PROGRAM QRIS + ✅ PROGRAM BIAYA ADMIN |
| Jenis Leads | *(kosongkan)* |
| Media Blasting | ✅ wa + ✅ telesales + ✅ digisales + ✅ email |
| Wilayah | *(kosongkan = semua)* |

**Klik Apply.**

**Yang diharapkan:**
- Tiga Stat Cards muncul: Total Leads, Total Take Up, Take Up Rate
- Chart trend mingguan tampil di bawah Stat Cards
- Badge response time muncul di pojok kanan atas (hijau jika < 5 detik)

---

### Test 1.2 — Filter spesifik satu program

| Field | Nilai |
|-------|-------|
| Periode Dari | `2024-08-01` |
| Periode Sampai | `2024-08-31` |
| Flag Program | ✅ PROGRAM QRIS saja |
| Media Blasting | ✅ wa |

**Klik Apply.**

**Yang diharapkan:**
- Data hanya dari C001 (Cashback QRIS Agustus 2024)
- Total leads berkurang dibanding Test 1.1

---

### Test 1.3 — Empty state

| Field | Nilai |
|-------|-------|
| Periode Dari | `2023-01-01` |
| Periode Sampai | `2023-12-31` |

**Klik Apply.**

**Yang diharapkan:**
- Muncul ikon Inbox + teks "Tidak ada data untuk filter yang dipilih"
- Tidak ada error merah

---

### Test 1.4 — Reset filter

Setelah Test 1.3, klik tombol **Reset**.

**Yang diharapkan:**
- Semua field filter kembali ke nilai default
- Tanggal kembali ke range default

---

## 2. Perbandingan Campaign

**Lokasi**: Sidebar → Perbandingan Campaign

### Test 2.1 — Bandingkan 2 campaign

1. Ketik `C001` di field input → klik **Tambah**
2. Ketik `C002` → klik **Tambah**
3. Klik **Bandingkan**

**Yang diharapkan:**
- Tabel perbandingan muncul dengan 5 kolom metrik
- Bar chart berdampingan tampil
- Dua chip campaign (C001, C002) muncul di atas

---

### Test 2.2 — Bandingkan 5 campaign (maksimum)

1. Tambahkan C001, C002, C003, C004, C005 satu per satu
2. Coba tambahkan campaign ke-6 (ketik `C001` lagi)

**Yang diharapkan:**
- Campaign C001–C005 berhasil ditambahkan
- Percobaan ke-6: tombol Tambah menjadi disabled / muncul pesan batas maksimal

---

### Test 2.3 — Hapus chip campaign

Setelah menambahkan beberapa campaign, klik tombol **×** di salah satu chip.

**Yang diharapkan:**
- Chip terhapus dari daftar
- Jumlah campaign berkurang

---

### Test 2.4 — Group by atribut

Setelah data muncul, pilih **Group By: flag_program** (atau wilayah/channel).

**Yang diharapkan:**
- Tabel diurutkan berdasarkan atribut yang dipilih secara ascending

---

## 3. Time to Take Up

**Lokasi**: Sidebar → Time to Take Up

### Test 3.1 — Analisis campaign C001

1. Masukkan Campaign ID: `C001`
2. Klik **Cari** / **Analisis**

**Yang diharapkan:**
- Histogram distribusi waktu (7 bin: 0-7, 7-14, 14-21, 21-30, 30-60, 60-90, 90+ hari)
- Stat cards: Rata-rata hari, Median hari
- Nilai rata-rata sekitar 10–15 hari

---

### Test 3.2 — Filter per campaign berbeda

Coba satu per satu: `C002`, `C003`, `C004`, `C005`

**Yang diharapkan:**
- Setiap campaign menampilkan distribusi berbeda
- C005 cenderung lebih cepat (majority di bin 0-14 hari)

---

### Test 3.3 — Campaign tidak ada

Masukkan Campaign ID: `C999`

**Yang diharapkan:**
- Muncul pesan "Belum ada data take up untuk campaign ini"
- Tidak ada error merah

---

## 4. Performa Regional

**Lokasi**: Sidebar → Performa Regional

### Test 4.1 — Cari performa C001

1. Masukkan Campaign ID: `C001`
2. Klik **Cari**

**Yang diharapkan:**
- Tabel wilayah muncul (Wilayah 1, 3, 5, 7, 9, 11)
- Badge take up rate berwarna:
  - Hijau (emerald) jika ≥ 10%
  - Kuning (amber) jika 5–9.99%
  - Merah (rose) jika < 5%
- Wilayah 7 kemungkinan tertinggi (ada data minggu dengan 100%)

---

### Test 4.2 — Pilih wilayah untuk trend mingguan

Setelah tabel muncul, klik salah satu baris wilayah (misal Wilayah 1).

**Yang diharapkan:**
- Chart trend mingguan untuk Wilayah 1 muncul di bawah tabel
- 4 data point mingguan selama Agustus 2024

---

### Test 4.3 — Filter flag program

1. Campaign ID: `C002`
2. Flag Program: pilih `PROGRAM BIAYA ADMIN`
3. Klik **Cari**

**Yang diharapkan:**
- Data muncul khusus untuk program Biaya Admin
- Wilayah yang tampil: 1, 3, 5, 7, 9, 11, 13

---

## 5. Kriteria Nasabah

**Lokasi**: Sidebar → Kriteria Nasabah

### Test 5.1 — Lihat distribusi C001

Masukkan Campaign ID: `C001` → Klik **Cari**

**Yang diharapkan:**
- 5 distribusi chart muncul:
  1. **segment_by_aum**: MASS, UPPERMASS, AFFLUENT, EMERALD, HIGH AFFLUENT, PRIVATE
  2. **range_usia**: GEN Y, GEN X, GEN Z, BABY BOOMER, GEN ALPHA
  3. **media_blasting**: wa (100% untuk C001)
  4. **segment_div_owner**: CRS, WEM (Perorangan)
  5. **flag_program**: PROGRAM QRIS (100% untuk C001)
- Setiap bar menampilkan take up rate per segmen

---

### Test 5.2 — Bandingkan dua campaign berbeda

Coba C001 vs C002 secara bergantian.

**Yang diharapkan:**
- C001: media_blasting = "wa" (100%)
- C002: media_blasting = "telesales" (100%)
- Distribusi segment_by_aum berbeda antara dua campaign

---

## 6. Campaign Serupa

**Lokasi**: Sidebar → Campaign Serupa

### Test 6.1 — Cari campaign serupa C001

1. Masukkan Reference Campaign ID: `C001`
2. Centang dimensi: ✅ **flag_program** + ✅ **jenis_leads**
3. Klik **Cari**

**Yang diharapkan:**
- C003 muncul sebagai hasil (similarity score: 0.83)
- Badge skor berwarna teal
- Dimensi yang cocok ditampilkan: `flag_program`, `jenis_leads`

---

### Test 6.2 — Dimensi berbeda

1. Reference: `C001`
2. Centang: ✅ **media_blasting** saja
3. Klik **Cari**

**Yang diharapkan:**
- C004 muncul (similarity score: 0.55) — keduanya pakai channel `wa`

---

### Test 6.3 — Klik campaign untuk detail

Klik salah satu card campaign hasil pencarian.

**Yang diharapkan:**
- Card terpilih berubah border menjadi teal (`border-2 border-[#005E6A]`)
- Panel perbandingan detail muncul di sebelah kanan atau bawah
- Menampilkan: Metrik Utama, Dimensi yang Cocok, Skor Kesamaan

---

### Test 6.4 — Campaign tanpa kesamaan

1. Reference: `C005`
2. Centang: ✅ **media_blasting** + ✅ **jenis_leads** + ✅ **flag_program**

**Yang diharapkan:**
- Mungkin empty state (tidak ada yang cocok di semua 3 dimensi sekaligus)
- Ikon SearchX muncul (bukan emoji)

---

## 7. AI Recommendations ✨

**Lokasi**: Sidebar → AI Recommendations

### Test 7.1 — Generate rekomendasi default

1. Pilih Campaign: **C001 — Cashback QRIS Agustus 2024**
2. Pilih Goal: **Maksimalkan Take Up Rate**
3. Klik **Generate Rekomendasi AI**

**Yang diharapkan:**
- Loading spinner muncul saat proses
- 3 rekomendasi muncul dengan priority badge (HIGH/MEDIUM/LOW)
- Campaign summary bar muncul (total leads, take up rate, dll)
- Label model: `[SIMULASI] amazon.bedrock.claude-3-sonnet`
- REC-001: tentang segmen terbaik
- REC-002: tentang wilayah terbaik
- REC-003: tentang campaign serupa (C003 dengan skor 0.83)

---

### Test 7.2 — Goal berbeda

1. Campaign: **C001**
2. Goal: **Percepat Waktu Take Up**
3. Generate

**Yang diharapkan:**
- REC-003 berubah menjadi rekomendasi optimasi durasi/timing
- Menyebutkan rata-rata hari take up

---

### Test 7.3 — Ekspansi channel

1. Campaign: **C001** (channel: wa)
2. Goal: **Perluas Jangkauan**
3. Generate

**Yang diharapkan:**
- REC-003 merekomendasikan channel selain `wa` (misal: digisales atau email)
- Menyebutkan A/B test 15-20% leads

---

### Test 7.4 — Campaign berbeda

Coba campaign **C002** (Migrasi, telesales) dengan goal **Maksimalkan Take Up Rate**.

**Yang diharapkan:**
- REC-002 menyebutkan Wilayah dengan performa terbaik untuk C002
- REC-003 mereferensikan C004 (similarity score 0.87 — tertinggi untuk C002)

---

### Test 7.5 — Expand/collapse rekomendasi

Klik header salah satu card rekomendasi.

**Yang diharapkan:**
- Card collapse/expand dengan smooth transition
- Default: REC-001 terbuka, REC-002 dan REC-003 tertutup

---

## 8. Export (di halaman manapun)

**Lokasi**: Tombol Export di pojok kanan atas setiap halaman

### Test 8.1 — Export berhasil

1. Di halaman Campaign Overview dengan data yang sudah muncul
2. Pilih format (CSV/Excel jika tersedia)
3. Klik **Export**

**Yang diharapkan:**
- Loading spinner pada tombol (`Mengekspor`)
- Toast hijau muncul di pojok bawah kanan: "File siap diunduh"
- File terunduh ke komputer
- Tidak ada karakter `!` di pesan toast

---

### Test 8.2 — Dismiss toast

Setelah toast muncul, klik tombol **×** di toast.

**Yang diharapkan:**
- Toast hilang
- Ikon `X` (bukan karakter `✕`)

---

## 9. UI/UX Checks — Desain BNI

Cek hal-hal berikut di **semua halaman**:

| Cek | Kriteria |
|-----|---------|
| ❌ Tidak ada emoji | Tidak ada 🎉 ✅ ⚠️ atau emoji apapun di UI |
| ✅ Sidebar gelap | Background sidebar = slate-900 (gelap, bukan putih) |
| ✅ Nav item aktif | Item aktif berwarna teal (#005E6A), bukan biru |
| ✅ Font Inter | Semua teks menggunakan font Inter (compact, sans-serif) |
| ✅ Card rounded | Semua card memiliki border-radius xl dan shadow-sm |
| ✅ Loading Lucide | Spinner pakai Loader2 berputar (bukan GIF) |
| ✅ Empty state | Ikon Inbox abu-abu + teks formal tanpa tanda seru |
| ✅ Error state | Ikon AlertCircle merah + teks formal |
| ✅ Top header bar | Header putih h-14 dengan judul halaman |

---

## 10. Navigasi Sidebar

Klik setiap item di sidebar secara berurutan:

1. Campaign Overview
2. Perbandingan Campaign
3. Time to Take Up
4. Performa Regional
5. Kriteria Nasabah
6. Campaign Serupa
7. AI Recommendations

**Yang diharapkan:**
- Setiap klik: halaman berganti sesuai item
- Item yang aktif berubah background ke teal
- Hanya satu item yang aktif pada satu waktu

---

## Ringkasan Nilai Valid (Quick Reference)

```
Campaign IDs   : C001 | C002 | C003 | C004 | C005
Tanggal valid  : 2024-07-01 s/d 2024-11-30
Wilayah ada data: 1 | 3 | 5 | 7 | 9 | 11 | 13
Flag Program   : PROGRAM QRIS | PROGRAM BIAYA ADMIN
Jenis Leads    : Akuisisi | Migrasi | Retensi
Media Blasting : wa | telesales | digisales | email
```

> **Tip**: Untuk testing cepat, gunakan selalu **C001** sebagai campaign utama —
> datanya paling lengkap (30 leads, 6 wilayah, 4 minggu trend).
