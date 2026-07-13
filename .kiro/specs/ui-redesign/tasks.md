# Implementation Plan: UI Redesign — BNI Design System

## Overview

Refactor menyeluruh frontend Campaign Insight Generator agar sesuai dengan BNI Design System. Implementasi mengikuti urutan wave dari design.md: foundation (Tailwind config), shared components (DashboardLayout, FilterPanel, ExportService), halaman-halaman (6 page), lalu verifikasi akhir dan penghapusan file CSS lama.

Stack: React + TypeScript (Create React App), Tailwind CSS 3.4.1, Lucide React 0.378.0.

---

## Tasks

- [x] 1. Instalasi dependensi dan konfigurasi Tailwind CSS
  - [x] 1.1 Update `frontend/package.json` dengan versi dependensi yang dipinned
    - Tambahkan `"tailwindcss": "3.4.1"` dan `"lucide-react": "0.378.0"` ke `dependencies`
    - Tambahkan `"autoprefixer": "10.4.19"` dan `"postcss": "8.4.38"` ke `devDependencies`
    - _Requirements: 1.1, 1.2, 1.3_

  - [x] 1.2 Buat `frontend/tailwind.config.js` dengan BNI color tokens dan Inter font
    - Definisikan `content: ['./src/**/*.{ts,tsx}']`
    - Extend colors: `'bni-teal': '#005E6A'` dan `'bni-orange': '#F15A24'`
    - Extend fontFamily: `sans: ['Inter', 'sans-serif']`
    - _Requirements: 1.4, 1.5, 1.6, 1.7_

  - [x] 1.3 Buat `frontend/postcss.config.js` untuk CRA PostCSS pipeline
    - Konfigurasi plugins: `tailwindcss: {}` dan `autoprefixer: {}`
    - Pastikan urutan: tailwindcss sebelum autoprefixer
    - _Requirements: 1.1_

  - [x] 1.4 Timpa `frontend/src/index.css` dengan Tailwind directives, Inter font, dan custom classes
    - Tambahkan `@import` Google Fonts Inter (weights 300–700) sebelum directives
    - Tambahkan tiga `@tailwind` directives: `base`, `components`, `utilities`
    - Definisikan `.bni-teal`, `.bg-bni-teal`, `.bni-orange`, `.bg-bni-orange`
    - Definisikan `.table-fixed-header th` dengan `position: sticky` dan `z-index: 10`
    - Definisikan `.truncate-2-lines` dengan `-webkit-line-clamp: 2`
    - _Requirements: 1.8, 1.9, 1.10, 1.11_

- [x] 2. Checkpoint — Verifikasi foundation
  - Pastikan `npm run build` berhasil tanpa TypeScript error. App lama masih render (file CSS belum dihapus).

- [x] 3. Refactor DashboardLayout — shell utama
  - [x] 3.1 Tulis ulang `frontend/src/components/DashboardLayout.tsx` dengan Tailwind dan Lucide icons
    - Ganti semua CSS class dari `DashboardLayout.css` dengan Tailwind utility classes
    - Import dan gunakan ikon Lucide: `LayoutGrid`, `GitCompareArrows`, `Clock`, `MapPin`, `Users`, `Search`, `LogOut`
    - Implementasikan sidebar dark (`bg-slate-900`, `w-64`) dengan logo header (`bg-slate-950`, `border-b border-slate-800`)
    - Implementasikan user session info (`bg-slate-800/50`, `text-xs`) dan logout button
    - Implementasikan nav item aktif: `bg-[#005E6A] text-white font-semibold`; nav item non-aktif: `text-slate-400 hover:bg-slate-800 hover:text-white text-xs`
    - Implementasikan Top Header Bar: `h-14 bg-white border-b border-gray-200 shadow-sm`
    - Content area: `flex-1 flex flex-col bg-slate-50 overflow-hidden`
    - Hapus import `DashboardLayout.css` dari file ini
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8, 2.9, 2.10, 2.11, 2.12_

  - [x] 3.2 Tulis property test untuk DashboardLayout — active nav exclusivity (Property 1)
    - **Property 1: Active nav item has exclusive active classes**
    - **Validates: Requirements 2.7, 2.8**
    - Gunakan `fc.constantFrom('/overview', '/comparison', '/time-analysis', '/regional', '/customer-criteria', '/similar-campaigns')` untuk route input
    - Assert: tepat satu nav item memiliki class `bg-[#005E6A]`; semua nav item lain tidak memiliki class itu
    - Gunakan `@testing-library/react` + `fast-check`

  - [x] 3.3 Tulis property test untuk DashboardLayout — no emoji (Property 2, DashboardLayout scope)
    - **Property 2: No emoji in any rendered component output (DashboardLayout)**
    - **Validates: Requirements 2.11**
    - Gunakan `fc.string()` untuk username input; `fc.constantFrom(...)` untuk active route
    - Assert: `document.body.textContent` tidak mengandung karakter emoji (Unicode ranges U+1F300–U+1FFFF, U+2600–U+27BF)

