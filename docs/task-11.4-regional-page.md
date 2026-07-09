# Task 11.4 — Halaman Performa Regional

## Ringkasan Singkat

`RegionalPerformancePage` adalah halaman dashboard yang menampilkan performa setiap wilayah (1–17) untuk sebuah campaign tertentu. Pengguna memasukkan Campaign ID, memilih filter program, lalu melihat tabel rangking wilayah berdasarkan Take Up Rate. Klik satu baris menampilkan grafik tren 8 minggu untuk wilayah tersebut.

---

## Penjelasan Awam (Non-Technical)

Bayangkan sebuah papan skor pertandingan olahraga, tetapi yang bersaing adalah wilayah-wilayah bank di seluruh Indonesia. Setiap baris tabel menunjukkan nama wilayah, berapa banyak nasabah yang dihubungi (Total Leads), berapa yang ikut serta (Total Take Up), dan seberapa tinggi tingkat keberhasilan kampanye di wilayah itu (Take Up Rate).

Wilayah dengan persentase tertinggi tampil di baris pertama — persis seperti klasemen sepak bola. Kalau Anda penasaran apakah sebuah wilayah trennya naik atau turun dalam 8 minggu terakhir, cukup klik barisnya dan grafik garis akan muncul di bawah tabel secara otomatis.

**Manfaat bagi pengguna bisnis:**
- Segera tahu wilayah mana yang paling responsif terhadap kampanye
- Bandingkan kinerja antar wilayah dalam satu layar
- Pantau tren mingguan untuk memutuskan alokasi sumber daya atau eskalasi

---

## Penjelasan Teknis

### File yang Dibuat/Dimodifikasi

| File | Aksi |
|------|------|
| `frontend/src/pages/RegionalPerformancePage.tsx` | Dibuat — komponen utama halaman |
| `frontend/src/pages/RegionalPerformancePage.css` | Dibuat — keyframe spinner + overrides responsif |
| `frontend/src/App.tsx` | Dimodifikasi — `/regional` route diarahkan ke `<RegionalPerformancePage />` |

### Library/Framework

- **React 18** — komponen fungsi dengan hooks
- **Chart.js 4 + react-chartjs-2 5** — Line chart untuk tren 8 minggu
- **Axios** (via `api.getRegionalPerformance`) — HTTP GET ke `/api/campaigns/regional/{id}`
- **TypeScript 4.9 strict** — semua state dan props bertipe penuh
- **React Router DOM 6** — routing `/regional`

### Pola Arsitektur

1. **Controlled inputs** — `campaignId` dan `flagProgram` dikendalikan penuh oleh state React
2. **On-demand fetch** — data hanya dimuat setelah pengguna menekan tombol *Cari* atau menekan Enter; tidak ada auto-fetch saat mount
3. **Row-click selection** — `selectedRegion: number | null` menyimpan `wilayah` yang dipilih; klik baris yang sama membatalkan pilihan (toggle)
4. **Chart data derivation** — `buildTrendChartData()` memfilter `data.trend` per `wilayah` di sisi klien; tidak perlu API tambahan
5. **Inline styles + CSS** — mengikuti konvensi proyek (seperti `CampaignOverviewPage`); CSS hanya untuk `@keyframes spin` dan media query

### Keputusan Desain Penting

- Data tabel **tidak di-sort ulang di frontend** — backend sudah mengirimkan `regions` terurut `take_up_rate DESC` (sesuai Property 7 di spec). Frontend menampilkan as-is.
- Rank ditampilkan sebagai `idx + 1` karena urutan array mencerminkan rank sebenarnya.
- **Kode warna Take Up Rate**: ≥10% hijau, 5–9.99% kuning, <5% merah — memberi sinyal visual instan tanpa perlu hover.
- **Trend chart judul** menggunakan pola `"Tren 8 Minggu — Wilayah {regionName}"` sesuai spesifikasi task.

### Edge Cases yang Ditangani

| Skenario | Penanganan |
|----------|-----------|
| Campaign ID kosong | Tombol *Cari* disabled; tidak bisa di-submit |
| API error | Banner merah dengan pesan error; tidak crash |
| `regions: []` | Pesan "Tidak ada data regional" dengan panduan ubah filter |
| Tidak ada trend point untuk wilayah | Pesan "Data tren tidak tersedia untuk wilayah ini" |
| `campaign_name` kosong | Fallback ke `campaign_id` |
| `flag_program` tidak diisi | Parameter tidak dikirim ke API (bukan string kosong) |

---

## Struktur Kode

