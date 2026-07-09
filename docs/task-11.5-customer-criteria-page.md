# Task 11.5 — CustomerCriteriaPage (Halaman Kriteria Nasabah)

## Ringkasan Singkat

`CustomerCriteriaPage` adalah halaman dashboard yang menampilkan **distribusi karakteristik demografis dan finansial nasabah** untuk sebuah campaign. Pengguna memasukkan Campaign ID, lalu sistem memuat data dari backend dan menampilkan grafik batang horizontal untuk setiap atribut nasabah — mulai dari segmen AUM, kelompok usia, wilayah domisili, produk yang dimiliki, hingga kategori saldo. Halaman ini membantu Campaign Owner memahami profil nasabah mana yang paling banyak melakukan take-up (konversi) dalam suatu kampanye.

---

## Penjelasan Awam (Non-Technical)

Bayangkan Anda sedang menganalisis kampanye pemasaran bank. Anda ingin tahu: "Nasabah dengan profil seperti apa yang paling banyak merespons kampanye ini?" Halaman Kriteria Nasabah menjawab pertanyaan itu secara visual.

- **Analogi**: Seperti laporan statistik pengunjung toko — berapa persen pembeli berusia muda vs tua, tinggal di kota mana, memiliki produk apa.
- **Yang ditampilkan**: 5 "kartu" grafik — satu untuk setiap karakteristik nasabah (segmen, usia, wilayah, produk, saldo).
- **Manfaat bisnis**: Membantu tim Campaign Owner merancang kampanye berikutnya dengan target nasabah yang lebih tepat, meningkatkan kemungkinan konversi.
- **Jika data tidak ada**: Kartu yang datanya kosong ditampilkan abu-abu dengan penjelasan mengapa data tidak tersedia.

---

## Penjelasan Teknis

### File yang Dibuat / Dimodifikasi

| File | Perubahan |
|------|-----------|
| `frontend/src/pages/CustomerCriteriaPage.tsx` | Dibuat — komponen utama halaman |
| `frontend/src/pages/CustomerCriteriaPage.css` | Dibuat — stylesheet tanpa Tailwind |
| `frontend/src/types/api.ts` | Dimodifikasi — `AttributeDistribution` ditambahkan field `available` (boolean) dan `unavailable_reason` (string \| null); `CustomerCriteriaResponse` ditambahkan `partial_data_message`, `available_attributes`, `unavailable_attributes` |
| `frontend/src/App.tsx` | Dimodifikasi — route `/customer-criteria` diarahkan ke `<CustomerCriteriaPage />` |

### Library / Framework

- **React 18** dengan TypeScript strict mode
- **Chart.js + react-chartjs-2** — grafik batang horizontal (`indexAxis: 'y'`)
- **DashboardLayout** — wrapper shell standar (header, sidebar, konten)
- **api.getCustomerCriteria(campaignId)** — GET `/api/campaigns/customer-criteria/{id}`

### Arsitektur Komponen

```
CustomerCriteriaPage
├── DashboardLayout          (shell: header + sidebar)
├── cc-input-card            (text input + tombol "Lihat Kriteria")
├── cc-banner-info           (partial_data_message — info banner biru)
├── cc-campaign-heading      (nama + ID campaign)
└── cc-dist-grid             (CSS grid responsive)
    └── DistributionCard × N (satu per atribut)
        ├── [unavailable] → kartu abu-abu + pesan
        └── [available]   → DistributionChart (Bar horizontal)
```

### Keputusan Desain Penting

1. **Horizontal bar chart** dipilih (bukan vertikal) karena label atribut seperti "UPPERMASS", "BABY BOOMER", "Jawa Barat" lebih mudah dibaca secara horizontal. Dikonfigurasi via `indexAxis: 'y'`.
2. **`isTall()`**: Atribut dengan >6 nilai (umumnya `domicile_region`) mendapat chart lebih tinggi (340px vs 240px) untuk mencegah label bertumpuk.
3. **Type update**: `AttributeDistribution` di `types/api.ts` awalnya tidak punya field `available` dan `unavailable_reason` — ditambahkan agar sesuai dengan respons aktual backend Lambda.
4. **Partial data banner**: Ditampilkan di atas grid chart hanya ketika `partial_data_message` ada di respons, membantu pengguna memahami bahwa sebagian data mungkin tidak lengkap.
5. **CSS murni** (tanpa Tailwind) sesuai konvensi proyek.

### Edge Cases yang Ditangani

- Campaign ID kosong → tombol dinonaktifkan
- API error → state error dengan pesan deskriptif
- Tidak ada distribusi (array kosong) → empty state card
- Atribut tidak tersedia (`available: false`) → kartu abu-abu dengan `unavailable_reason`
- Banyak nilai per atribut → chart lebih tinggi otomatis
- Tooltip multiline: count, distribusi%, take-up count, take-up rate%

---

## Struktur Kode

