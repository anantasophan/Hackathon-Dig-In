# Task UI 8.1 — CampaignComparisonPage: Migrasi ke Tailwind CSS

## Ringkasan Singkat

Task ini melakukan rewrite menyeluruh `frontend/src/pages/CampaignComparisonPage.tsx` untuk menghapus seluruh objek `styles` bertipe `React.CSSProperties`, tag `<style>` dengan `@keyframes spin`, dan import `CampaignComparisonPage.css`. Semua styling diganti dengan Tailwind CSS utility classes sesuai BNI Design System. Hasilnya adalah halaman Perbandingan Campaign yang sepenuhnya bebas dari CSS inline, menggunakan shared components (`EmptyState`, `LoadingState`, `ErrorState`), dan tampilan konsisten dengan seluruh halaman lain dalam aplikasi.

---

## Penjelasan Awam (Non-Technical)

**Apa fungsinya dalam bahasa sehari-hari?**

Bayangkan sebuah formulir di kantor yang awalnya ditulis tangan dengan berbagai warna tinta dan sticky notes tempel sana-sini. Task ini adalah proses merapikannya: semua tulisan tangan diketik ulang menggunakan template standar kantor yang resmi, sehingga tampilannya seragam dengan formulir-formulir lain.

**Analoginya dengan kehidupan nyata?**

Seperti mengganti seragam yang dijahit sendiri-sendiri per orang menjadi seragam kantor yang sudah ada standar potong dan warnanya — semua terlihat rapi dan seragam, tapi fungsinya tetap sama.

**Manfaat bagi pengguna bisnis?**

- Halaman Perbandingan Campaign kini tampil konsisten dengan halaman lain (font, warna, ukuran tombol)
- Spinner loading tidak lagi bergantung pada file CSS eksternal — muncul dengan animasi yang sama di semua browser
- Chip campaign yang dipilih berwarna BNI Teal, langsung dikenali sebagai elemen aktif

---

## Penjelasan Teknis

### File yang Dimodifikasi

| File | Perubahan |
|------|-----------|
| `frontend/src/pages/CampaignComparisonPage.tsx` | Rewrite: hapus `styles` object, `@keyframes`, dan CSS import. Ganti semua `style={}` dengan Tailwind classes |

### File yang Tidak Dimodifikasi (sudah tidak diimpor)
- `frontend/src/pages/CampaignComparisonPage.css` — masih ada di filesystem tapi tidak diimpor dari manapun (memenuhi Requirement 13.4–13.5)

### Library / Framework

- **Tailwind CSS 3.4.1** — seluruh styling
- **Lucide React 0.378.0** — ikon `Loader2` untuk spinner loading
- **StateComponents** (`EmptyState`, `LoadingState`, `ErrorState`) dari `frontend/src/components/StateComponents.tsx` — sudah diimplementasikan di task 14.1

### Pola Arsitektur

**Before (pola lama):**
```tsx
// Objek styles dengan React.CSSProperties
const styles: Record<string, React.CSSProperties> = {
  container: { padding: '24px', maxWidth: '1200px' },
  chip: { backgroundColor: 'rgba(0,94,106,0.2)', border: '1px solid #005E6A', ... },
  // 30+ properties...
};

// Penggunaan
<div style={styles.container}>
  <span style={styles.chip}>{id}</span>
</div>

// Tag <style> injected untuk @keyframes spin
<style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
```

**After (pola baru — Tailwind):**
```tsx
// Tidak ada objek styles
// Tailwind classes langsung di JSX
<div className="p-6 max-w-[1200px]">
  <span className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-[#005E6A]/20 border border-[#005E6A] text-[#005E6A] rounded-full text-xs font-medium">
    {id}
  </span>
</div>

// Spinner dari Lucide + Tailwind animate-spin
<LoadingState />
// atau inline: <Loader2 className="w-8 h-8 animate-spin text-[#005E6A]" />
```

### Keputusan Desain Penting

1. **Chart.js height exception** — `<div className="relative" style={{ height: '420px' }}>` dipertahankan sebagai satu-satunya `style={}` karena Chart.js membutuhkan pixel height eksplisit untuk rendering yang benar. Ini adalah pengecualian yang diizinkan oleh design.md dan Requirement 6.10.