```typescript
// Helpers (pure functions, tidak mengubah state)
formatNumber(n)          → string  // format angka dengan separator ribuan id-ID
formatRate(n)            → string  // contoh: "12.34%"
formatCurrency(n)        → string  // contoh: "Rp 1.500.000"
buildTrendChartData(trend, wilayah, regionName)  → Chart.js data object
buildTrendChartOptions(regionName)               → Chart.js options object

// State utama
campaignId: string         // input Campaign ID
flagProgram: string        // filter program ('', 'PROGRAM QRIS', 'PROGRAM BIAYA ADMIN')
selectedRegion: number | null  // wilayah yang sedang dipilih
data: RegionalPerformanceResponse | null
loading: boolean
error: string | null

// Handler
handleFetch()       // panggil api.getRegionalPerformance, update state
handleKeyDown()     // Enter di input → handleFetch
handleRowClick(wilayah)  // toggle selectedRegion
```

---

## Simulasi / Skenario

### Skenario 1 — Happy Path

**Input:** Campaign ID = `"CAMP-2024-001"`, Program = `"PROGRAM QRIS"`

**Proses:**
1. Pengguna klik *Cari*
2. `api.getRegionalPerformance("CAMP-2024-001", "PROGRAM QRIS")` dipanggil
3. Response: 12 wilayah, sudah terurut take_up_rate DESC
4. Tabel menampilkan 12 baris; baris pertama = Wilayah Jawa Barat (take_up_rate 18.5%)

**Output:**
```
Rank | Wilayah         | Total Leads | Total Take Up | Take Up Rate | Avg. Transaksi
  1  | Jawa Barat (W3) |   12,450    |    2,303      |   18.50% 🟢 |  Rp 2.100.000
  2  | DKI Jakarta (W1)|   18,200    |    2,866      |   15.75% 🟢 |  Rp 3.500.000
  ...
```

### Skenario 2 — Pilih Wilayah untuk Tren

**Aksi:** Klik baris "Jawa Barat"

**Output:** Grafik Line Chart muncul di bawah tabel:
- Judul: `"Tren 8 Minggu — Wilayah Jawa Barat"`
- X axis: 8 tanggal `week_start` berurutan
- Y axis: take_up_rate tiap minggu

### Skenario 3 — Data Regional Kosong

**Input:** Campaign ID = `"CAMP-OLD-999"`, Program = `"PROGRAM BIAYA ADMIN"`

**Output:** Banner kuning:
> *"Tidak ada data wilayah yang tersedia untuk campaign CAMP-OLD-999 dengan program PROGRAM BIAYA ADMIN. Coba ubah filter program atau pilih campaign lain."*

### Skenario 4 — API Error

**Skenario:** Backend return 500

**Output:** Banner merah dengan pesan error dari exception; tidak ada crash; pengguna bisa ubah input dan coba lagi.

---

## Keterkaitan dengan Komponen Lain

| Hubungan | Komponen |
|----------|---------|
| **Bergantung pada** | `DashboardLayout` (shell + navigasi), `useAuth` (username + sign-out), `api.getRegionalPerformance` (HTTP layer), types `RegionalPerformanceResponse`, `RegionMetric`, `RegionalTrendPoint` |
| **Digunakan oleh** | `App.tsx` via route `/regional` |
| **Pengaruh ke** | Jika signature `api.getRegionalPerformance` berubah, halaman ini perlu disesuaikan |

---

## Requirements yang Dipenuhi

| Requirement | Deskripsi |
|-------------|-----------|
| **4.1** | Tabel wilayah diurutkan berdasarkan take_up_rate DESC |
| **4.2** | Grafik tren 8 minggu per wilayah ditampilkan saat baris diklik |
| **4.3** | Filter flag_program terintegrasi (select dropdown) |
| **4.4** | Pesan kosong yang informatif saat tidak ada data regional |
| **4.5** | Input Campaign ID dengan validasi (tidak bisa fetch jika kosong) |

---

## Catatan Penting

- **Sorting dilakukan di backend**, bukan frontend. Jika backend mengembalikan urutan berbeda, urutan tabel akan mengikuti respons backend.
- Komponen **tidak melakukan auto-fetch saat pertama render** — data hanya dimuat setelah pengguna mengisi Campaign ID dan menekan *Cari*. Ini menghindari API call yang tidak perlu saat halaman pertama dibuka.
- **Toggle selection**: klik baris yang sama dua kali akan menutup grafik tren (mekanisme toggle `selectedRegion`).
- **Limit 8 minggu** dijaga di fungsi `buildTrendChartData` dengan `.slice(-8)` sebagai guard, meskipun backend seharusnya sudah membatasi.
- Todo: tambahkan kemampuan export tabel regional ke CSV setelah task 11.7 (Export Service) selesai.
