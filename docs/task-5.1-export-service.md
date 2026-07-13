# Task 5.1 — ExportService: Rewrite dengan Tailwind CSS dan Lucide Icons

## Ringkasan Singkat

Task ini menulis ulang komponen `frontend/src/components/ExportService.tsx` sepenuhnya menggunakan Tailwind CSS utility classes dan Lucide React icons, menggantikan emoji karakter dan file `ExportService.css` lama. Komponen ini digunakan di halaman-halaman dashboard untuk memungkinkan pengguna mengekspor data ke format CSV, Excel, atau PDF, disertai notifikasi toast yang profesional.

---

## Penjelasan Awam (Non-Technical)

**Fungsinya dalam bahasa sehari-hari:**
Komponen `ExportService` adalah tombol "Unduh Data" yang muncul di pojok kanan atas setiap halaman dashboard. Pengguna bisa memilih format file (CSV, Excel, atau PDF), lalu klik tombol untuk mengunduh data yang sedang ditampilkan.

**Analoginya dengan kehidupan nyata:**
Bayangkan mesin kasir di supermarket — setelah transaksi selesai, kasir bisa mencetak struk ke kertas biasa (CSV), format Excel (Excel), atau format dokumen resmi (PDF). ExportService adalah tombol "Cetak" tersebut.

**Perubahan yang terlihat oleh pengguna:**
- Sebelumnya: tombol bertuliskan "📥 Export" dengan emoji; notifikasi muncul dengan teks "✅ File siap diunduh!"
- Sesudahnya: tombol menggunakan ikon download yang bersih; notifikasi menggunakan ikon lingkaran centang/peringatan/error yang profesional dengan teks formal tanpa tanda seru

**Manfaat bagi pengguna bisnis:**
Tampilan yang lebih bersih dan profesional sesuai standar visual bank BNI, tanpa emoji yang terasa informal.

---

## Penjelasan Teknis

### File yang Dimodifikasi

- **Diubah**: `frontend/src/components/ExportService.tsx` — rewrite penuh

### Perubahan Utama

#### 1. Import CSS dihapus, Lucide icons ditambahkan
```tsx
// DIHAPUS:
import './ExportService.css';

// DITAMBAHKAN:
import { Download, Loader2, CheckCircle, AlertCircle, XCircle, X } from 'lucide-react';
```

Enam ikon menggantikan enam emoji:
| Emoji Lama | Lucide Icon Baru | Konteks |
|------------|-----------------|---------|
| `📥` | `Download` | Tombol export idle |
| `⏳` | `Loader2` + `animate-spin` | Tombol export saat loading |
| `✅` | `CheckCircle` | Toast sukses |
| `⚠️` | `AlertCircle` | Toast timeout/warning |
| `❌` | `XCircle` | Toast error |
| `✕` | `X` | Tombol dismiss toast |

#### 2. Sub-komponen Toast diperbarui
Toast sekarang menggunakan Tailwind untuk warna background dan Lucide untuk ikon status:
- `bg-emerald-600` — sukses
- `bg-amber-500` — warning (timeout)
- `bg-rose-600` — error

Ikon dipilih secara dinamis berdasarkan `type` prop menggunakan ternary expression.

#### 3. Tombol Export
State idle: `bg-[#005E6A] hover:bg-[#004852] text-white font-semibold rounded-lg text-xs`
State loading: `bg-[#005E6A]/70 cursor-not-allowed` dengan `Loader2 animate-spin`
State disabled (prop): `bg-gray-300 text-gray-500 cursor-not-allowed`

#### 4. Toast container diposisikan fixed
```tsx
<div className="fixed bottom-5 right-5 max-w-sm space-y-2 z-50">
```
Toast muncul di pojok kanan bawah layar, tidak menggeser layout komponen lain.

#### 5. Pesan toast diformalkan (tanpa tanda seru)
| Pesan Lama | Pesan Baru |
|------------|------------|
| `'✅ File siap diunduh!'` | `'File siap diunduh'` |
| `'⚠️ Ekspor timeout (>30 detik). Coba kurangi rentang data atau coba lagi.'` | `'Ekspor timeout (>30 detik). Coba kurangi rentang data atau coba lagi'` |
| `` `❌ Ekspor gagal: ${cause}. Coba lagi.` `` | `` `Ekspor gagal: ${cause}. Coba lagi` `` |

### Yang Tidak Berubah

Seluruh logika bisnis dipertahankan persis sama:
- `useEffect` untuk auto-dismiss toast sukses setelah 5 detik
- `handleExport` — memanggil `api.exportData()` dan memproses response
- `handleRetry` — memanggil ulang `handleExport`
- `handleDismiss` — set toast ke `null`
- Semua TypeScript interfaces (`ExportServiceProps`, `ExportFormat`, `ToastState`, `ToastProps`)
- Penanganan `ApiTimeoutError`
- `window.open(url, '_blank')` untuk trigger download

### Tidak Ada `style={}` Inline
Sesuai requirements, tidak ada atribut `style={}` di komponen ini.

---

## Struktur Kode

### Komponen Utama

```tsx
ExportService(props: ExportServiceProps): JSX.Element
```
Root component. Mengelola state `format`, `exporting`, dan `toast`. Merender button group + toast notification.

### Sub-komponen

```tsx
Toast(props: ToastProps): JSX.Element
```
Komponen notifikasi internal. Menerima `message`, `type`, `onDismiss`, dan opsional `onRetry`.

### Hooks yang Digunakan

