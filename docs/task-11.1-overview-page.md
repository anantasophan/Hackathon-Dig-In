# Task 11.1 — Campaign Overview Page

## Ringkasan Singkat

Halaman Campaign Overview adalah halaman utama dashboard yang ditampilkan pertama kali saat pengguna login. Halaman ini menampilkan tiga metrik agregat (Total Leads, Total Take Up, Take-Up Rate), grafik tren take-up rate dalam bentuk line chart, dan panel filter di sisi kiri. Setiap perubahan filter akan memicu pengambilan data baru dari API secara otomatis.

---

## Penjelasan Awam (Non-Technical)

**Bayangkan sebuah dasbor mobil**: ketika Anda nyalakan mesin, langsung terlihat kecepatan, bensin, dan suhu mesin — semua di satu tempat.

Halaman Campaign Overview bekerja seperti itu untuk kampanye pemasaran:
- **Total Leads** = berapa banyak nasabah yang dikirimkan pesan kampanye
- **Total Take Up** = berapa yang akhirnya melakukan transaksi
- **Take-Up Rate** = persentase keberhasilan kampanye (misal: 12.50%)
- **Grafik tren** = apakah persentase keberhasilan naik atau turun dari waktu ke waktu?

Di sisi kiri ada **panel filter** yang memungkinkan pengguna mempersempit data — misalnya hanya melihat kampanye QRIS di Wilayah 5 melalui channel WhatsApp dalam 3 bulan terakhir.

Manfaat untuk pengguna bisnis: bisa langsung melihat kesehatan kampanye secara keseluruhan dan mengidentifikasi tren tanpa perlu mengolah data manual.

---

## Penjelasan Teknis

### File yang Dibuat/Dimodifikasi

| File | Status | Keterangan |
|------|--------|------------|
| `frontend/src/pages/CampaignOverviewPage.tsx` | ✅ Dibuat | Komponen utama halaman |
| `frontend/src/pages/CampaignOverviewPage.css` | ✅ Dibuat | Styling BEM untuk halaman |

### Library/Framework yang Digunakan

- **React 18** — komponen fungsional dengan hooks (`useState`, `useEffect`, `useCallback`)
- **Chart.js + react-chartjs-2** — line chart untuk tren take-up rate
- **TypeScript strict mode** — type safety penuh
- **AWS Amplify Auth** — via `useAuth` hook untuk session management

### Pola Arsitektur

1. **Filter-driven fetch**: `FilterPanel` memanggil `onFilterChange` setiap kali pengguna klik Apply/Reset. Callback ini di-pass langsung ke `fetchOverview` → tidak ada state filter di parent, hanya data hasil fetch.

2. **API layer**: `api.getCampaignOverview(params)` dari `services/api.ts` — menggunakan Axios dengan request interceptor untuk JWT dan response interceptor untuk error mapping.

3. **Error taxonomy**: Menggunakan typed error classes:
   - `ApiTimeoutError` → pesan timeout spesifik dalam Bahasa Indonesia
   - Error lainnya → pesan generik dari `err.message`

4. **Empty state detection**: Backend mengembalikan field `message` ketika tidak ada data yang cocok — halaman mendeteksi ini dan menampilkan empty state daripada crash.

5. **Response time indicator**: Menggunakan `performance.now()` untuk mengukur latensi setiap request — ditampilkan sebagai badge hijau (< 5 detik) atau kuning (≥ 5 detik).

### Keputusan Desain Penting

- **BEM CSS classes** digunakan (bukan inline styles) untuk mendukung theming, responsiveness via media queries, dan print stylesheet.
- **Line color `#2b6cb0`** (bukan `#3182ce`) sesuai spesifikasi task.
- **`filterStateToRequest`** memeta `FilterState` → `CampaignOverviewRequest`, dengan mengonversi array kosong ke `undefined` agar tidak mengirimkan parameter filter kosong ke backend.
- **`Filler` plugin Chart.js** didaftarkan untuk mendukung `fill: true` pada dataset (area di bawah garis).

### Edge Cases yang Ditangani

- Response dengan field `message` → empty state, bukan data kosong
- `ApiTimeoutError` → pesan khusus "Coba persempit filter"
- `trend.length === 0` → placeholder teks daripada chart kosong yang membingungkan
- `data.filters.length === 0` → tidak menampilkan filter summary
- Initial load otomatis dengan rentang 3 bulan terakhir (tanpa perlu user klik Apply)

---

## Struktur Kode

### Fungsi/Komponen Utama

```typescript
// Konversi FilterState ke CampaignOverviewRequest
function filterStateToRequest(filters: FilterState): CampaignOverviewRequest

// Format angka dengan pemisah ribuan: 12345 → "12.345"
function formatNumber(n: number): string

// Format persentase: 12.5 → "12.50%"
function formatRate(n: number): string

// Build data object untuk Chart.js Line chart
function buildChartData(trend: TrendDataPoint[]): ChartData

// Kartu metrik individual (label + value + icon)
const MetricCard: React.FC<MetricCardProps>

// Spinner loading state
const LoadingSpinner: React.FC

// Komponen halaman utama
const CampaignOverviewPage: React.FC  // default export
```

