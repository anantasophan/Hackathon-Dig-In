# Task 4.1 (UI Redesign) — FilterPanel: Rewrite dengan Tailwind CSS & Lucide Icons

## Ringkasan Singkat

Task ini menulis ulang komponen `FilterPanel.tsx` — panel filter yang digunakan bersama di semua halaman dashboard — agar sepenuhnya menggunakan Tailwind CSS utility classes dan ikon Lucide React. File CSS lama (`FilterPanel.css`) dihapus dari import, semua karakter teks `▼▲` diganti dengan komponen ikon `ChevronDown`/`ChevronUp`, dan seluruh class berbasis BEM (`filter-panel__*`) dikonversi ke class Tailwind yang sesuai BNI Design System.

---

## Penjelasan Awam (Non-Technical)

Panel filter di dashboard adalah kotak kontrol di sisi kiri layar yang memungkinkan pengguna memilih rentang tanggal, jenis program, kanal distribusi, dan wilayah sebelum melihat data kampanye.

Sebelum task ini, tampilan panel menggunakan file CSS tersendiri yang sering tidak sinkron dengan tampilan halaman lain. Setelah task ini, panel filter menggunakan sistem desain yang sama persis dengan seluruh aplikasi — warna, ukuran teks, sudut elemen, dan tombol semua konsisten.

Analogi sederhana: seperti mengganti papan kontrol yang dibuat manual dengan papan kontrol dari pabrik yang sudah punya standar baku. Hasilnya lebih rapi, lebih mudah dirawat, dan terlihat profesional.

---

## Penjelasan Teknis

### File yang Dimodifikasi

| File | Perubahan |
|------|-----------|
| `frontend/src/components/FilterPanel.tsx` | Full rewrite: hapus import CSS, tambah Lucide import, ganti semua class BEM dengan Tailwind |

### Library yang Digunakan

- **Tailwind CSS 3.4.1** — semua styling via utility classes
- **lucide-react 0.378.0** — `ChevronDown`, `ChevronUp` untuk tombol Collapse/Expand

### Perubahan Kunci

#### Import

```tsx
// DIHAPUS
import './FilterPanel.css';

// DITAMBAHKAN
import { ChevronDown, ChevronUp } from 'lucide-react';
```

#### Container

```tsx
// Sebelum
<aside className="filter-panel" aria-label="Filter Panel">

// Sesudah
<aside className="bg-white border border-gray-200 rounded-xl shadow-sm" aria-label="Filter Panel">
```

#### Header

```tsx
// Sebelum
<div className="filter-panel__header">
  <span className="filter-panel__title">Filter</span>
  <button className="filter-panel__toggle">
    {isCollapsed ? '▼ Expand' : '▲ Collapse'}
  </button>

// Sesudah
<div className="flex items-center justify-between px-4 py-3 border-b border-gray-100">
  <span className="text-xs font-bold uppercase tracking-wider text-gray-600">Filter</span>
  <button type="button" className="flex items-center gap-1 text-xs text-gray-500 hover:text-gray-700">
    {isCollapsed ? (
      <><ChevronDown className="w-4 h-4" /><span>Expand</span></>
    ) : (
      <><ChevronUp className="w-4 h-4" /><span>Collapse</span></>
    )}
  </button>
```

#### Tombol Apply & Reset

```tsx
// Reset
<button type="button" className="flex-1 px-4 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 font-semibold rounded-lg text-xs transition-colors">
  Reset
</button>

// Apply
<button type="button" className="flex-1 px-4 py-2 bg-[#005E6A] hover:bg-[#004852] text-white font-semibold rounded-lg text-xs transition-colors">
  Apply
</button>
```

#### Input Date & Text

```tsx
<input type="date"
  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#005E6A] bg-white text-xs"
/>

<input type="text"
  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#005E6A] bg-white text-xs"
/>
```

#### CheckboxGroup (sub-komponen)

```tsx
// Fieldset
<fieldset className="space-y-2">

// Legend
<legend className="text-xs font-bold uppercase tracking-wider text-gray-600 mb-2">

// Grid checkbox
<div className="grid grid-cols-2 gap-1.5">

// Label
<label className="flex items-center gap-2 text-xs text-gray-700 cursor-pointer">

// Checkbox input
<input type="checkbox" className="rounded border-gray-300 text-[#005E6A] focus:ring-[#005E6A]">
```

### Logika yang Tidak Berubah

Semua handler (`handleDateChange`, `handleFlagProgramChange`, `handleMediaBlastingChange`, `handleWilayahChange`, `handleJenisCleadsChange`, `handleApply`, `handleReset`), state management (`useState`, `useCallback`), dan TypeScript interface (`FilterPanelProps`, `CheckboxGroupProps`) tetap identik — hanya markup/className yang berubah.