2. **StateComponents digunakan** — `EmptyState`, `LoadingState`, `ErrorState` diimpor dari `../components/StateComponents` alih-alih diimplementasikan inline, mengikuti pola DRY yang sudah ada sejak task 14.1.

3. **Chip campaign** menggunakan class `inline-flex items-center gap-1.5 px-2.5 py-1 bg-[#005E6A]/20 border border-[#005E6A] text-[#005E6A] rounded-full text-xs font-medium` — ini menggunakan opacity modifier `/20` Tailwind untuk warna background semi-transparan.

4. **Tombol disabled** menggunakan conditional className: tombol aktif mendapat `bg-[#005E6A]`, tombol disabled mendapat `bg-gray-300 cursor-not-allowed text-gray-500` — tidak ada inline style, semua lewat Tailwind.

---

## Struktur Kode (Ringkasan Fungsi Utama)

```tsx
// Mapping styles lama → Tailwind baru
styles.container        → className="p-6 max-w-[1200px]"
styles.card             → className="bg-white p-4 border border-gray-200 rounded-xl shadow-sm mb-4"
styles.sectionTitle     → className="text-xs font-bold uppercase tracking-wider text-gray-400 mb-3"
styles.input            → className="w-56 px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#005E6A] bg-white text-xs"
styles.addButton        → className="px-4 py-2 bg-[#005E6A] hover:bg-[#004852] text-white font-semibold rounded-lg text-xs transition-colors"
styles.addButtonDisabled→ className="px-4 py-2 bg-gray-300 text-gray-500 font-semibold rounded-lg text-xs cursor-not-allowed"
styles.chip             → className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-[#005E6A]/20 border border-[#005E6A] text-[#005E6A] rounded-full text-xs font-medium"
styles.chipRemove       → className="hover:text-rose-600 transition-colors"
styles.compareButton    → className="px-6 py-2.5 bg-[#005E6A] hover:bg-[#004852] text-white font-semibold rounded-lg text-xs transition-colors"
styles.compareButtonDisabled → className="px-6 py-2.5 bg-gray-300 text-gray-500 font-semibold rounded-lg text-xs cursor-not-allowed"
styles.thCell           → className="px-3 py-2.5 text-left bg-slate-900 text-white text-xs font-semibold whitespace-nowrap"
styles.tdEven           → className="px-3 py-2.5 bg-white border-b border-gray-100 text-xs"
styles.tdOdd            → className="px-3 py-2.5 bg-slate-50 border-b border-gray-100 text-xs"
styles.spinnerContainer → LoadingState component (flex justify-center items-center py-12)
styles.spinner          → <Loader2 className="w-8 h-8 animate-spin text-[#005E6A]" />
styles.emptyState       → EmptyState component
styles.errorState       → ErrorState component
styles.select           → className="px-3 py-2 border border-gray-300 rounded-lg text-xs bg-white focus:ring-2 focus:ring-[#005E6A] focus:outline-none"
styles.chartWrapper     → className="relative" + style={{ height: '420px' }} (Chart.js exception)
styles.chipRow          → className="flex flex-wrap gap-2 mt-3"
styles.inputRow         → className="flex items-center gap-2 flex-wrap"
styles.label            → className="text-xs font-bold uppercase tracking-wider text-gray-600"
```

---

## Simulasi / Skenario

### Skenario 1 — Happy Path: Membandingkan 3 Campaign

**Input:** User memasukkan campaign ID "C001", "C002", "C003" satu per satu, lalu menekan Bandingkan.

