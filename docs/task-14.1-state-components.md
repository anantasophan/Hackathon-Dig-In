# Task 14.1 — Ekstrak Shared State Components (EmptyState, LoadingState, ErrorState)

## Ringkasan Singkat

Task ini mengekstrak pola-pola tampilan berulang (kosong, loading, error) yang sebelumnya ditulis secara terpisah di setiap halaman menjadi tiga komponen bersama yang dapat digunakan ulang: `EmptyState`, `LoadingState`, dan `ErrorState`. Komponen-komponen ini disimpan di `frontend/src/components/StateComponents.tsx` dan diimpor di 6 halaman dashboard.

## Penjelasan Awam (Non-Technical)

Bayangkan sebuah toko yang memiliki 6 karyawan. Setiap karyawan biasanya mengatakan hal yang berbeda ketika toko sedang tutup: "Stok habis", "Sedang restok", "Toko sedang libur". Task ini memastikan semua karyawan menggunakan papan pengumuman yang sama — sehingga pesan yang ditampilkan konsisten kepada semua pelanggan di manapun mereka berada di dalam toko.

Manfaat untuk pengguna bisnis:
- Tampilan "Tidak ada data", "Memuat data", dan "Terjadi kesalahan" kini seragam di seluruh halaman
- Mudah diubah di satu tempat jika perlu update teks atau ikon

## Penjelasan Teknis

### File yang Dibuat

**`frontend/src/components/StateComponents.tsx`** — file baru berisi tiga komponen React:

| Komponen | Props | Penggunaan |
|----------|-------|------------|
| `EmptyState` | `message?`, `hint?` | Ketika query mengembalikan nol hasil |
| `LoadingState` | `text?` | Ketika request API sedang berjalan |
| `ErrorState` | `message` (required) | Ketika API request gagal |

Setiap komponen menggunakan Lucide React icons (`Inbox`, `Loader2`, `AlertCircle`) dan Tailwind CSS utility classes sesuai BNI Design System.

### File yang Dimodifikasi

Semua 6 halaman berikut diupdate untuk mengimpor dan menggunakan komponen bersama:

1. `CampaignOverviewPage.tsx` — loading/error/empty state diganti
2. `CampaignComparisonPage.tsx` — loading/error/empty (idle) state diganti
3. `TimeToTakeUpPage.tsx` — loading/error/empty state diganti
4. `RegionalPerformancePage.tsx` — loading/error/empty state diganti (idle MapPin state tetap)
5. `CustomerCriteriaPage.tsx` — state di dalam card wrapper diganti
6. `SimilarCampaignPage.tsx` — loading/error state diganti; idle (`Search`) dan no-results (`SearchX`) state tetap karena page-specific

### Keputusan Desain Penting

- **SimilarCampaignPage** memiliki dua state yang sengaja tidak diganti:
  - Idle state (sebelum search): menggunakan ikon `Search` dengan pesan custom
  - No-results state: menggunakan ikon `SearchX` yang spesifik untuk konteks pencarian
  - Loading state menggunakan `<LoadingState text="Mencari" />` karena teks "Mencari" lebih sesuai daripada default "Memuat data"

- **CustomerCriteriaPage** mempertahankan card wrapper (`bg-white border ...rounded-xl`) di sekeliling state components karena konsisten dengan layout halaman tersebut

- Lucide icons yang tidak lagi digunakan langsung di halaman (seperti `Loader2`, `Inbox`, `AlertCircle`) dihapus dari impor masing-masing halaman untuk menghindari unused import warnings

## Struktur Kode

```tsx
// StateComponents.tsx

export const EmptyState: React.FC<EmptyStateProps> = ({ message, hint }) => (
  <div className="text-center py-12 text-gray-400">
    <Inbox className="w-8 h-8 mx-auto mb-2 text-gray-300" />
    <p className="text-sm font-medium">{message}</p>
    <p className="text-xs mt-1">{hint}</p>
  </div>
);

export const LoadingState: React.FC<LoadingStateProps> = ({ text }) => (
  <div className="text-center py-12 text-gray-400">
    <Loader2 className="w-8 h-8 mx-auto mb-2 animate-spin text-[#005E6A]" />
    <p className="text-sm font-medium">{text}</p>
  </div>
);

export const ErrorState: React.FC<ErrorStateProps> = ({ message }) => (
  <div className="text-center py-12">
    <AlertCircle className="w-8 h-8 mx-auto mb-2 text-rose-400" />
    <p className="text-sm font-medium text-rose-600">Terjadi kesalahan</p>
    <p className="text-xs mt-1 text-gray-500">{message}</p>
  </div>
);
```

## Simulasi / Skenario

### Skenario 1 — Empty State (CampaignComparisonPage)
- **Input**: Pengguna belum menekan tombol "Bandingkan"
- **Proses**: `result === null && !isLoading && !apiError` → render `<EmptyState hint="Pilih 2–5 campaign..." />`
- **Output**: Inbox icon + "Tidak ada data tersedia" + hint text

### Skenario 2 — Loading State dengan Custom Text (SimilarCampaignPage)
- **Input**: Pengguna menekan "Cari Campaign Serupa"
- **Proses**: `loading === true` → render `<LoadingState text="Mencari" />`
- **Output**: Spinning teal Loader2 icon + "Mencari"

### Skenario 3 — Error State (RegionalPerformancePage)
- **Input**: API timeout saat mencari data wilayah
- **Proses**: `error !== null && !loading` → render `<ErrorState message="Terjadi kesalahan... Periksa Campaign ID dan coba lagi." />`
- **Output**: Rose AlertCircle icon + "Terjadi kesalahan" heading + detail message

## Keterkaitan dengan Komponen Lain

- **Bergantung pada**: `lucide-react` (Inbox, Loader2, AlertCircle icons), Tailwind CSS
- **Digunakan oleh**: CampaignOverviewPage, CampaignComparisonPage, TimeToTakeUpPage, RegionalPerformancePage, CustomerCriteriaPage, SimilarCampaignPage
- **Pengaruh ke**: Perubahan pada teks default atau styling di `StateComponents.tsx` akan mempengaruhi tampilan di semua 6 halaman secara serentak

## Requirements yang Dipenuhi

- **11.1**: Empty state seragam dengan pola `text-center py-12 text-gray-400` + Lucide icon `w-8 h-8 text-gray-300`
- **11.2**: Tidak ada emoji pada empty state di seluruh halaman
- **11.3**: Loading state menggunakan `Loader2 animate-spin text-[#005E6A]`
- **11.4**: Error state menggunakan `AlertCircle text-rose-600`
- **11.5**: Teks status formal: "Tidak ada data tersedia", "Terjadi kesalahan", "Memuat data" — tanpa tanda seru

## Catatan Penting

- Build failure yang ada (`TS2582: Cannot find name 'describe'` di `CampaignChip.property.test.tsx`) adalah **pre-existing** — sudah ada sebelum task ini dikerjakan dan tidak berkaitan dengan perubahan di task 14.1
- Semua 7 file (StateComponents.tsx + 6 halaman) melewati TypeScript diagnostics tanpa error
- `EmptyState.hint` default = "Silakan sesuaikan filter untuk menampilkan data" — halaman yang memerlukan hint berbeda dapat meng-override via prop