| Simbol | Jenis | Deskripsi |
|--------|-------|-----------|
| `ATTR_LABELS` | const | Peta `attribute_key → label Bahasa Indonesia` |
| `humanizeAttr(attribute)` | helper | Konversi snake_case → label manusiawi |
| `fmtPct(n)` | helper | Format angka ke `"40.00%"` |
| `fmtNum(n)` | helper | Format angka ke `"1.234"` (id-ID locale) |
| `isTall(dist)` | helper | True jika items > 6 (pakai chart lebih tinggi) |
| `DistributionChart` | component | `<Bar>` horizontal dengan tooltip kustom |
| `DistributionCard` | component | Kartu per atribut (available/unavailable) |
| `CustomerCriteriaPage` | component | Halaman utama — state + layout + render logic |

---

## Simulasi / Skenario

### Skenario 1 — Data Lengkap (Happy Path)

**Input**: Campaign ID = `"QRIS-2024-07"`

**Proses**:
1. User ketik ID → klik "Lihat Kriteria"
2. Loading spinner tampil
3. `api.getCustomerCriteria("QRIS-2024-07")` → GET backend
4. Backend kembalikan 5 distribusi, semua `available: true`

**Output**:
```
Nama Campaign: Kampanye QRIS Nasabah Aktif (QRIS-2024-07)
[5 kartu grafik horizontal]
  ✅ Segmen Nasabah    — MASS 40% | UPPERMASS 30% | EMERALD 20% | AFFLUENT 10%
  ✅ Kelompok Usia     — GEN Y 45% | GEN X 30% | BABY BOOMER 15% | GEN Z 10%
  ✅ Wilayah Domisili  — (banyak nilai, chart lebih tinggi)
  ✅ Produk yang Dimiliki — Tabungan 60% | Giro 25% | Deposito 15%
  ✅ Kategori Saldo    — 0-1jt 35% | 1-10jt 40% | >10jt 25%
```

Tooltip saat hover "MASS": `Jumlah: 1.200 | Distribusi: 40.00% | Take Up: 360 | Take-Up Rate: 30.00%`

---

### Skenario 2 — Data Parsial (Req 5.5)

**Input**: Campaign ID = `"ADMIN-2024-03"` (data `balance_category` tidak ada)

**Output**:
```
ℹ️ Atribut berikut tidak tersedia untuk campaign ini: balance_category.
[4 kartu berwarna normal + 1 kartu abu-abu]
  ✅ Segmen Nasabah    — grafik normal
  ✅ Kelompok Usia     — grafik normal
  ✅ Wilayah Domisili  — grafik normal
  ✅ Produk yang Dimiliki — grafik normal
  ⚠️ Kategori Saldo   — [abu-abu] "Atribut 'balance_category' tidak tersedia untuk campaign ini."
```

---

### Skenario 3 — Error API

**Input**: Campaign ID = `"NONEXISTENT-999"`

**Output**:
```
⚠️ Terjadi kesalahan saat memuat data.
Silakan periksa Campaign ID dan coba lagi.
```

---

## Keterkaitan dengan Komponen Lain

- **Bergantung pada**:
  - `DashboardLayout` — shell visual (sidebar navigasi, header)
  - `api.getCustomerCriteria()` di `services/api.ts` — HTTP call ke backend
  - `CustomerCriteriaResponse`, `AttributeDistribution`, `DistributionItem` dari `types/api.ts`
  - `useAuth` hook — username untuk header dan fungsi sign-out
  - `chart.js` + `react-chartjs-2` — rendering grafik

- **Digunakan oleh**:
  - `App.tsx` — route `/customer-criteria`

- **Pengaruh ke**:
  - Jika `AttributeDistribution` di `types/api.ts` berubah, komponen ini perlu menyesuaikan rendering conditional `available`/unavailable

---

## Requirements yang Dipenuhi

| Requirement | Deskripsi |
|-------------|-----------|
| 5.1 | Distribusi demografis (segmen, usia, wilayah domisili) ditampilkan sebagai grafik |
| 5.2 | Distribusi finansial (produk, saldo) ditampilkan sebagai grafik |
| 5.3 | Visualisasi take-up vs non-take-up — terlihat di tooltip per bar |
| 5.4 | Per-atribut take_up_rate breakdown — tooltip menampilkan take_up_count dan take_up_percentage |
| 5.5 | Pesan data parsial + kartu abu-abu untuk atribut yang tidak tersedia |

---

## Catatan Penting

- **Type update wajib**: `AttributeDistribution` di `types/api.ts` diperbarui agar match dengan respons backend aktual yang memiliki field `available` dan `unavailable_reason`. Field ini tidak ada di definisi tipe awal.
- **`campaign_name` opsional**: Backend Lambda saat ini tidak mengembalikan `campaign_name` secara eksplisit di response body (hanya `campaign_id`). Field `campaign_name?` dibuat optional di tipe sehingga rendering graceful jika tidak ada.
- **Tidak ada FilterPanel**: Halaman ini tidak menggunakan FilterPanel karena filter kampanye tidak relevan — input hanya Campaign ID tunggal.
- **Todo**: Bisa ditambahkan perbandingan visual take-up vs non-take-up sebagai dataset kedua di grafik (stacked bar), jika requirement 5.3 ingin divisualisasikan lebih eksplisit.