**Proses:**
1. Setiap input ditampilkan sebagai chip: warna BNI Teal semi-transparan, rounded-full
2. Tombol Bandingkan aktif (bg-[#005E6A]) setelah 2 campaign ditambahkan
3. Saat loading: `LoadingState` muncul dengan `Loader2 animate-spin text-[#005E6A]`
4. Setelah data masuk: tabel dengan header `bg-slate-900 text-white`, baris genap `bg-white`, baris ganjil `bg-slate-50`

**Output:** Tabel perbandingan 5 metrik + bar chart Chart.js dengan tinggi 420px.

### Skenario 2 — Tombol Disabled

**Input:** User belum memasukkan campaign apapun.

**Proses:** Tombol Bandingkan dirender dengan class `bg-gray-300 cursor-not-allowed text-gray-500`.

**Output:** Tombol terlihat abu-abu dan tidak bisa diklik. Pesan "Pilih minimal 2 campaign" muncul di sebelahnya (`text-xs text-gray-400`).

### Skenario 3 — Error State

**Input:** API mengembalikan error (network timeout, 500, dll).

**Proses:** `ErrorState` component dirender dengan `AlertCircle text-rose-400` dan pesan error dari server.

**Output:** Tampilan pesan error konsisten dengan halaman lain — tanpa emoji, teks formal.

---

## Keterkaitan dengan Komponen Lain

- **Bergantung pada:**
  - `StateComponents.tsx` (`EmptyState`, `LoadingState`, `ErrorState`) — task 14.1
  - `DashboardLayout.tsx` — shell layout sidebar + top bar
  - `api.ts` → `api.compareCampaigns()` — service layer API
  - `chart.js` + `react-chartjs-2` — visualisasi bar chart

- **Digunakan oleh:**
  - `App.tsx` via route `/comparison` → `<CampaignComparisonPage />`

- **Pengaruh ke:**
  - Tidak ada komponen lain yang mengimpor `CampaignComparisonPage` secara langsung
  - Jika `StateComponents` berubah, tampilan loading/error/empty di halaman ini ikut berubah

---

## Requirements yang Dipenuhi

| Requirement | Deskripsi |
|-------------|-----------|
| 6.1 | Seluruh layout menggunakan Tailwind CSS — objek `styles` dihapus |
| 6.2 | Card input campaign: `bg-white p-4 border border-gray-200 rounded-xl shadow-sm` |
| 6.3 | Tombol Tambah: `bg-[#005E6A] hover:bg-[#004852] text-white font-semibold rounded-lg text-xs` |
| 6.4 | Tombol Bandingkan: `bg-[#005E6A] hover:bg-[#004852] text-white font-semibold rounded-lg` |
| 6.5 | Tombol disabled: `bg-gray-300 cursor-not-allowed text-gray-500` |
| 6.6 | Chip campaign: `bg-[#005E6A]/20 border border-[#005E6A] text-[#005E6A] rounded-full text-xs font-medium` |
| 6.7 | Header tabel: `bg-slate-900 text-white text-xs font-semibold` |
| 6.8 | Loading: `Loader2 animate-spin text-[#005E6A]` via `LoadingState` — bukan `@keyframes spin` |
| 6.9 | Error: `AlertCircle text-rose-400` via `ErrorState` |
| 6.10 | Tidak ada `style={}` kecuali Chart.js height exception |
| 6.11 | Tidak ada emoji dimanapun dalam komponen |
| 13.4 | Import `CampaignComparisonPage.css` dihapus dari komponen |

---

## Catatan Penting

1. **File CSS lama masih ada**: `frontend/src/pages/CampaignComparisonPage.css` masih ada di filesystem tapi tidak diimpor dari manapun. Requirement 13.5 hanya melarang referensi, bukan keberadaan file — bisa dihapus secara fisik di task cleanup (task 14.x).

2. **Chart.js inline style**: Satu-satunya `style={}` yang tersisa adalah `style={{ height: '420px' }}` pada wrapper chart. Ini adalah pengecualian yang didokumentasikan dalam design.md dan diizinkan oleh Requirement 6.10.

3. **Conditional className pattern**: Tombol yang perlu state enabled/disabled menggunakan ternary operator pada `className` (bukan conditional `style={}`) — pola ini konsisten dengan button di halaman lain.

4. **`@keyframes spin` dihapus**: Sebelumnya terdapat tag `<style>` yang meng-inject keyframe spinner inline. Ini sudah dihapus sepenuhnya — Tailwind's `animate-spin` menggantikan fungsi tersebut.