- [x] 4. Refactor FilterPanel — panel filter bersama
  - [x] 4.1 Tulis ulang `frontend/src/components/FilterPanel.tsx` dengan Tailwind dan Lucide icons
    - Ganti semua styling dari `FilterPanel.css` dengan Tailwind utility classes
    - Container: `bg-white border border-gray-200 rounded-xl shadow-sm`
    - Legend: `text-xs font-bold uppercase tracking-wider text-gray-600`
    - Ganti karakter `▼▲` dengan ikon Lucide `ChevronDown`/`ChevronUp`
    - Tombol Apply: `bg-[#005E6A] hover:bg-[#004852] text-white font-semibold rounded-lg text-xs`
    - Tombol Reset: `bg-gray-100 hover:bg-gray-200 text-gray-700 font-semibold rounded-lg text-xs`
    - Input text/date: `border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#005E6A] text-xs`
    - Hapus import `FilterPanel.css` dari file ini
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8_

- [x] 5. Refactor ExportService — tombol ekspor dengan toast
  - [x] 5.1 Tulis ulang `frontend/src/components/ExportService.tsx` dengan Tailwind dan Lucide icons
    - Ganti emoji `📥 ⏳ ✅ ⚠️ ❌ ✕` dengan ikon Lucide: `Download`, `Loader2`, `CheckCircle`, `AlertCircle`, `XCircle`, `X`
    - Export button idle: `bg-[#005E6A] hover:bg-[#004852] text-white font-semibold rounded-lg text-xs`
    - Export button loading: `animate-spin` pada `Loader2` icon
    - Toast container: `fixed bottom-5 right-5 max-w-sm z-50`
    - Toast success: `bg-emerald-600`; warning: `bg-amber-500`; error: `bg-rose-600`
    - Teks toast formal tanpa tanda seru: `"File siap diunduh"`, `"Ekspor gagal"`, `"Ekspor timeout (...). Coba kurangi rentang data atau coba lagi"`
    - Hapus import `ExportService.css` dari file ini
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 4.8, 4.9, 4.10_

  - [x] 5.2 Tulis property test untuk ExportService — toast type menentukan icon dan background (Property 3)
    - **Property 3: Toast type determines icon and background class**
    - **Validates: Requirements 4.3, 4.4, 4.5**
    - Gunakan `fc.constantFrom('success', 'warning', 'error')` untuk toast type
    - Assert: `success` → `CheckCircle` + `bg-emerald-600`; `warning` → `AlertCircle` + `bg-amber-500`; `error` → `XCircle` + `bg-rose-600`

  - [x] 5.3 Tulis property test untuk ExportService — pesan toast tidak mengandung tanda seru (Property 4)
    - **Property 4: Toast messages contain no exclamation marks**
    - **Validates: Requirements 4.10, 11.5**
    - Gunakan `fc.constantFrom('completed', 'timeout', 'error')` untuk export API response status, dengan `fc.string()` untuk error cause
    - Assert: semua string pesan toast yang dihasilkan tidak mengandung karakter `!`

- [x] 6. Checkpoint — Verifikasi shared components
  - Pastikan sidebar dark render, FilterPanel tampil benar, ExportService button visible. Jalankan `npm run build`.

