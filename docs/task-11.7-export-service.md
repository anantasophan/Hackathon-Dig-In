# Task 11.7 — ExportService: Komponen Ekspor Data Dashboard

## Ringkasan Singkat

`ExportService` adalah komponen React TypeScript yang dapat dipasang di halaman mana pun pada dashboard Campaign Insight Generator. Komponen ini menampilkan tombol **Export** beserta pemilih format (CSV, Excel, PDF), memanggil API backend untuk menghasilkan file, lalu mengunduhnya otomatis lewat *presigned URL* begitu file siap. Semua kondisi — sukses, timeout, dan error — ditangani dan dikomunikasikan kepada pengguna melalui notifikasi *toast* inline.

---

## Penjelasan Awam (Non-Technical)

Bayangkan tombol "Print" di sebuah laporan bank. Pengguna memilih format yang diinginkan (Excel untuk diolah lebih lanjut, PDF untuk presentasi, CSV untuk analitik), lalu menekan tombol. Sistem menyiapkan file di belakang layar; begitu file siap, unduhan dimulai otomatis dan muncul pesan hijau "File siap diunduh!"

Kalau server terlalu lama menyiapkan file (lebih dari 30 detik), akan muncul pesan kuning yang menyarankan pengguna untuk mempersempit rentang data atau mencoba lagi. Kalau ada kesalahan teknis, muncul pesan merah beserta penjelasan dan tombol "Coba Lagi" — sehingga pengguna tidak perlu mengulangi seluruh proses dari awal.

**Manfaat bagi pengguna bisnis:**
- Bisa langsung mendapat file laporan dari halaman mana pun tanpa perlu keluar dari dashboard.
- Filter yang sedang aktif (periode, wilayah, channel) otomatis disertakan dalam file yang diunduh — tidak perlu filter ulang di Excel.
- Informasi metadata (nama filter, rentang waktu, sumber halaman) tercantum dalam file ekspor, sehingga laporan bisa langsung didistribusikan ke stakeholder.

---

## Penjelasan Teknis

### File yang Dibuat

| File | Deskripsi |
|------|-----------|
| `frontend/src/components/ExportService.tsx` | Komponen React utama |
| `frontend/src/components/ExportService.css` | Stylesheet — button group + toast notifications |

### Library dan Framework

- **React 18** — `useState`, `useEffect`, `useCallback`, `FC`
- **TypeScript strict mode** — semua tipe dideklarasikan eksplisit, tidak ada `any` kecuali pada `catch (err: unknown)`
- **Axios** via `api.exportData()` dari `../services/api`
- Tidak menggunakan Tailwind — semua styling via CSS murni

### Pola Arsitektur

1. **Reusable dumb component** — menerima `page`, `filters`, `timeRangeStart`, `timeRangeEnd`, dan `disabled` sebagai props; tidak menyimpan state domain.
2. **Inline Toast sub-component** — `Toast` didefinisikan dalam file yang sama, tidak diekspos sebagai export publik; hanya digunakan oleh `ExportService`.
3. **Auto-dismiss via `useEffect`** — toast bertipe `success` dihapus otomatis setelah 5 detik; toast `warning`/`error` tetap tampil sampai pengguna menutup atau menekan "Coba Lagi".
4. **Error disambiguation** — `ApiTimeoutError` dari `api.ts` diperlakukan sama dengan `response.status === 'timeout'` sehingga pesan timeout muncul baik ketika backend merespons dengan status `"timeout"` maupun ketika Axios client-timeout (35 detik) terpicu lebih dahulu.

### Keputusan Desain

- `void handleExport()` digunakan pada event handler untuk memenuhi aturan TypeScript `no-floating-promises` tanpa harus menggunakan `eslint-disable`.
- Format default diset ke `'csv'` karena paling ringan dan paling umum digunakan untuk analitik lanjutan.
- Tombol Export dan select format dinonaktifkan bersamaan selama proses ekspor berlangsung (`isButtonDisabled`) untuk mencegah request ganda.
- Toast diposisikan `absolute` di bawah kanan komponen (bukan `fixed` di pojok layar) agar tidak mengganggu konten halaman lain ketika beberapa halaman dipasang `ExportService` secara bersamaan.

### Edge Cases yang Ditangani

| Kondisi | Penanganan |
|---------|-----------|
| `response.status === 'timeout'` | Toast warning + retry |
| `ApiTimeoutError` (client timeout 35 s) | Toast warning + retry |
| `response.status === 'error'` | Toast error dengan `error_message` dari respons |
| Exception lain (network, 5xx, dll) | Toast error dengan `err.message` |
| `response.status === 'completed'` tapi `download_url` kosong | Tidak ada unduhan; toast success tidak ditampilkan — kondisi ini dijaga oleh kondisi `response.status === 'completed' && response.download_url` |
| `disabled={true}` dari parent | Tombol dan select dinonaktifkan; klik `handleExport` di-guard early-return |

---

## Struktur Kode

```typescript
// Props komponen
interface ExportServiceProps {
  page: string;            // e.g. "campaign_overview"
  filters: ActiveFilter[]; // filter aktif dari halaman induk
  timeRangeStart: string;  // yyyy-mm-dd
  timeRangeEnd: string;    // yyyy-mm-dd
  disabled?: boolean;      // nonaktifkan saat data belum dimuat
}

// State internal
const [format, setFormat] = useState<'pdf' | 'excel' | 'csv'>('csv');
const [exporting, setExporting] = useState(false);
const [toast, setToast] = useState<ToastState | null>(null);

// Sub-komponen Toast
interface ToastProps {
  message: string;
  type: 'success' | 'warning' | 'error';
  onDismiss: () => void;
  onRetry?: () => void;  // hanya untuk warning/error
}
```

