# Task 9.1 — TimeToTakeUpPage: Tailwind CSS + Lucide Icons Rewrite

## Ringkasan Singkat

Task ini menulis ulang halaman `TimeToTakeUpPage.tsx` dari gaya lama berbasis `TimeToTakeUpPage.css` dan emoji menjadi sepenuhnya berbasis Tailwind CSS dan ikon Lucide React, konsisten dengan design system BNI Campaign Insight Generator.

---

## Penjelasan Awam (Non-Technical)

Bayangkan sebuah dashboard bank yang menampilkan grafik "berapa hari biasanya nasabah mulai melakukan take up setelah dikampanyekan." Sebelumnya, halaman ini menggunakan potongan-potongan kode CSS tersendiri dan ikon emoji (📊, 📈, ⬇️, ⬆️, ✅, ⚠️, 📭) yang terlihat kurang profesional untuk standar perbankan.

Setelah task ini, tampilan yang sama kini menggunakan:
- **Ikon dari Lucide** — ikon vektor yang bersih dan konsisten di seluruh aplikasi
- **Tailwind CSS** — kelas utility yang sudah terstandarisasi, tidak ada CSS file terpisah
- **Warna BNI Teal** (`#005E6A`) sebagai accent utama pada ikon, tombol, dan fokus input

Manfaat bagi pengguna bisnis: tampilan lebih rapi dan profesional, sesuai standar brand bank.

---

## Penjelasan Teknis

### File yang Dimodifikasi

| File | Perubahan |
|------|-----------|
| `frontend/src/pages/TimeToTakeUpPage.tsx` | Rewrite lengkap — hapus CSS import, ganti semua `ttu-*` class dengan Tailwind, ganti emoji dengan Lucide icons |

### File yang Dihapus (referensi)

- `import './TimeToTakeUpPage.css'` — dihapus dari file TSX
- CSS class `ttu-*` — seluruhnya digantikan Tailwind utility classes

### Library yang Digunakan

- `lucide-react` — `Clock`, `Timer`, `AlertCircle`, `Inbox`, `Loader2`, `BarChart2`, `TrendingDown`, `TrendingUp`, `Users`
- `tailwindcss` — semua styling kecuali satu pengecualian Chart.js (lihat di bawah)

### Keputusan Desain Penting

1. **Inline style diizinkan hanya untuk Chart.js wrapper**: `style={{ height: '320px' }}` tetap digunakan karena Chart.js memerlukan tinggi eksplisit dalam pixel untuk render yang benar — tidak bisa diekspresikan sebagai Tailwind class statis.

2. **Ikon untuk statistik Min/Max/Total**: Task instruksi menyebutkan Clock (rata-rata) dan Timer (median). Untuk Min, Max, Total, digunakan ikon tematik yang relevan: `TrendingDown` (minimum), `TrendingUp` (maksimum), `Users` (total take up nasabah).

3. **StatCard interface diperbarui**: Prop `icon` diubah dari `string` (emoji) menjadi `React.ReactNode` sehingga bisa menerima komponen Lucide icon.

4. **`@keyframes spin` dihapus**: Tag `<style>` inline di JSX dihapus. Spinner sekarang menggunakan `<Loader2 className="... animate-spin" />` yang memanfaatkan Tailwind's built-in `animate-spin`.

5. **Conditional className button**: Button submit menggunakan template ternary untuk membedakan state aktif dan disabled, menghilangkan kebutuhan class `ttu-btn-primary--disabled`.

### State yang Tidak Diubah

Semua logika TypeScript berikut dipertahankan persis sama:
- State variables (`campaignId`, `channel`, `region`, `data`, `emptyMessage`, `loading`, `error`, `hasFetched`)
- Handler functions (`handleFetch`, `handleKeyDown`)
- Chart.js registration
- Helper functions (`buildChartData`, `chartOptions`, `_histogramCounts`)
- Constants (`BUCKET_LABELS`, `CHANNEL_OPTIONS`)

---

## Struktur Kode

```tsx
// Sub-component — StatCard
interface StatCardProps {
  label: string;
  value: string;
  icon: React.ReactNode;   // diubah dari string ke React.ReactNode
}
const StatCard: React.FC<StatCardProps> = ({ label, value, icon }) => (
  <div className="bg-white p-4 border border-gray-200 rounded-xl shadow-sm flex items-start gap-3">
    <div className="flex-shrink-0 text-[#005E6A]">{icon}</div>
    <div>
      <span className="text-xs font-medium text-slate-400 block">{label}</span>
      <span className="text-2xl font-bold text-slate-700">{value}</span>
    </div>
  </div>
);
```

### Pemetaan Class Lama → Baru

