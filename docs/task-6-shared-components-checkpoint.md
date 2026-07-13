# Task 6 — Checkpoint: Verifikasi Shared Components

## Ringkasan Singkat

Task ini merupakan checkpoint verifikasi untuk memastikan bahwa 3 shared components utama dashboard (`DashboardLayout.tsx`, `FilterPanel.tsx`, dan `ExportService.tsx`) telah diimplementasikan secara benar sesuai design system BNI. Tidak ada perubahan kode dilakukan — seluruh isi task adalah pemeriksaan dan dokumentasi hasil verifikasi.

---

## Penjelasan Awam (Non-Technical)

Bayangkan sebuah tim konstruksi sedang membangun gedung. Setelah menyelesaikan fondasi dan tiga dinding utama, mereka melakukan **inspeksi kualitas** sebelum melanjutkan ke lantai berikutnya.

Checkpoint ini adalah inspeksi kualitas untuk tiga "dinding utama" tampilan aplikasi:
- **DashboardLayout** — struktur kerangka aplikasi (sidebar + area konten)
- **FilterPanel** — panel untuk memilih filter data
- **ExportService** — tombol untuk mengunduh data

Inspeksi memastikan bahwa semua dinding sudah dibangun dengan material yang benar (Tailwind CSS), menggunakan ikon yang sesuai standar BNI (Lucide React), dan tidak ada "material selundupan" (CSS lama, emoji, atau style inline).

---

## Penjelasan Teknis

### Files yang Diverifikasi

| File | Path |
|------|------|
| `DashboardLayout.tsx` | `frontend/src/components/DashboardLayout.tsx` |
| `FilterPanel.tsx` | `frontend/src/components/FilterPanel.tsx` |
| `ExportService.tsx` | `frontend/src/components/ExportService.tsx` |

### Kriteria Verifikasi

Setiap file diperiksa terhadap 5 kriteria:

1. **Tidak ada CSS import** — tidak boleh ada `import './ComponentName.css'` atau sejenisnya
2. **Tidak ada emoji** — tidak boleh ada karakter emoji dalam JSX atau string yang dirender
3. **Tidak ada inline `style={}`** — semua styling harus menggunakan Tailwind class (kecuali Chart.js yang memiliki pengecualian, tapi ketiga komponen ini tidak menggunakan Chart.js)
4. **Lucide icons yang benar** — ikon yang digunakan harus sesuai design system
5. **Tailwind classes yang benar** — warna BNI, sidebar dark, border/radius sesuai standar

---

## Hasil Verifikasi

### ✅ DashboardLayout.tsx — LULUS

| Kriteria | Status | Detail |
|----------|--------|--------|
| Tidak ada CSS import | ✅ | Tidak ada `import './DashboardLayout.css'` |
| Tidak ada emoji | ✅ | Tidak ada karakter emoji di seluruh file |
| Tidak ada inline `style={}` | ✅ | Semua styling via Tailwind class |
| Lucide icons benar | ✅ | `LayoutGrid`, `GitCompareArrows`, `Clock`, `MapPin`, `Users`, `Search`, `LogOut` |
| Tailwind classes benar | ✅ | Sidebar `bg-slate-900`, logo header `bg-slate-950`, nav aktif `bg-[#005E6A]`, konten `bg-slate-50` |

**Catatan teknis**: Komponen menggunakan `NavLink` dari `react-router-dom` dengan render prop `({ isActive })` untuk toggle class aktif/inaktif. Struktur sidebar memenuhi semua ketentuan design system: dark background, BNI Teal untuk item aktif, `text-slate-400` untuk item inaktif.

---

### ✅ FilterPanel.tsx — LULUS

| Kriteria | Status | Detail |
|----------|--------|--------|
| Tidak ada CSS import | ✅ | Tidak ada import CSS apapun |
| Tidak ada emoji | ✅ | Tidak ada karakter emoji |
| Tidak ada inline `style={}` | ✅ | Semua styling via Tailwind class |
| Lucide icons benar | ✅ | `ChevronDown` (collapsed) dan `ChevronUp` (expanded) |
| Tailwind classes benar | ✅ | Panel `bg-white border border-gray-200 rounded-xl shadow-sm`, focus ring `focus:ring-[#005E6A]`, button primary `bg-[#005E6A] hover:bg-[#004852]` |

**Catatan teknis**: Komponen memiliki generic `CheckboxGroup<T>` yang mendukung `string | number` untuk mendukung wilayah (number 1–17) dan flag_program/media_blasting (string). State collapse/expand diimplementasikan dengan `useState<boolean>` murni tanpa animasi CSS terpisah.

---

### ✅ ExportService.tsx — LULUS

