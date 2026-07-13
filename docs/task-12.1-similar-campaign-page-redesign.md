# Task 12.1 — Rewrite SimilarCampaignPage dengan Tailwind + Lucide Icons

## Ringkasan Singkat

Task ini melakukan rewrite penuh halaman `SimilarCampaignPage.tsx` — halaman "Campaign Serupa" — untuk sepenuhnya menggunakan Tailwind CSS utility classes dan Lucide React icons, menggantikan semua class CSS lama dari `SimilarCampaignPage.css`, semua emoji, dan semua inline styles, agar tampilan konsisten dengan BNI Design System.

## Penjelasan Awam (Non-Technical)

Bayangkan sebuah halaman di aplikasi bank yang menampilkan daftar kampanye yang mirip satu sama lain. Sebelumnya, tampilan halaman ini menggunakan warna dan gaya lama yang tidak sesuai standar visual BNI, dan menggunakan emoji seperti 📊 atau ⚠️ sebagai ikon. Sekarang, halaman ini menggunakan warna resmi BNI (hijau teal #005E6A), ikon vektor profesional dari library Lucide React, dan tampilan yang bersih dan konsisten dengan halaman-halaman lain di aplikasi.

Manfaat bagi pengguna bisnis: tampilan yang lebih profesional, konsisten, dan mudah dibaca sesuai standar enterprise bank.

## Penjelasan Teknis

**File yang dimodifikasi:**
- `frontend/src/pages/SimilarCampaignPage.tsx` — full rewrite

**File yang tidak perlu dihapus (sudah tidak ada):**
- `frontend/src/pages/SimilarCampaignPage.css` — sudah tidak diimpor dan tidak direferensikan

**Library yang digunakan:**
- `lucide-react` — icons (Search, SearchX, AlertCircle, Loader2, BarChart2, GitCompareArrows, Star, Info, TrendingUp)
- Tailwind CSS 3.4.1 — semua styling

**Pola arsitektur yang diterapkan:**
- Sub-komponen `CampaignCard` dengan Tailwind conditional class (selected vs unselected) menggunakan ternary expression dengan full string literals di kedua branch
- Sub-komponen `ComparisonView` dengan section headings menggunakan Lucide icons inline
- Shared patterns: loading state (Loader2 + animate-spin), error state (AlertCircle), empty/no-result state (SearchX), idle state (Search)

**Keputusan desain penting:**
- Card terpilih: `border-2 border-[#005E6A]` vs card biasa: `border border-gray-200` — keduanya adalah full string literals, memenuhi aturan Tailwind purging
- Similarity score badge: `bg-[#005E6A]/20 border border-[#005E6A]` — warna teal dengan opacity 20% untuk background
- Dimension matching badge: `bg-[#005E6A]/10 border border-[#005E6A]/40` — lebih subtle dari similarity badge
- Tidak ada `style={}` di manapun (tidak ada Chart.js di halaman ini)

## Struktur Kode

```tsx
// CampaignCard — kartu hasil pencarian campaign serupa
const CampaignCard: React.FC<CampaignCardProps>
  // Props: campaign, isSelected, onClick
  // Renders: card dengan conditional border, metrics grid, badge row

// ComparisonView — panel detail side-by-side setelah card dipilih
const ComparisonView: React.FC<ComparisonViewProps>
  // Props: campaign
  // Renders: 4 sections dengan Lucide section headings

// SimilarCampaignPage — main component
const SimilarCampaignPage: React.FC
  // States: referenceId, dimensions, data, selectedCampaign, loading, error
  // Renders: search form → loading/error/no-result/results/idle states
```

## Simulasi / Skenario

**Skenario 1 — Pencarian berhasil:**
- User memasukkan campaign ID `CAMP-001`, memilih dimensi `flag_program` + `media_blasting`
- Klik tombol "Cari Campaign Serupa" (teal button dengan ikon Search)
- Loading state tampil: `Loader2` berputar dengan teks "Memuat data"
- Hasil: 5 kartu campaign muncul dengan badge skor kesamaan teal
- User klik salah satu kartu → panel ComparisonView muncul di kanan

**Skenario 2 — Tidak ada hasil:**
- API mengembalikan array kosong
- Tampil: ikon `SearchX` abu-abu + teks "Tidak Ditemukan" + hint untuk perluas dimensi

**Skenario 3 — Idle (belum cari):**
- Halaman baru dibuka, belum ada pencarian
- Tampil: ikon `Search` abu-abu + teks "Cari Campaign Serupa" + instruksi

**Skenario 4 — Error API:**
- Request gagal dengan network error
- Tampil: ikon `AlertCircle` rose + teks "Terjadi kesalahan" + pesan error detail

## Keterkaitan dengan Komponen Lain

- **Bergantung pada**: `DashboardLayout` (shell wrapper), `api.getSimilarCampaigns()` (service layer), `useAuth` hook, type `SimilarCampaignResponse` dan `SimilarCampaignResult` dari `types/api`
- **Digunakan oleh**: React Router via route `/similar-campaigns`
- **Pengaruh ke**: tidak ada komponen lain yang bergantung pada file ini

## Requirements yang Dipenuhi

- **10.1** — Styling menggunakan Tailwind CSS, tidak mengimpor `SimilarCampaignPage.css`
- **10.2** — Card campaign menggunakan class `bg-white p-4 border border-gray-200 rounded-xl shadow-sm hover:shadow-md transition`
- **10.3** — Similarity score badge: `bg-[#005E6A]/20 border border-[#005E6A] text-[#005E6A] text-xs font-semibold rounded px-1.5 py-0.5`
- **10.4** — Ikon Lucide React: Search, Star, TrendingUp, BarChart2, GitCompareArrows, Info, SearchX digunakan — tidak ada emoji
- **10.5** — Error state menggunakan ikon `AlertCircle` dengan class `text-rose-600`
- **10.6** — No-result state menggunakan ikon `SearchX` dari Lucide React
- **10.7** — Tidak ada inline styles (`style={}`) di manapun dalam komponen
- **10.8** — Tidak ada emoji di manapun dalam komponen

## Catatan Penting

- File `SimilarCampaignPage.css` tidak perlu dihapus secara manual karena tidak pernah diimpor di versi rewrite ini — jika masih ada di filesystem, tidak akan mempengaruhi build
- Class `truncate-2-lines` yang digunakan pada nama campaign didefinisikan di `index.css` sebagai custom class (webkit-box pattern)
- Warna `#005E6A` digunakan langsung sebagai arbitrary value Tailwind — tidak memerlukan class `bni-teal` dari config karena arbitrary values selalu tersedia
- Build production berhasil dengan `Compiled successfully` — ukuran bundle JS: 167.94 kB (gzip), CSS: 4.21 kB (gzip)