### Fungsi Utama

| Fungsi | Deskripsi |
|--------|-----------|
| `handleExport()` | Async — memanggil `api.exportData()`, mengelola state, men-trigger download, dan menetapkan toast |
| `handleRetry()` | Memanggil ulang `handleExport()` dari tombol "Coba Lagi" di dalam toast |
| `handleDismiss()` | Menutup toast secara manual |
| `useEffect([toast])` | Auto-dismiss toast success setelah 5 detik |

---

## Simulasi / Skenario

### Skenario 1 — Ekspor Sukses (Happy Path)

**Konteks:** Campaign Owner berada di halaman Campaign Overview dengan filter periode 3 bulan terakhir, channel `wa`, wilayah 5.

**Input:**
```typescript
<ExportService
  page="campaign_overview"
  filters={[
    { field: "media_blasting", values: ["wa"] },
    { field: "wilayah", values: ["5"] }
  ]}
  timeRangeStart="2025-04-01"
  timeRangeEnd="2025-07-01"
/>
```

**Proses:**
1. Pengguna memilih format "Excel" dari dropdown, lalu klik "📥 Export".
2. Tombol berganti menjadi "⏳ Mengekspor..." dan dinonaktifkan.
3. `api.exportData()` mengirim `POST /api/export` dengan body lengkap.
4. Backend merespons dalam 8 detik: `{ status: "completed", download_url: "https://s3.amazonaws.com/..." }`.
5. `window.open(download_url, '_blank')` membuka tab baru → unduhan dimulai.

**Output:**
- Tombol kembali aktif.
- Toast hijau: `✅ File siap diunduh!` — hilang otomatis setelah 5 detik.

---

### Skenario 2 — Timeout (>30 detik)

**Proses:**
1. Backend tidak merespons dalam batas waktu; mengembalikan `{ status: "timeout" }`.
2. Tombol kembali aktif.

**Output:**
- Toast kuning: `⚠️ Ekspor timeout (>30 detik). Coba kurangi rentang data atau coba lagi.`
- Tombol "Coba Lagi" tersedia di toast.

---

### Skenario 3 — Error Teknis

**Proses:**
1. Server mengembalikan `{ status: "error", error_message: "Athena query execution failed" }`.

**Output:**
- Toast merah: `❌ Ekspor gagal: Athena query execution failed. Coba lagi.`
- Tombol "Coba Lagi" dan tombol tutup (✕) tersedia.

---

## Cara Penggunaan di Halaman Lain

```tsx
import ExportService from '../components/ExportService';

// Di dalam CampaignOverviewPage, setelah data dimuat:
<ExportService
  page="campaign_overview"
  filters={activeFilters}      // ActiveFilter[] dari state halaman
  timeRangeStart={dateRange.startDate}
  timeRangeEnd={dateRange.endDate}
  disabled={!dataLoaded}       // nonaktifkan saat data masih loading
/>
```

Komponen ini bisa dipasang di header halaman, toolbar atas, atau di manapun yang relevan — karena menggunakan `display: inline-flex` dan posisi toast `absolute`.

---

## Keterkaitan dengan Komponen Lain

- **Bergantung pada:**
  - `api.exportData()` — `frontend/src/services/api.ts`
  - `ApiTimeoutError` — `frontend/src/services/api.ts`
  - `ExportRequest`, `ExportResponse`, `ActiveFilter` — `frontend/src/types/api.ts`
- **Digunakan oleh:** Semua halaman dashboard yang menyediakan fitur ekspor (CampaignOverviewPage, RegionalPerformancePage, dll.)
- **Pengaruh ke:** Backend Lambda `export_service` — `POST /api/export`

---

## Requirements yang Dipenuhi

| Requirement | Acceptance Criteria |
|-------------|---------------------|
| 8.1 | Ekspor menggunakan filter aktif halaman; format PDF, Excel, CSV tersedia |
| 8.2 | Metadata (filter aktif, rentang waktu, nama halaman) dikirim ke backend lewat `ExportRequest` |
| 8.3 | Unduhan otomatis via `window.open(download_url, '_blank')` + notifikasi sukses in-app |
| 8.4 | Timeout ditangani: toast warning + opsi retry |
| 8.5 | Error teknis ditangani: toast error dengan pesan penyebab + opsi retry |

---

## Catatan Penting

- **Posisi toast:** Toast diposisikan `absolute` relatif terhadap `.export-service`. Halaman yang meng-host komponen ini perlu memastikan wrapper memiliki `position: relative` (atau `overflow: visible`) agar toast tidak terpotong.
- **`window.open` dan popup blocker:** Browser dengan popup blocker ketat mungkin memblokir `window.open` jika tidak dipanggil secara sinkron dari event user. Karena ada `await api.exportData()` di antaranya, beberapa browser dapat memblokir ini. Solusi alternatif (membuat `<a>` element dan klik programatis) bisa diimplementasikan jika menjadi masalah di production.
- **Retry state:** Saat pengguna menekan "Coba Lagi", toast lama dihapus dan proses ekspor dimulai ulang dengan format dan filter yang sama.
- **Format default CSV:** Dipilih karena ukuran file terkecil; bisa diubah ke `'excel'` jika kebutuhan bisnis berubah.