| Kriteria | Status | Detail |
|----------|--------|--------|
| Tidak ada CSS import | ✅ | Tidak ada import CSS apapun |
| Tidak ada emoji | ✅ | Tidak ada karakter emoji (termasuk emoji checkmark atau warning) |
| Tidak ada inline `style={}` | ✅ | Semua styling via Tailwind class |
| Lucide icons benar | ✅ | `Download`, `Loader2`, `CheckCircle`, `AlertCircle`, `XCircle`, `X` |
| Toast formal tanpa tanda seru | ✅ | Semua pesan toast formal: `'File siap diunduh'`, `'Ekspor timeout (>30 detik)...'`, `'Ekspor gagal: ...'` — tidak ada `!` |

**Catatan teknis**: Sub-komponen `Toast` merupakan internal component di file yang sama. Toast menggunakan `role="alert"` dan `aria-live="assertive"` untuk aksesibilitas. Auto-dismiss hanya berlaku untuk toast `success` (5 detik). Toast `warning` dan `error` memiliki tombol "Coba Lagi" (`onRetry` callback).

---

## Ringkasan Verifikasi

| Komponen | CSS Import | Emoji | Inline Style | Lucide Icons | Tailwind Classes | STATUS |
|----------|-----------|-------|--------------|--------------|------------------|--------|
| DashboardLayout.tsx | ✅ Bersih | ✅ Bersih | ✅ Bersih | ✅ Benar | ✅ Benar | **LULUS** |
| FilterPanel.tsx | ✅ Bersih | ✅ Bersih | ✅ Bersih | ✅ Benar | ✅ Benar | **LULUS** |
| ExportService.tsx | ✅ Bersih | ✅ Bersih | ✅ Bersih | ✅ Benar | ✅ Benar | **LULUS** |

**Hasil keseluruhan: 3/3 komponen LULUS. Tidak ada perubahan kode diperlukan.**

---

## Simulasi / Skenario

### Skenario 1: Pengguna Membuka Dashboard

1. `DashboardLayout` dirender — sidebar `bg-slate-900` muncul di kiri, konten `bg-slate-50` di kanan
2. NavLink `/overview` aktif → item mendapat class `bg-[#005E6A] text-white`
3. Item lain tetap `text-slate-400 hover:bg-slate-800`
4. Ikon `LayoutGrid` tampil 16×16px di sebelah label "Campaign Overview"

### Skenario 2: Pengguna Collapse/Expand Filter Panel

1. FilterPanel dirender dengan `isCollapsed = false` → ChevronUp icon + "Collapse" label
2. User klik tombol → `setIsCollapsed(true)` → ChevronDown icon + "Expand" label
3. Body filter (`id="filter-panel-body"`) hilang dari DOM (conditional render `{!isCollapsed && ...}`)
4. Tidak ada animasi slide — toggling langsung, sesuai enterprise aesthetic

### Skenario 3: Export Gagal Timeout

1. User klik "Export" → `exporting = true` → icon berubah ke `Loader2` spinning
2. API melempar `ApiTimeoutError` setelah 30+ detik
3. Toast `warning` muncul: `"Ekspor timeout (>30 detik). Coba kurangi rentang data atau coba lagi"`
4. Toast berwarna `bg-amber-500`, ikon `AlertCircle`, ada tombol "Coba Lagi" — **tidak ada emoji, tidak ada tanda seru**
5. Toast tidak auto-dismiss (hanya success yang auto-dismiss)

---

## Keterkaitan dengan Komponen Lain

- **DashboardLayout** digunakan oleh: semua 6 halaman dashboard (`CampaignOverviewPage`, `CampaignComparisonPage`, dll.)
- **FilterPanel** digunakan oleh: semua halaman yang memerlukan filter (Overview, Comparison, Regional, dll.)
- **ExportService** digunakan oleh: semua halaman dashboard sebagai tombol ekspor opsional
- **Bergantung pada**: `api.ts` (service layer Axios), `types/api.ts` (types), `types/filters.ts` (FilterState)

---

## Requirements yang Dipenuhi

| Komponen | Requirements |
|----------|-------------|
| DashboardLayout | 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8, 2.9, 2.10, 2.11, 2.12 |
| FilterPanel | 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8 |
| ExportService | 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 4.8, 4.9, 4.10 |

---

## Catatan Penting

- **Tidak ada perubahan kode** dilakukan pada checkpoint ini — semua 3 file sudah benar dari task sebelumnya (3.1, 4.1, 5.1)
- **Toast ExportService**: pesan menggunakan titik `.` sebagai terminator kalimat, bukan tanda seru `!` — ini adalah keputusan desain intentional sesuai design system enterprise BNI
- **FilterPanel `jenisCleads`**: field menggunakan nama `jenisCleads` (camelCase dari `jenis_leads`) — dipisahkan dengan koma di UI, diparse menjadi array sebelum dikirim ke API
- **DashboardLayout tidak memiliki icon di top header bar** — `<h1>` hanya berisi teks tanpa icon Lucide, berbeda dengan referensi `main_v4a.html`. Ini adalah simplifikasi yang acceptable karena icon bersifat opsional di design system
