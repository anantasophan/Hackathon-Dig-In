# Task UI 10.1 — RegionalPerformancePage: Tailwind CSS Rewrite

## Ringkasan Singkat

Task ini memverifikasi dan menyempurnakan refactor penuh `RegionalPerformancePage.tsx` agar sepenuhnya menggunakan Tailwind CSS, menghapus semua `styles` object berbasis `React.CSSProperties`, mengganti emoji dengan ikon Lucide React, mengimplementasikan fungsi `getTakeUpBadgeClasses()` untuk badge warna bertingkat, dan memastikan tidak ada import `RegionalPerformancePage.css` yang tersisa. Hasilnya adalah halaman Performa Regional yang sepenuhnya mengikuti BNI Design System — konsisten dengan halaman lainnya di aplikasi.

---

## Penjelasan Awam (Non-Technical)

Bayangkan sebuah aplikasi bank yang menampilkan performa kampanye di 17 wilayah Indonesia. Di setiap baris tabel, ada badge warna yang menunjukkan seberapa bagus performa wilayah itu: **hijau** berarti sangat baik (Take Up Rate ≥ 10%), **kuning** berarti sedang (5–9.99%), dan **merah** berarti perlu perhatian (< 5%).

Sebelumnya, badge-badge ini dihasilkan lewat kode yang "campur aduk" — sebagian warnanya diatur secara langsung via JavaScript (inline styles), sebagian lagi dari file CSS terpisah. Ini seperti dekorasi toko yang sebagian dipasang permanen di dinding (file CSS), sebagian lagi ditempel pakai pita perekat sementara (inline styles) — hasilnya tidak rapi dan sulit dipelihara.

Setelah refactor ini, semua warna badge dikelola lewat satu fungsi bersih (`getTakeUpBadgeClasses`), dan seluruh tampilan menggunakan Tailwind CSS — satu sistem yang konsisten, sama seperti semua halaman lainnya di aplikasi.

**Manfaat bisnis:**
- Tampilan lebih profesional dan sesuai identitas visual BNI
- Tidak ada emoji seperti 🗺️ atau ⚠️ yang terkesan tidak formal
- Badge warna langsung menginformasikan status performa — analis bisa membaca data lebih cepat

---

## Penjelasan Teknis

### File yang Diverifikasi / Dimodifikasi

| File | Tindakan |
|------|----------|
| `frontend/src/pages/RegionalPerformancePage.tsx` | Diverifikasi sudah full Tailwind — tidak ada `styles` object, tidak ada CSS import, tidak ada emoji |
| `frontend/src/components/StateComponents.tsx` | Dikonfirmasi: `LoadingState`, `EmptyState`, `ErrorState` dengan Lucide icons sudah digunakan |

### Library yang Digunakan

- **Tailwind CSS 3.4.1** — seluruh styling
- **Lucide React 0.378.0** — `MapPin` (idle state), `Loader2` (via `LoadingState`), `AlertCircle` (via `ErrorState`), `Inbox` (via `EmptyState`)
- **chart.js + react-chartjs-2** — grafik tren 8 minggu per wilayah
- **`@testing-library/react` + `fast-check`** — digunakan di Task 10.2 untuk property test `getTakeUpBadgeClasses`

### Pola Arsitektur yang Diterapkan

**Badge sebagai pure function:**
```tsx
export function getTakeUpBadgeClasses(rate: number): string {
  if (rate >= 10) return 'bg-emerald-100 text-emerald-700 rounded px-1.5 py-0.5 text-xs font-semibold';
  if (rate >= 5)  return 'bg-amber-100 text-amber-700 rounded px-1.5 py-0.5 text-xs font-semibold';
  return 'bg-rose-100 text-rose-700 rounded px-1.5 py-0.5 text-xs font-semibold';
}
```

Fungsi ini di-`export` agar bisa diuji secara unit di Task 10.2. Setiap cabang mengembalikan **full class string** — tidak ada konstruksi string dinamis parsial, memastikan Tailwind JIT compiler dapat men-scan semua class yang digunakan.

**Shared state components:**
Semua kondisi loading/empty/error didelegasikan ke `StateComponents.tsx`:
- `<LoadingState />` → `Loader2 animate-spin text-[#005E6A]`
- `<EmptyState />` → `Inbox w-8 h-8 text-gray-300` + teks formal
- `<ErrorState message="..." />` → `AlertCircle text-rose-400` + teks merah

**Idle state tetap inline** di halaman ini (saat user belum mengetik Campaign ID), karena teksnya spesifik untuk konteks regional (bukan pattern generik):
```tsx
<MapPin className="w-8 h-8 mx-auto mb-2 text-gray-300" />
<p className="text-sm font-medium">Belum ada data ditampilkan</p>
<p className="text-xs mt-1">Masukkan Campaign ID di atas...</p>
```

**Row selection dengan visual ring:**
```tsx
className={`cursor-pointer hover:bg-slate-50 transition-colors${
  isSelected ? ' ring-2 ring-inset ring-[#005E6A]' : ''
}`}
```