---

## Struktur Kode

| Simbol | Tipe | Deskripsi |
|--------|------|-----------|
| `toISODate(date)` | Helper function | Konversi Date object ke string `yyyy-mm-dd` |
| `buildDefaultFilters()` | Helper function | Hitung state filter default: 3 bulan lalu s/d hari ini |
| `resolveInitialFilters(initial)` | Helper function | Merge `initialFilters` prop dengan default values |
| `CheckboxGroup<T>` | Sub-komponen generik | Render fieldset + grid checkbox untuk tipe `string` atau `number` |
| `FilterPanel` | Komponen utama | Container panel filter collapsible |

---

## Simulasi / Skenario

### Skenario 1 — Panel ditampilkan dalam kondisi default (expanded)

1. Pengguna membuka halaman Campaign Overview
2. FilterPanel dirender dengan `initialFilters` tidak diberikan
3. Komponen menghitung rentang tanggal default (3 bulan lalu sampai hari ini)
4. Panel tampil terbuka, menampilkan semua fieldset dengan styling Tailwind:
   - Header: background putih, border bawah `gray-100`, label uppercase teal
   - Tombol Collapse dengan ikon `ChevronUp` di sebelah kanan header
   - Input date dengan focus ring `#005E6A` saat diklik
   - Checkbox grid 2 kolom untuk Flag Program, Media Blasting, Wilayah
   - Dua tombol di bawah: Reset (abu-abu) dan Apply (teal `#005E6A`)

### Skenario 2 — Pengguna collapse dan expand panel

1. Pengguna klik tombol "Collapse" (ada ikon `ChevronUp`)
2. Body panel disembunyikan (`isCollapsed = true`)
3. Tombol berganti menjadi `ChevronDown` + teks "Expand"
4. Pengguna klik lagi → panel terbuka kembali, tombol kembali ke `ChevronUp`

### Skenario 3 — Pengguna apply filter dan reset

1. Pengguna pilih rentang tanggal, centang "PROGRAM QRIS", pilih channel "wa"
2. Klik Apply → `onFilterChange(filters)` dipanggil dengan state terkini
3. Halaman parent fetch data baru sesuai filter
4. Pengguna klik Reset → filter kembali ke default, `onFilterChange(defaultFilters)` dipanggil

---

## Keterkaitan dengan Komponen Lain

- **Bergantung pada**: `FilterState` dan `FilterChangeHandler` dari `../types/filters`, `lucide-react`
- **Digunakan oleh**: `CampaignOverviewPage`, `TimeToTakeUpPage`, `CustomerCriteriaPage`, dan halaman lain yang butuh filter
- **Pengaruh ke**: Perubahan pada interface `FilterState` di `types/filters.ts` akan memerlukan update pada handler dan state di FilterPanel

---

## Requirements yang Dipenuhi

| Requirement | Deskripsi |
|-------------|-----------|
| 3.1 | Seluruh styling menggunakan Tailwind CSS — tidak ada import `FilterPanel.css` |
| 3.2 | Label fieldset dengan class `text-xs font-bold uppercase tracking-wider text-gray-600` |
| 3.3 | Tombol Collapse/Expand menggunakan ikon Lucide `ChevronUp`/`ChevronDown` |
| 3.4 | Tombol Apply: `bg-[#005E6A] hover:bg-[#004852] text-white font-semibold rounded-lg` |
| 3.5 | Tombol Reset: `bg-gray-100 hover:bg-gray-200 text-gray-700 font-semibold rounded-lg` |
| 3.6 | Input date & text: `border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#005E6A] text-xs` |
| 3.7 | Container: `bg-white border border-gray-200 rounded-xl shadow-sm` |
| 3.8 | Tidak ada emoji di manapun dalam komponen |

---

## Catatan Penting

- `FilterPanel.css` belum dihapus dari filesystem pada task ini — penghapusan file CSS dilakukan di task 15.1. Task ini hanya menghapus **import**-nya dari `FilterPanel.tsx`.
- Tidak ada `style={}` inline di komponen ini — semua styling via Tailwind class literals.
- Semua Tailwind class ditulis sebagai full string literals (tidak dikonstruksi secara dinamis), sehingga Tailwind purger dapat mendeteksinya dengan benar.
- Komponen `CheckboxGroup` adalah generik (`T extends string | number`) — tipe ini dipertahankan untuk mendukung wilayah berupa `number[]` dan channel berupa `string[]`.
- TypeScript diagnostics: **0 errors** setelah rewrite.