### State yang Dikelola

```typescript
const [data, setData] = useState<CampaignOverviewResponse | null>(null);
const [loading, setLoading] = useState(false);
const [error, setError] = useState<string | null>(null);
const [emptyMessage, setEmptyMessage] = useState<string | null>(null);
const [responseMs, setResponseMs] = useState<number | null>(null);
```

---

## Simulasi / Skenario

### Skenario 1 — Happy Path (Data Tersedia)

**Input**: Pengguna membuka halaman, filter default (3 bulan terakhir, semua program)

**Proses**:
1. `useEffect` memanggil `fetchOverview(defaultFilters)` saat mount
2. `loading = true` → spinner ditampilkan
3. `api.getCampaignOverview({ start_date: "2025-04-01", end_date: "2025-07-01" })` dipanggil
4. Response diterima dalam 2.3 detik

**Output**:
```
Total Leads:    45,230
Total Take Up:  5,628
Take-Up Rate:   12.44%
[Line chart menampilkan 12 titik data mingguan]
Badge: ✓ <5s (hijau)
```

### Skenario 2 — Filter Menghasilkan Data Kosong

**Input**: Pengguna memilih Wilayah 17 + PROGRAM QRIS + channel "push notif" (kombinasi tidak ada data)

**Proses**:
1. Backend merespons dengan `{ message: "Tidak ada data untuk filter yang dipilih" }`
2. `maybeEmpty.message` truthy → `setEmptyMessage(...)`, `setData(null)`

**Output**:
```
📭 Tidak ada data yang cocok
"Tidak ada kampanye yang sesuai dengan filter yang dipilih..."
```

### Skenario 3 — Timeout

**Input**: Query berat ke Athena, server merespons 408 setelah 30 detik

**Proses**:
1. `ApiTimeoutError` dilempar oleh response interceptor
2. `catch (err)` → `err instanceof ApiTimeoutError` → pesan khusus

**Output**:
```
⚠️ Query membutuhkan waktu terlalu lama. Coba persempit filter atau coba kembali.
```

---

## Keterkaitan dengan Komponen Lain

**Bergantung pada:**
- `DashboardLayout` — wrapper layout dengan sidebar navigasi dan header
- `FilterPanel` — panel filter dengan callback `onFilterChange`
- `api.getCampaignOverview()` — API call ke backend Lambda
- `useAuth` hook — session user dan fungsi sign-out
- `CampaignOverviewRequest` / `CampaignOverviewResponse` / `TrendDataPoint` types

**Digunakan oleh:**
- `App.tsx` — di-render pada route `/overview`

**Pengaruh ke:**
- Perubahan `FilterState` interface di `types/filters.ts` → perlu update `filterStateToRequest`
- Perubahan `CampaignOverviewResponse` di `types/api.ts` → perlu update render logic
- Perubahan endpoint `/api/campaigns/overview` → perlu update `api.ts`

---

## Requirements yang Dipenuhi

| Requirement | Deskripsi |
|-------------|-----------|
| 1.1 | Dashboard dengan ringkasan metrik kampanye |
| 1.2 | Total Leads, Total Take Up, Take-Up Rate ditampilkan |
| 1.3 | Integrasi FilterPanel — filter berdasarkan periode, produk, channel, wilayah |
| 1.4 | Refresh data saat filter berubah (callback `onFilterChange`) |
| 1.5 | Empty state ketika tidak ada data cocok dengan filter |
| 1.6 | Loading state saat fetch berlangsung |
| 1.7 | Indikator respons < 5 detik (badge hijau/kuning) |

---

## Catatan Penting

1. **Line chart color**: Menggunakan `#2b6cb0` sesuai spesifikasi, bukan `#3182ce` yang dipakai di Comparison page.

2. **Filler plugin**: `Filler` dari Chart.js harus didaftarkan secara eksplisit untuk `fill: true` pada line chart. Tanpa ini area di bawah garis tidak dirender.

3. **Performance.now() timing**: Waktu diukur dari sebelum `api.getCampaignOverview()` dipanggil hingga setelah response diterima. Ini mencakup network latency + Athena query time.

4. **Initial load**: Halaman langsung memuat data dengan filter default 3 bulan terakhir saat pertama dibuka — pengguna tidak perlu klik "Apply".

5. **Locale formatting**: `toLocaleString('id-ID')` menggunakan titik sebagai pemisah ribuan (e.g. `45.230`) sesuai konvensi Indonesia.

6. **Todo**: Tambahkan tombol "Retry" setelah error state untuk memudahkan pengguna mencoba ulang tanpa harus mengubah filter.