| Hook | Tujuan |
|------|--------|
| `useState<ExportFormat>` | Format ekspor aktif (default: 'csv') |
| `useState<boolean>` | Status proses ekspor berjalan |
| `useState<ToastState \| null>` | State notifikasi toast |
| `useEffect` | Auto-dismiss toast sukses setelah 5 detik |
| `useCallback` | Memoize `handleExport`, `handleRetry`, `handleDismiss` |

---

## Simulasi / Skenario

### Skenario 1 — Ekspor Berhasil (Happy Path)

**Input:** Pengguna memilih format "Excel" dan klik tombol Export pada halaman Campaign Overview dengan filter bulan Januari 2025.

**Proses:**
1. Tombol berubah menjadi `Loader2 animate-spin` + teks "Mengekspor"
2. `api.exportData({ page: 'campaign_overview', format: 'excel', filters: [...], ... })` dipanggil
3. API merespons `{ status: 'completed', download_url: 'https://s3.amazonaws.com/...' }`
4. `window.open(url, '_blank')` dieksekusi — file Excel terunduh di tab baru
5. Toast hijau muncul di pojok kanan bawah: ikon `CheckCircle` + "File siap diunduh"
6. Setelah 5 detik, toast otomatis menghilang

**Output:** File Excel terunduh, notifikasi sukses muncul lalu hilang otomatis.

### Skenario 2 — Ekspor Timeout

**Input:** Pengguna mencoba ekspor dengan rentang data 1 tahun penuh — server butuh lebih dari 30 detik.

**Proses:**
1. `api.exportData()` melempar `ApiTimeoutError` atau merespons `{ status: 'timeout' }`
2. Toast kuning muncul: ikon `AlertCircle` + "Ekspor timeout (>30 detik). Coba kurangi rentang data atau coba lagi"
3. Tombol "Coba Lagi" muncul di dalam toast

**Output:** Toast warning dengan opsi retry. Pengguna bisa klik "Coba Lagi" atau mempersempit rentang data.

### Skenario 3 — Ekspor Gagal (Server Error)

**Input:** Server merespons dengan error internal.

**Proses:**
1. API merespons `{ status: 'error', error_message: 'Database connection failed' }`
2. Toast merah muncul: ikon `XCircle` + "Ekspor gagal: Database connection failed. Coba lagi"
3. Tombol "Coba Lagi" tersedia; tombol X untuk dismiss

**Output:** Notifikasi merah informatif tanpa tanda seru berlebihan.

---

## Keterkaitan dengan Komponen Lain

**Bergantung pada:**
- `../services/api` — fungsi `api.exportData()` dan class `ApiTimeoutError`
- `../types/api` — tipe `ActiveFilter` dan `ExportRequest`
- `lucide-react` — ikon `Download`, `Loader2`, `CheckCircle`, `AlertCircle`, `XCircle`, `X`
- Tailwind CSS — sudah dikonfigurasi di `tailwind.config.js` (Task 1.2)

**Digunakan oleh:**
- `CampaignOverviewPage` — tombol ekspor di header halaman
- `CampaignComparisonPage` — ekspor hasil perbandingan
- `TimeToTakeUpPage` — ekspor data analisis waktu
- `RegionalPerformancePage` — ekspor data regional
- `CustomerCriteriaPage` — ekspor data kriteria nasabah
- `SimilarCampaignPage` — ekspor daftar campaign serupa

**Pengaruh ke:**
- Jika pesan toast diubah, semua halaman yang menggunakan `ExportService` akan terpengaruh
- Jika warna button utama `#005E6A` berubah, update di file ini dan Tailwind config

---

## Requirements yang Dipenuhi

| Requirement | Deskripsi |
|-------------|-----------|
| 4.1 | Tombol Export menggunakan ikon `Download` dari Lucide — bukan emoji |
| 4.2 | Saat loading, menampilkan `Loader2 animate-spin` — bukan emoji `⏳` |
| 4.3 | Toast sukses: `CheckCircle` + `bg-emerald-600` — bukan `✅` |
| 4.4 | Toast warning: `AlertCircle` + `bg-amber-500` — bukan `⚠️` |
| 4.5 | Toast error: `XCircle` + `bg-rose-600` — bukan `❌` |
| 4.6 | Toast diposisikan `fixed bottom-5 right-5 max-w-sm z-50` |
| 4.7 | Tombol dismiss toast menggunakan ikon `X` — bukan karakter `✕` |
| 4.8 | Tidak ada emoji di manapun dalam komponen |
| 4.9 | Seluruh styling menggunakan Tailwind CSS — tidak ada import `ExportService.css` |
| 4.10 | Pesan toast formal tanpa tanda seru: "File siap diunduh", "Ekspor gagal", "Ekspor timeout" |

---

## Catatan Penting

- **ExportService.css belum dihapus dari filesystem** — file CSS lama masih ada di disk. Import-nya sudah dihapus dari komponen ini. Penghapusan file CSS akan dilakukan di Task 15.1.
- **Logika bisnis tidak diubah sama sekali** — hanya presentasi visual yang berubah.
- **`select` element mempertahankan styling minimal** — elemen native browser untuk kompatibilitas maksimal. Focus ring menggunakan `focus:ring-[#005E6A]`.
- **`aria-busy` pada button** — atribut aksesibilitas dipertahankan untuk screen reader saat proses ekspor berjalan.
- **Toast tidak menggunakan portal** — toast dirender in-tree dengan `position: fixed` melalui Tailwind, sehingga tidak memerlukan `ReactDOM.createPortal`.