### Keputusan Desain Penting

1. **`getTakeUpBadgeClasses` di-export** — memungkinkan property test di Task 10.2 menguji fungsi ini secara langsung tanpa perlu me-render komponen penuh.

2. **Chart.js inline style diizinkan** — `style={{ height: '340px' }}` pada wrapper Chart.js adalah satu-satunya pengecualian inline style yang diizinkan oleh design spec, karena `react-chartjs-2` membutuhkan dimensi eksplisit.

3. **Ternary dengan full strings** — penentuan kelas `tdBase` menggunakan ternary bersarang dengan **full class strings** di setiap cabang, bukan konstruksi parsial:
   ```tsx
   const tdBase = isSelected
     ? 'px-3 py-2.5 bg-[#005E6A]/10 border-b border-[#005E6A]/20 text-xs'
     : idx % 2 === 0
     ? 'px-3 py-2.5 bg-white border-b border-gray-100 text-xs'
     : 'px-3 py-2.5 bg-slate-50 border-b border-gray-100 text-xs';
   ```

### Edge Cases yang Ditangani

- Campaign ID kosong → tombol Cari disabled (`bg-gray-300 cursor-not-allowed`)
- Region tanpa data tren → `EmptyState` spesifik di panel chart bawah
- Tren guard: `slice(-8)` memastikan maksimal 8 titik data meskipun backend mengirim lebih
- `selectedRegion` di-reset ke `null` setiap kali fetch baru dimulai
- Keyboard navigation: row tabel bisa diaktifkan dengan Enter/Space

---

## Struktur Kode

### Fungsi Utama

| Signature | Deskripsi |
|-----------|-----------|
| `export function getTakeUpBadgeClasses(rate: number): string` | Mengembalikan Tailwind class string untuk badge berdasarkan 3 tier rate: ≥10% (emerald), ≥5% (amber), <5% (rose). Di-export untuk testability. |
| `function formatNumber(n: number): string` | Format angka dengan pemisah ribuan Indonesia (`id-ID`), contoh: `12345` → `"12.345"` |
| `function formatRate(n: number): string` | Format rate sebagai persentase 2 desimal, contoh: `8.5` → `"8.50%"` |
| `function formatCurrency(n: number): string` | Format nilai transaksi dalam IDR, contoh: `1500000` → `"Rp 1.500.000"` |
| `function buildTrendChartData(trend, wilayah, regionName)` | Filter tren berdasarkan wilayah, ambil 8 titik terakhir, bangun Chart.js dataset dengan BNI Teal `#005E6A` |
| `function buildTrendChartOptions(regionName)` | Konfigurasi Chart.js: legend, title, tooltip dengan format `%`, axis labels slate-400, grid slate-50 |
| `const RegionalPerformancePage: React.FC` | Komponen utama. Mengelola state `campaignId`, `flagProgram`, `selectedRegion`, `data`, `loading`, `error`. |

### Konstanta

```tsx
const FLAG_PROGRAM_OPTIONS: { value: string; label: string }[] = [
  { value: '', label: 'Semua Program' },
  { value: 'PROGRAM QRIS', label: 'PROGRAM QRIS' },
  { value: 'PROGRAM BIAYA ADMIN', label: 'PROGRAM BIAYA ADMIN' },
];
```

---

## Simulasi / Skenario

### Skenario 1 — Analis Melihat Performa Wilayah QRIS

**Konteks:** Ahmad, analis kampanye BNI, ingin tahu wilayah mana yang paling sukses dalam kampanye QRIS periode Juli 2025.

**Input:**
- Campaign ID: `QRS-2025-07-001`
- Program: `PROGRAM QRIS`
- Klik tombol "Cari"

**Proses:**
1. `handleFetch()` dipanggil → `setLoading(true)`, `setData(null)`, `setSelectedRegion(null)`
2. `<LoadingState />` ditampilkan → spinner `Loader2 animate-spin text-[#005E6A]`
3. `api.getRegionalPerformance('QRS-2025-07-001', 'PROGRAM QRIS')` berhasil
4. `setData(response)` dengan 17 region, diurutkan descending berdasarkan `take_up_rate`

**Output — tabel 3 wilayah teratas:**
```
Rank | Wilayah         | Total Leads | Total Take Up | Take Up Rate        | Avg. Transaksi
1    | Wilayah Jakarta | 2.450        | 312           | [hijau] 12.73%      | Rp 285.000
2    | Wilayah Jawa    | 1.890        | 158           | [kuning] 8.36%      | Rp 210.000
3    | Wilayah Bali    | 750          | 28            | [merah] 3.73%       | Rp 195.000
```

- Badge hijau (`bg-emerald-100 text-emerald-700`) karena rate 12.73% ≥ 10%
- Badge kuning (`bg-amber-100 text-amber-700`) karena rate 8.36% → 5 ≤ rate < 10
- Badge merah (`bg-rose-100 text-rose-700`) karena rate 3.73% < 5%

### Skenario 2 — Melihat Tren 8 Minggu