- [x] 7. Refactor CampaignOverviewPage
  - [x] 7.1 Tulis ulang `frontend/src/pages/CampaignOverviewPage.tsx` dengan Tailwind dan Lucide icons
    - Buat sub-komponen `StatCard` dengan interface `{ label, value, icon }` dan class: `bg-white p-4 border border-gray-200 rounded-xl shadow-sm`
    - Label StatCard: `text-xs font-medium text-slate-400`; value: `text-2xl font-bold text-slate-700`
    - Gunakan ikon Lucide: `Users` (Total Leads), `TrendingUp` (Total Take Up), `BarChart2` (Take Up Rate)
    - Response time badge: `CheckCircle text-emerald-600` jika `< 5000ms`; `AlertCircle text-amber-600` jika `>= 5000ms`
    - Error state: ikon `AlertCircle text-rose-600`; empty state: ikon `Inbox text-gray-300`
    - Chart.js wrapper boleh menggunakan `style={{ height: '320px' }}` — satu-satunya pengecualian inline style
    - Hapus import `CampaignOverviewPage.css` dari file ini
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 5.8, 5.9, 5.10, 5.11_

  - [x] 7.2 Tulis property test untuk StatCard — required Tailwind classes (Property 5)
    - **Property 5: Stat Card elements have required Tailwind classes**
    - **Validates: Requirements 5.1, 5.2, 5.3, 7.2, 7.3**
    - Gunakan `fc.record({ label: fc.string(), value: fc.string() })` untuk StatCard props
    - Assert: container memiliki `bg-white border border-gray-200 rounded-xl shadow-sm`; label memiliki `text-xs font-medium text-slate-400`; value memiliki `text-2xl font-bold text-slate-700`

  - [x] 7.3 Tulis property test untuk response time badge (Property 6)
    - **Property 6: Response time badge icon is correct for all response times**
    - **Validates: Requirements 5.5, 5.6**
    - Gunakan `fc.float({ min: 0, max: 60000 })` untuk `responseMs`
    - Assert: `responseMs < 5000` → `CheckCircle` + `text-emerald-600`; `responseMs >= 5000` → `AlertCircle` + `text-amber-600`

- [x] 8. Refactor CampaignComparisonPage
  - [x] 8.1 Tulis ulang `frontend/src/pages/CampaignComparisonPage.tsx` dengan Tailwind
    - Hapus seluruh objek `styles` berisi `React.CSSProperties` dan tag `<style>` dengan `@keyframes spin`
    - Ganti semua `styles.*` dengan Tailwind classes sesuai tabel di design.md
    - Chip campaign: `bg-[#005E6A]/20 border border-[#005E6A] text-[#005E6A] rounded-full text-xs font-medium`
    - Spinner loading: `<Loader2 className="w-8 h-8 animate-spin text-[#005E6A]" />`
    - Tombol disabled: `bg-gray-300 cursor-not-allowed text-gray-500`
    - Header tabel: `bg-slate-900 text-white text-xs font-semibold`
    - Hapus import `CampaignComparisonPage.css` dari file ini
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7, 6.8, 6.9, 6.10, 6.11_

  - [x] 8.2 Tulis property test untuk campaign chip classes (Property 7)
    - **Property 7: Campaign chip has required Tailwind classes**
    - **Validates: Requirements 6.6**
    - Gunakan `fc.array(fc.string({ minLength: 1 }), { minLength: 1, maxLength: 5 })` untuk selected campaign IDs
    - Assert: setiap chip yang dirender memiliki classes `bg-[#005E6A]/20 border border-[#005E6A] text-[#005E6A] rounded-full text-xs font-medium`

- [x] 9. Refactor TimeToTakeUpPage
  - [x] 9.1 Tulis ulang `frontend/src/pages/TimeToTakeUpPage.tsx` dengan Tailwind dan Lucide icons
    - Gunakan sub-komponen `StatCard` yang sama dengan CampaignOverviewPage
    - StatCard rata-rata: ikon `Clock`; StatCard median: ikon `Timer`
    - Grid stat cards: `grid grid-cols-2 gap-4`
    - Error state: `AlertCircle text-rose-600`; empty state: `Inbox text-gray-300`
    - Chart.js wrapper: boleh `style={{ height: '320px' }}`
    - Hapus import `TimeToTakeUpPage.css` dari file ini
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7, 7.8_