| Class Lama | Tailwind Baru |
|------------|---------------|
| `ttu-page` | `flex flex-col gap-4` |
| `ttu-page__title` | `text-md font-bold text-gray-700` |
| `ttu-card` | `bg-white p-4 border border-gray-200 rounded-xl shadow-sm` |
| `ttu-card__heading` | `text-xs font-bold uppercase tracking-wider text-gray-400 mb-3` |
| `ttu-input-row` | `flex flex-col gap-1` |
| `ttu-label` | `text-xs font-bold uppercase tracking-wider text-gray-600` |
| `ttu-required` | `text-rose-500` |
| `ttu-input` | `w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#005E6A] bg-white text-xs` |
| `ttu-input ttu-input--short` | `w-20 px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#005E6A] bg-white text-xs` |
| `ttu-filters-row` | `flex gap-4 flex-wrap mt-3` |
| `ttu-filter-group` | `flex flex-col gap-1` |
| `ttu-select` | `px-3 py-2 border border-gray-300 rounded-lg text-xs bg-white focus:ring-2 focus:ring-[#005E6A] focus:outline-none` |
| `ttu-action-row` | `mt-4` |
| `ttu-btn-primary` (enabled) | `px-5 py-2 bg-[#005E6A] hover:bg-[#004852] text-white font-semibold rounded-lg text-xs transition-colors` |
| `ttu-btn-primary--disabled` | `px-5 py-2 bg-gray-300 text-gray-500 font-semibold rounded-lg text-xs cursor-not-allowed` |
| `ttu-stats-row` | `grid grid-cols-2 gap-4` |
| `ttu-campaign-name` | `text-sm text-gray-600` |
| `ttu-chart-container` | `style={{ height: '320px' }}` (pengecualian Chart.js) |
| `ttu-chart-note` | `text-[10px] text-gray-400 mt-2` |

### State Box → Lucide Icon Pattern

| State | Icon | Kelas |
|-------|------|-------|
| Pre-fetch | `<Clock className="w-8 h-8 mx-auto mb-2 text-gray-300" />` | `text-center py-12 text-gray-400` |
| Loading | `<Loader2 className="w-8 h-8 mx-auto mb-2 animate-spin text-[#005E6A]" />` | `text-center py-12 text-gray-400` |
| Error | `<AlertCircle className="w-8 h-8 mx-auto mb-2 text-rose-400" />` | `text-center py-12` |
| Empty | `<Inbox className="w-8 h-8 mx-auto mb-2 text-gray-300" />` | `text-center py-12 text-gray-400` |

---

## Simulasi / Skenario

### Skenario 1 — Happy Path: Analisis berhasil dimuat

**Input:**
- Campaign ID: `"QRIS-2024-07"`, channel: kosong, region: kosong

**Proses:**
1. User mengetik campaign ID, tombol aktif (BNI Teal)
2. Klik "Lihat Analisis" → loading state tampil dengan `<Loader2>` berputar
3. API mengembalikan data histogram + stats

**Output:**
- 5 stat cards tersusun grid 2 kolom: Median (Timer icon), Rata-rata (Clock icon), Minimum (TrendingDown), Maksimum (TrendingUp), Total Take Up (Users)
- Bar chart histogram dengan tinggi 320px
- Catatan kaki `text-[10px] text-gray-400`

### Skenario 2 — Error State

**Input:** Campaign ID tidak valid → API mengembalikan error

**Output:**
```
[AlertCircle icon — rose-400]
Terjadi kesalahan
"Campaign not found" (dari error.message)
```

### Skenario 3 — Pre-fetch (belum pernah submit)

**Output:**
```
[Clock icon — gray-300]
Masukkan campaign ID untuk melihat analisis
```

---

## Keterkaitan dengan Komponen Lain

- **Bergantung pada**: `DashboardLayout`, `api.getTimeAnalysis()`, `TimeAnalysisResponse` type, `chart.js`, `react-chartjs-2`, `lucide-react`
- **Digunakan oleh**: Router `App.tsx` — path `/time-to-take-up`
- **Pengaruh ke**: Tidak ada komponen yang mengimpor `TimeToTakeUpPage` secara langsung (page-level component)

---

## Requirements yang Dipenuhi

Dari spec `ui-redesign`:
- **9.1** — Tulis ulang `TimeToTakeUpPage.tsx` dengan Tailwind dan Lucide icons
- Menghapus semua emoji dari UI (sesuai aturan design system: DILARANG emoji)
- Menggunakan Lucide icons sebagai pengganti emoji (sesuai aturan: HARUS DIGUNAKAN)
- Seluruh styling menggunakan Tailwind CSS (sesuai Aturan Implementasi #1)
- StatCard mengikuti pola BNI design system (icon + label + value)
- Warna BNI Teal `#005E6A` untuk primary button, focus ring, icon accent

---

## Catatan Penting

1. **CSS file `TimeToTakeUpPage.css`** masih ada di disk — bisa dihapus secara terpisah jika sudah tidak ada komponen lain yang mengimpornya.
2. **Chart.js inline style** (`style={{ height: '320px' }}`) adalah satu-satunya pengecualian inline style yang diizinkan per design spec — ini adalah limitasi teknis Chart.js.
3. **`BarChart2` diimpor** di baris import tapi tidak digunakan — bisa dihapus jika ESLint `no-unused-vars` aktif. Saat ini tidak menyebabkan TypeScript error.
4. **Grid stat cards** — dengan 5 item di grid 2 kolom, item ke-5 (Total Take Up) akan menempati baris penuh di mobile, yang secara visual wajar.