**Konteks:** Ahmad mengklik baris "Wilayah Jakarta" untuk melihat tren historis.

**Proses:**
1. `handleRowClick(1)` dipanggil → `setSelectedRegion(1)`
2. Row mendapat `ring-2 ring-inset ring-[#005E6A]` dan cell `bg-[#005E6A]/10`
3. `buildTrendChartData(data.trend, 1, 'Jakarta')` memfilter tren untuk `wilayah === 1`
4. Chart.js Line chart muncul dengan 8 titik data mingguan

**Output — chart:**
- Garis biru-hijau BNI Teal dengan area fill semi-transparan
- X-axis: `2025-05-12`, `2025-05-19`, ..., `2025-06-30`
- Y-axis: 0% – 20% dengan label `%`
- Klik baris yang sama lagi → `selectedRegion` kembali ke `null`, chart hilang

### Skenario 3 — Campaign ID Tidak Ditemukan

**Input:** Campaign ID `NONEXISTENT-999`

**Proses:**
1. API mengembalikan `{ regions: [], trend: [] }`
2. `data.regions.length === 0` → `<EmptyState>` ditampilkan

**Output:**
```
[Inbox icon abu-abu]
Tidak ada data tersedia
Tidak ada data wilayah yang tersedia untuk campaign NONEXISTENT-999.
Coba ubah filter program atau pilih campaign lain.
```

---

## Keterkaitan dengan Komponen Lain

**Bergantung pada:**
- `StateComponents.tsx` (`EmptyState`, `LoadingState`, `ErrorState`) — digunakan untuk semua state display
- `DashboardLayout.tsx` — wrapper shell (sidebar, header)
- `api.ts` — `api.getRegionalPerformance(campaignId, flagProgram?)` untuk fetch data
- `useAuth` hook — `user.username` dan `signOut` untuk session info di sidebar
- `types/api.ts` — `RegionalPerformanceResponse`, `RegionMetric`, `RegionalTrendPoint` interfaces

**Digunakan oleh:**
- `App.tsx` (atau router config) — di-mount pada route `/regional`

**Pengaruh ke:**
- Task 10.2 (`PropertyTest.takeupbadge.test.tsx`) — mengimpor `getTakeUpBadgeClasses` dari file ini untuk property testing. Jika signature fungsi berubah, test perlu diperbarui.
- Tidak ada halaman lain yang mengimpor komponen dari file ini

---

## Requirements yang Dipenuhi

| Requirement | Deskripsi |
|-------------|-----------|
| **8.1** | Seluruh layout menggunakan Tailwind — tidak ada `styles` object `React.CSSProperties` |
| **8.2** | Filter card: `bg-white p-4 border border-gray-200 rounded-xl shadow-sm` |
| **8.3** | Tombol Cari: `bg-[#005E6A] hover:bg-[#004852] text-white font-semibold rounded-lg` |
| **8.4** | Form label: `text-xs font-bold uppercase tracking-wider text-gray-600` |
| **8.5** | Badge rate tinggi (≥10%): `bg-emerald-100 text-emerald-700` |
| **8.6** | Badge rate sedang (5–9.99%): `bg-amber-100 text-amber-700` |
| **8.7** | Badge rate rendah (<5%): `bg-rose-100 text-rose-700` |
| **8.8** | Loading: `Loader2 animate-spin text-[#005E6A]` via `LoadingState` |
| **8.9** | Idle state: `MapPin` Lucide icon — bukan emoji 🗺️ |
| **8.10** | Empty state: `Inbox` Lucide icon via `EmptyState` — bukan emoji 📭 |
| **8.11** | Error state: `AlertCircle` Lucide icon via `ErrorState` — bukan emoji ⚠️ |
| **8.12** | Tidak ada inline styles kecuali Chart.js wrapper `style={{ height: '340px' }}` |
| **8.13** | Tidak ada emoji di manapun dalam komponen ini |

---

## Catatan Penting

### Limitasi yang Diketahui
- `RegionalPerformancePage.css` masih ada di filesystem sebagai file. File ini **tidak diimpor** di manapun dan akan dihapus di Task 15.1 (bulk CSS deletion).
- Fungsi `getTakeUpBadgeClasses` menggunakan `rate >= 5` sebagai batas bawah tier amber — rate persis `5.0` masuk amber, bukan rose. Ini sesuai requirements (5–9.99% = sedang).

### Asumsi yang Dibuat
- Backend mengembalikan `regions` sudah dalam urutan descending `take_up_rate` — halaman tidak melakukan sorting ulang.
- Backend mengembalikan `trend` sudah diurutkan ascending berdasarkan `week_start` — `slice(-8)` mengambil 8 data terbaru.
- `wilayah` di Indonesia menggunakan kode integer 1–17 sesuai domain data model.

### Todo untuk Pengembangan Berikutnya
- Tambah fitur perbandingan antar wilayah (multi-select row dengan chart overlay)
- Tambah export tabel performa regional ke CSV/Excel
- Pagination jika jumlah wilayah > 17 (saat ini hardcoded 17 wilayah BNI)