- [x] 10. Refactor RegionalPerformancePage
  - [x] 10.1 Tulis ulang `frontend/src/pages/RegionalPerformancePage.tsx` dengan Tailwind
    - Hapus seluruh objek `styles` berisi `Record<string, React.CSSProperties>`
    - Implementasikan fungsi `getTakeUpBadgeClasses(rate: number): string` yang mengembalikan full class string:
      - `rate >= 10` → `bg-emerald-100 text-emerald-700 rounded px-1.5 py-0.5 text-xs font-semibold`
      - `rate >= 5` → `bg-amber-100 text-amber-700 rounded px-1.5 py-0.5 text-xs font-semibold`
      - `rate < 5` → `bg-rose-100 text-rose-700 rounded px-1.5 py-0.5 text-xs font-semibold`
    - Ganti emoji `🗺️ 📭 ⚠️` dengan ikon Lucide `MapPin`, `Inbox`, `AlertCircle`
    - Spinner: `<Loader2 className="w-8 h-8 animate-spin text-[#005E6A]" />`
    - Form label: `text-xs font-bold uppercase tracking-wider text-gray-600`
    - Hapus import `RegionalPerformancePage.css` dari file ini
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 8.7, 8.8, 8.9, 8.10, 8.11, 8.12, 8.13_

  - [x] 10.2 Tulis property test untuk take-up rate badge (Property 8)
    - **Property 8: Take-up rate badge class is determined by rate value**
    - **Validates: Requirements 8.5, 8.6, 8.7**
    - Gunakan `fc.float({ min: 0, max: 50 })` untuk `rate`
    - Assert: `rate >= 10` → `bg-emerald-100 text-emerald-700`; `5 <= rate < 10` → `bg-amber-100 text-amber-700`; `rate < 5` → `bg-rose-100 text-rose-700`
    - Test fungsi `getTakeUpBadgeClasses` secara unit di samping property test

- [x] 11. Refactor CustomerCriteriaPage
  - [x] 11.1 Tulis ulang `frontend/src/pages/CustomerCriteriaPage.tsx` dengan Tailwind dan Lucide icons
    - Ganti semua CSS class dari `CustomerCriteriaPage.css` dengan Tailwind utility classes
    - Card wrapper tabel: `bg-white border border-gray-200 rounded-xl shadow-sm overflow-hidden`
    - Section heading: `text-xs font-bold uppercase tracking-wider text-gray-400`
    - Tabel header row: `bg-slate-900`; `<th>`: `px-3 py-2.5 text-left text-white font-semibold whitespace-nowrap`
    - Gunakan ikon Lucide `Users` dan `Filter` untuk elemen visual
    - Error state: `AlertCircle text-rose-600`; empty state: `Inbox`
    - Hapus import `CustomerCriteriaPage.css` dari file ini
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7, 9.8_

- [x] 12. Refactor SimilarCampaignPage
  - [x] 12.1 Tulis ulang `frontend/src/pages/SimilarCampaignPage.tsx` dengan Tailwind dan Lucide icons
    - Ganti semua CSS class dari `SimilarCampaignPage.css` dengan Tailwind utility classes
    - Card campaign: `bg-white p-4 border border-gray-200 rounded-xl shadow-sm hover:shadow-md transition-shadow cursor-pointer`
    - Card terpilih: `bg-white p-4 border-2 border-[#005E6A] rounded-xl shadow-md cursor-pointer`
    - Similarity score badge: `bg-[#005E6A]/20 border border-[#005E6A] text-[#005E6A] text-xs font-semibold rounded px-1.5 py-0.5`
    - Ganti emoji di `ComparisonView` section headings dengan ikon Lucide: `BarChart2`, `GitCompareArrows`, `Star`, `Info`, `TrendingUp`
    - Empty/no-result state: ikon `SearchX`; idle state: ikon `Search`
    - Hapus import `SimilarCampaignPage.css` dari file ini
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 10.7, 10.8_

- [x] 13. Checkpoint — Verifikasi semua halaman
  - Jalankan `npm run build`. S   em ua 6 halaman harus render tanpa TypeScript error.

