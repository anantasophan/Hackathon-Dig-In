# Demo Narrative Script — Campaign Insight Generator

> Alur cerita demo: **"Divisi Bisnis mau bikin campaign QRIS baru. Sebelum minta leads ke Divisi Data, mereka cek dulu histori di dashboard ini."**
> Setiap fitur didemokan sebagai satu langkah dalam proses tersebut.

---

## Daftar Isi

1. [Campaign Overview](#1-campaign-overview--bagaimana-performa-semua-campaign-secara-umum)
2. [Perbandingan Campaign](#2-perbandingan-campaign--qris-lama-vs-qris-baru-bedanya-di-mana)
3. [Time to Take Up](#3-time-to-take-up--berapa-lama-nasabah-baru-transaksi-setelah-di-blast)
4. [Performa Regional](#4-performa-regional--wilayah-mana-yang-paling-responsif)
5. [Kriteria Nasabah](#5-kriteria-nasabah--segmen-mana-yang-paling-mungkin-convert)
6. [Campaign Serupa](#6-campaign-serupa--belajar-dari-campaign-yang-mirip)
7. [AI Recommendations](#7-ai-recommendations--kalau-ai-yang-kasih-saran-apa-katanya)
8. [Ringkasan Alur Demo](#ringkasan-alur-demo-urutan-yang-disarankan-8-menit)
9. [Catatan Teknis: Penyesuaian Tanggal](#catatan-teknis-penyesuaian-tanggal)

---

## 1. Campaign Overview — "Bagaimana performa semua campaign secara umum?"

**Setup**: buka halaman Overview, ubah tanggal filter **Dari `2026-01-01` Sampai `2026-12-31`** (biar semua 9 campaign masuk).

**Yang ditunjukkan:**
- Total 2.620 leads, 157 take-up, rate keseluruhan **5.99%**
- Grafik tren menunjukkan lonjakan besar di sekitar Juni 2026 (333 leads dalam satu minggu) — titik masuk yang bagus untuk bilang "ini data riil dari campaign QRIS dan E-Wallet, volumenya jauh lebih besar dari campaign-campaign sebelumnya"

**Narasi**: "Sebelum kita punya dashboard ini, tim harus buka file Excel terpisah untuk tahu angka-angka ini. Sekarang tinggal atur filter tanggal, semua kelihatan."

**Coba juga**: centang filter **Flag Program → PROGRAM TAPENAS**, klik Apply. Tunjukkan angka berubah instan.

---

## 2. Perbandingan Campaign — "QRIS lama vs QRIS baru, bedanya di mana?"

**Setup bagian 1**: masukkan campaign ID `C001, C002, C003, C004, C005` (batch campaign awal tahun 2026).

| Campaign | Leads | Take-up Rate | Nilai Transaksi |
|---|---|---|---|
| C001 Cashback QRIS Batch 1 2026 | 30 | 33.3% | Rp 28 jt |
| C005 Email QRIS Affluent | 21 | **42.9%** (tertinggi) | Rp 39 jt |

**Narasi 1**: "Ini contoh batch campaign QRIS pertama kita di 2026 — take-up rate 30-40%, cukup sehat."

**Setup bagian 2**: ganti input jadi `C006, C007, C008, C009` (batch campaign volume besar, pertengahan 2026).

| Campaign | Leads | Take-up Rate | Nilai Transaksi |
|---|---|---|---|
| C006 Cashback QRIS 2026 | 800 | 0.62% | Rp 262 rb |
| C007 E-Wallet/Billpayment 2026 | 800 | 2.5% | Rp 1.5 jt |
| C008 Tapenas Emas 2026 | 800 | 0.75% | **Rp 2.4 miliar** |
| C009 Lifegoals Balrun Payroll | 104 | **80.77%** | Rp 682 jt |

**Narasi 2** (poin paling kuat untuk juri): "Perhatikan, take-up rate batch campaign volume besar ini sangat rendah dibanding batch pertama — 0.6% vs 33%. Ini bukan bug, ini kenyataan pahit yang justru jadi alasan kenapa tools ini dibutuhkan: dengan basis leads besar (800rb+), konversi kecil itu wajar, tapi tim butuh insight untuk tahu **segmen mana** yang harus diprioritaskan. Sementara itu lihat C008 Tapenas — rate cuma 0.75% tapi nilai transaksinya 2.4 miliar, karena setiap nasabah yang convert nabung besar. Dan C009 Lifegoals rate-nya 80%, jauh berbeda karena ini bukan cold leads, tapi follow-up ke nasabah yang sudah engaged."

---

## 3. Time to Take Up — "Berapa lama nasabah baru transaksi setelah di-blast?"

**Setup 1**: masukkan `C001` (batch pertama).
- Rata-rata **11.6 hari**, median 10 hari, rentang 2-24 hari — pola cepat dan rapi.

**Setup 2**: ganti ke `C008` (Tapenas Emas).
- Rata-rata **59.3 hari**, median 70 hari — 66.7% nasabah baru buka rekening di rentang 60-90 hari.

**Narasi**: "Produk QRIS itu impulsif — orang klik link, langsung transaksi, rata-rata 11 hari. Tapi produk tabungan seperti Tapenas jauh lebih lambat, karena keputusan buka rekening berjangka butuh pertimbangan matang, rata-rata 2 bulan. Insight ini penting: kalau Divisi Bisnis mau evaluasi campaign Tapenas cuma 2 minggu setelah blast, kesimpulannya akan salah — take-up-nya belum kelihatan."

**Bonus opsional**: coba `C009`, tunjukkan ada `min_days: -18` (minus). Jelaskan: "Ini catatan jujur soal data — beberapa nasabah ternyata sudah buka rekening Lifegoals SEBELUM WA blast ini dikirim, jadi bukan hasil dari campaign ini. Transparansi data seperti ini yang bikin insight bisa dipercaya."

---

## 4. Performa Regional — "Wilayah mana yang paling responsif?"

**Setup**: masukkan `C005` (batch pertama, cuma ada 7 wilayah: 1,3,5,7,9,11,13) dulu untuk baseline sederhana — Wilayah 1, 5, 11 semua di 66.67%.

**Lanjut**: masukkan `C007` (E-Wallet 2026) — sekarang **semua 17 wilayah** muncul (bukan cuma 7).

**Yang ditunjukkan**: Wilayah 14 unggul dengan take-up rate 7.69%, jauh di atas rata-rata keseluruhan campaign (2.5%).

**Narasi**: "Data campaign terbaru mencakup seluruh 17 wilayah operasional, bukan cuma sample kecil. Dashboard otomatis rank wilayah dari yang paling responsif. Kalau mau campaign susulan, Wilayah 14 layak diprioritaskan channel WA-nya."

---

## 5. Kriteria Nasabah — "Segmen mana yang paling mungkin convert?"

**Setup**: masukkan `C008` (Tapenas Emas).

**Yang ditunjukkan**: breakdown by `segment_by_aum`
- MASS: 316 nasabah, **0% take-up**
- HIGH AFFLUENT: 178 nasabah, **1.69% take-up** — lebih baik dari MASS

**Narasi**: "Ini contoh nyata kenapa fitur ini bernilai: kalau leads Tapenas berikutnya difokuskan ke segmen MASS (porsi terbesar, 39.5%), hasilnya nihil. Tapi segmen HIGH AFFLUENT, meski volumenya lebih kecil, justru convert. Insight seperti ini langsung actionable buat Divisi Bisnis menyusun kriteria campaign berikutnya."

---

## 6. Campaign Serupa — "Belajar dari campaign yang mirip"

**Setup 1** (batch pertama, hasil bagus untuk ditunjukkan): Referensi `C001`, centang dimensi **`flag_program` + `jenis_leads`**.
- Hasil: C003 muncul, skor kesamaan 0.83, take-up rate 20.69%

**Setup 2** (batch volume besar): Referensi `C006`, centang dimensi **`jenis_leads` + `media_blasting`**.
- Hasil: C007 muncul, skor 0.67, take-up rate 2.5%

**Narasi**: "Sebelum Divisi Bisnis submit request leads baru, mereka bisa cek dulu: 'campaign apa yang mirip dengan rencana saya, dan bagaimana hasilnya dulu?' Ini menjawab pain point utama di proposal awal — mengurangi trial-and-error dan revisi request."

**Peringatan saat demo**: field harus dicentang kombinasi yang memang match — kalau centang 3 dimensi sekaligus, hasilnya sering kosong karena butuh exact match di semua dimensi yang dicentang.

---

## 7. AI Recommendations — "Kalau AI yang kasih saran, apa katanya?"

**Setup**: pilih campaign `C006` atau `C008` dari dropdown, pilih salah satu tujuan optimasi, klik **Generate Rekomendasi AI**.

**Narasi**: "Ini fitur future enhancement yang disebut di proposal awal, sekarang sudah ada simulasinya. AI menganalisis data historis campaign dan memberi 3 rekomendasi konkret — target segmen, channel, dan timing — bukan cuma laporan pasif."

> **Catatan**: cek dulu isi respons sebelum demo live, karena ini simulasi/mock, bukan model AI produksi sungguhan — supaya tidak salah klaim ke juri.

---

## Ringkasan Alur Demo (urutan yang disarankan, ±8 menit)

1. **Overview** → tunjukkan skala data (2.620 leads, 9 campaign) — 1 menit
2. **Comparison** C001-C005 vs C006-C009 → kontras batch pertama vs batch volume besar, ini klimaks cerita — 2 menit
3. **Time to Take Up** C001 vs C008 → insight kecepatan konversi beda per produk — 1.5 menit
4. **Regional** C007 → insight wilayah terbaik dari 17 wilayah — 1 menit
5. **Kriteria Nasabah** C008 → insight segmen yang salah sasaran vs yang tepat — 1.5 menit
6. **Campaign Serupa** C001 → tutup dengan pain point utama yang terjawab — 1 menit

---

## Catatan Teknis: Penyesuaian Tanggal

Seluruh 9 campaign (C001-C009) sekarang berada dalam rentang **1 Januari 2026 - awal Juni 2026**. Campaign C001-C005 awalnya berbasis tanggal 2024 (bawaan data demo sebelumnya) — tanggalnya sudah digeser maju +549 hari agar tidak ada lagi campaign yang tercatat di 2024. Nama program C001 dan C002 yang sebelumnya menyebut "Agustus 2024" dan "Q3 2024" juga sudah diperbarui menjadi "Cashback QRIS Batch 1 2026" dan "Migrasi Biaya Admin Batch 1 2026" agar konsisten di seluruh aplikasi (dropdown filter, halaman Campaign Serupa, dan AI Recommendations).

Pergeseran dilakukan secara uniform (semua tanggal terkait: `periode_start`, `periode_end`, `take_up_date`, data tren mingguan, data regional mingguan) sehingga durasi campaign, urutan relatif antar campaign, dan seluruh statistik (`time_to_take_up_days`, `take_up_rate`, dll) tidak berubah — hanya titik kalendernya yang maju.

---

## Referensi Cepat: Nilai Filter yang Valid

```
Flag Program  : PROGRAM QRIS | PROGRAM BIAYA ADMIN | PROGRAM TAPENAS | PROGRAM LIFEGOALS
Media Blasting : wa | telesales | email | digisales
Wilayah        : 1 - 17
Campaign IDs   : C001 | C002 | C003 | C004 | C005 | C006 | C007 | C008 | C009
Jenis Leads    : MIGRASI BAU, MIGRASI BAU 2, MIGRASI - TAMBAH 87K, MIGRASI - CASHOUT,
                 MIGRASI - BO, Balrun - Affluent, Balrun- Payroll, Balrun- BO,
                 Lifegoals - Balrun Payroll, Akuisisi, Migrasi, Retensi
```

*Dokumen ini dibuat berdasarkan data aktual dari local dev server (`localhost:8000`), diverifikasi langsung lewat pemanggilan setiap endpoint API sebelum narasi ditulis.*