- [x] 14. Implementasikan shared state patterns dan konsistensi tipografi
  - [x] 14.1 Ekstrak komponen `EmptyState`, `LoadingState`, `ErrorState` sebagai shared components
    - `EmptyState`: `text-center py-12 text-gray-400`, ikon `Inbox w-8 h-8 text-gray-300`, teks `text-sm font-medium`, sub-teks `text-xs`
    - `LoadingState`: `text-center py-12`, ikon `Loader2 w-8 h-8 animate-spin text-[#005E6A]`, teks `text-sm font-medium`
    - `ErrorState`: `text-center py-12`, ikon `AlertCircle w-8 h-8 text-rose-400`, teks `text-sm font-medium text-rose-600`
    - Update semua 6 halaman untuk menggunakan komponen shared ini menggantikan implementasi lokal yang redundan
    - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5_

  - [x] 14.2 Tulis property test untuk empty state consistency (Property 9)
    - **Property 9: Empty state pattern is consistent across all pages**
    - **Validates: Requirements 11.1, 11.2**
    - Render setiap page component dalam kondisi empty-data state
    - Assert: output mengandung elemen dengan class `text-center py-12 text-gray-400`, ikon `Inbox` dengan `w-8 h-8 text-gray-300`, elemen teks dengan `text-sm font-medium`

  - [x] 14.3 Tulis property test untuk loading state (Property 10)
    - **Property 10: Loading state uses Loader2 with animate-spin across all pages**
    - **Validates: Requirements 11.3, 6.8, 8.8**
    - Render setiap page component dalam loading state
    - Assert: output mengandung `Loader2` icon dengan class `animate-spin` dan `text-[#005E6A]`; tidak ada div spinner CSS custom

  - [x] 14.4 Tulis property test untuk no emoji invariant (Property 2, all components)
    - **Property 2: No emoji in any rendered component output (all components)**
    - **Validates: Requirements 2.11, 3.8, 4.8, 5 (all pages), 11.2**
    - Gunakan `fc.string()` untuk username dan `fc.string()` untuk error message inputs
    - Render semua komponen (DashboardLayout, FilterPanel, ExportService, semua 6 halaman)
    - Assert: `document.body.textContent` tidak mengandung karakter emoji (cek Unicode ranges U+1F300–U+1FFFF, U+2600–U+27BF)

- [x] 15. Hapus file CSS lama
  - [x] 15.1 Hapus 9 file CSS komponen dan halaman yang sudah digantikan Tailwind
    - Hapus: `frontend/src/components/DashboardLayout.css`
    - Hapus: `frontend/src/components/FilterPanel.css`
    - Hapus: `frontend/src/components/ExportService.css`
    - Hapus: `frontend/src/pages/CampaignOverviewPage.css`
    - Hapus: `frontend/src/pages/CampaignComparisonPage.css`
    - Hapus: `frontend/src/pages/TimeToTakeUpPage.css`
    - Hapus: `frontend/src/pages/RegionalPerformancePage.css`
    - Hapus: `frontend/src/pages/CustomerCriteriaPage.css`
    - Hapus: `frontend/src/pages/SimilarCampaignPage.css`
    - Verifikasi tidak ada import CSS lama yang tersisa di file `.tsx` manapun
    - _Requirements: 13.1, 13.2, 13.3, 13.4, 13.5_

- [x] 16. Final checkpoint — Verifikasi lengkap
  - Jalankan `npm run build` — tidak ada TypeScript error, tidak ada CSS import warning
  - Jalankan `npm run lint` (jika tersedia) — tidak ada ESLint error
  - Konfirmasi tidak ada file `.css` yang masih diimpor di dalam `src/`
  - Konfirmasi tidak ada karakter emoji di file `.tsx` manapun
  - Konfirmasi tidak ada `style={}` selain pada wrapper Chart.js

---

## Notes

- Task bertanda `*` adalah opsional dan dapat dilewati untuk MVP lebih cepat
- Setiap task mereferensikan requirement spesifik untuk keterlacakan
- Checkpoint memastikan validasi inkremental
- Property tests menggunakan `fast-check` + `@testing-library/react`
- Unit tests menggunakan `@testing-library/react` untuk example-based checks
- Satu-satunya pengecualian inline style yang diizinkan: `style={{ height: '...' }}` pada wrapper div Chart.js
- Semua class Tailwind harus berupa full string literals — jangan konstruksi class string secara dinamis kecuali menggunakan ternary dengan full strings di kedua cabang

---

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1"] },
    { "id": 1, "tasks": ["1.2", "1.3"] },
    { "id": 2, "tasks": ["1.4"] },
    { "id": 3, "tasks": ["3.1"] },
    { "id": 4, "tasks": ["4.1", "5.1"] },
    { "id": 5, "tasks": ["3.2", "3.3", "5.2", "5.3"] },
    { "id": 6, "tasks": ["7.1", "8.1", "9.1", "10.1", "11.1", "12.1"] },
    { "id": 7, "tasks": ["7.2", "7.3", "8.2", "10.2"] },
    { "id": 8, "tasks": ["14.1"] },
    { "id": 9, "tasks": ["14.2", "14.3", "14.4"] },
    { "id": 10, "tasks": ["15.1"] }
  ]
}
```
