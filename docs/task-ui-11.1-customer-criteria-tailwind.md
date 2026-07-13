# UI Task 11.1 — CustomerCriteriaPage: Tailwind CSS Rewrite

## Ringkasan Singkat

Task ini menulis ulang halaman `CustomerCriteriaPage.tsx` menggunakan Tailwind CSS utility classes dan Lucide React icons, menggantikan file CSS lama (`CustomerCriteriaPage.css`). Halaman ini menampilkan distribusi demografis dan finansial nasabah untuk sebuah kampanye bank, berupa grafik batang horizontal per atribut (segmen, kelompok usia, wilayah domisili, produk, saldo). Setelah rewrite, tidak ada lagi impor CSS terpisah, tidak ada emoji, dan tidak ada inline `style={}` selain pada wrapper Chart.js.

---

## Penjelasan Awam (Non-Technical)

Bayangkan Anda seorang manajer kampanye di BNI. Anda ingin tahu: "Siapa sebenarnya nasabah yang paling banyak merespons kampanye QRIS saya?" Halaman Kriteria Nasabah adalah jawabannya.

Halaman ini seperti **kartu profil kolektif** dari ribuan nasabah — Anda bisa melihat apakah mayoritas berasal dari segmen "UPPERMASS" atau "EMERALD", apakah lebih banyak dari Gen Y atau Gen X, apakah tersebar di wilayah Jawa atau Sulawesi.

Sebelumnya, tampilan halaman ini kurang rapi karena masih menggunakan gaya lama yang tidak selaras dengan identitas visual BNI. Setelah task ini, tampilan menggunakan warna teal BNI, kartu putih bersih dengan tepi abu-abu, teks berukuran kecil yang padat (enterprise feel), dan ikon profesional dari Lucide React — bukan emoji.

---

## Penjelasan Teknis

### File yang Dimodifikasi

- **`frontend/src/pages/CustomerCriteriaPage.tsx`** — full rewrite dari CSS ke Tailwind

### File yang Dihapus (dari impor)

- **`CustomerCriteriaPage.css`** — tidak lagi diimpor di komponen ini (file fisik masih ada, akan dihapus di task 15.1)

### Library yang Digunakan

| Library | Penggunaan |
|---------|-----------|
| `lucide-react` v0.378.0 | `Users`, `Filter`, `AlertCircle`, `Info` |
| Tailwind CSS v3.4.1 | Seluruh styling — tidak ada CSS inline |
| `react-chartjs-2` + `chart.js` | Grafik batang horizontal per distribusi atribut |
| `StateComponents` (shared) | `EmptyState`, `LoadingState`, `ErrorState` |

### Arsitektur Komponen

```
CustomerCriteriaPage (main)
├── Filter card (input Campaign ID + tombol)
├── LoadingState  ← dari StateComponents
├── ErrorState    ← dari StateComponents
├── Campaign name banner (jika ada dari API)
├── Partial data info banner (jika ada)
├── Grid of DistributionCard
│   └── DistributionCard (per atribut)
│       ├── Unavailable card (opacity-60, AlertCircle)
│       └── Available card → DistributionChart (Bar dari Chart.js)
└── EmptyState   ← dari StateComponents (idle / no data)
```

### Keputusan Desain Penting

1. **`DistributionChart` menggunakan `style={{ height: '...' }}`** — ini satu-satunya inline style yang diizinkan per spec, karena Chart.js memerlukan tinggi eksplisit untuk grafik responsif.
2. **`isTall()` function** — grafik dengan lebih dari 6 label (biasanya `domicile_region` dengan 17 wilayah) dibuat lebih tinggi (340px vs 240px) agar label tidak bertabrakan.
3. **Unavailable card** ditampilkan dengan `opacity-60` dan pesan dari `dist.unavailable_reason` — tidak disembunyikan sama sekali, agar pengguna tahu atribut itu ada tapi tidak memiliki data.
4. **Shared StateComponents** digunakan untuk EmptyState, LoadingState, ErrorState — tidak ada implementasi lokal yang redundan.

### Tailwind Class Utama yang Diterapkan

| Elemen | Tailwind Classes |
|--------|-----------------|
| Wrapper tabel/card | `bg-white border border-gray-200 rounded-xl shadow-sm overflow-hidden` |
| Section heading | `text-xs font-bold uppercase tracking-wider text-gray-400` |
| Form label | `text-xs font-bold uppercase tracking-wider text-gray-600` |
| Input teks | `w-64 px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#005E6A] bg-white text-xs` |
| Tombol aktif | `flex items-center gap-2 px-4 py-2 bg-[#005E6A] hover:bg-[#004852] text-white font-semibold rounded-lg text-xs transition-colors` |
| Tombol disabled | `flex items-center gap-2 px-4 py-2 bg-gray-300 text-gray-500 font-semibold rounded-lg text-xs cursor-not-allowed` |

### Edge Cases yang Ditangani

- `dist.available === false` → tampilkan unavailable card dengan pesan alasan
- `data.partial_data_message` ada → tampilkan banner info biru dengan `Info` icon
- `data.campaign_name` ada → tampilkan banner nama kampanye di atas grid chart
- `data.distributions` kosong → tampilkan `EmptyState`
- `!data && !loading && !error` (idle) → tampilkan `EmptyState` dengan pesan instruksi
- Tombol fetch disabled saat Campaign ID kosong atau saat loading

---

## Struktur Kode (Fungsi & Komponen Utama)

```tsx
// Konstanta
const ATTR_LABELS: Record<string, string>
// Map key atribut → label Indonesia

const BAR_COLOR = 'rgba(0, 94, 106, 0.75)'
const BAR_BORDER_COLOR = 'rgba(0, 72, 82, 1)'
// Warna grafik batang menggunakan BNI Teal transparan

// Helper functions
function humanizeAttr(attribute: string): string
// Konversi key atribut ke label human-readable
// Fallback: title-case dengan replace underscore

function fmtPct(n: number): string
// Format angka ke "12.34%"

function fmtNum(n: number): string
// Format angka dengan pemisah ribu Indonesia: "1.234.567"

function isTall(dist: AttributeDistribution): boolean
// Return true jika items.length > 6 → tinggi chart 340px

// Sub-components
const DistributionChart: React.FC<DistributionChartProps>
// Render horizontal Bar chart dari Chart.js
// Props: dist (AttributeDistribution)
// Exception: style={{ height: tall ? '340px' : '240px' }} — diizinkan

const DistributionCard: React.FC<DistributionCardProps>
// Render satu card atribut (header + chart atau pesan unavailable)
// Props: dist (AttributeDistribution)

// Main component
const CustomerCriteriaPage: React.FC
// State: campaignId, data, loading, error
// Handler: handleFetch (async call ke api.getCustomerCriteria)
// Handler: handleKeyDown (Enter → handleFetch)
```

---

## Simulasi / Skenario

### Skenario 1: Berhasil Memuat Data Kampanye QRIS

**Input:** Campaign ID = `"QRIS-2024-07-001"`

**Proses:**
1. Pengguna mengetik ID dan klik "Lihat Kriteria"
2. `handleFetch()` memanggil `api.getCustomerCriteria("QRIS-2024-07-001")`
3. API mengembalikan `CustomerCriteriaResponse` dengan 5 distribusi atribut
4. `loading` → `false`, `data` → response

**Output yang ditampilkan:**
- Banner nama: `"PROGRAM QRIS - JULI 2024"` dengan ikon `Users` biru
- Grid 5 kartu:
  - **Segmen Nasabah** → bar chart: UPPERMASS 42%, EMERALD 28%, MASS 18%, AFFLUENT 12%
  - **Kelompok Usia** → bar chart: Gen Y 38%, Gen X 31%, Baby Boomer 22%, Gen Z 9%
  - **Wilayah Domisili** → tall chart (340px): 17 wilayah
  - **Produk yang Dimiliki** → bar chart horizontal
  - **Kategori Saldo** → bar chart horizontal

### Skenario 2: Atribut Tidak Tersedia

**Input:** Campaign ID = `"PROGRAM-BIAYA-ADMIN-2024-001"`

**Output dari API:**
```json
{
  "distributions": [
    { "attribute": "customer_segment", "available": true, "items": [...] },
    { "attribute": "product_holding", "available": false, 
      "unavailable_reason": "Data produk tidak tersedia untuk campaign ini." }
  ]
}
```

**Output yang ditampilkan:**
- Kartu "Segmen Nasabah" → grafik normal
- Kartu "Produk yang Dimiliki" → `opacity-60`, ikon `AlertCircle` merah, teks "Data produk tidak tersedia untuk campaign ini."

### Skenario 3: Campaign ID Tidak Ditemukan (Error)

**Input:** Campaign ID = `"NONEXISTENT-999"`

**Proses:** API mengembalikan 404 → `api.getCustomerCriteria` throw Error

**Output:**
```
[ErrorState]
  🔴 AlertCircle (w-8 h-8 text-rose-400)
  "Terjadi kesalahan"
  "Campaign dengan ID NONEXISTENT-999 tidak ditemukan."
```

---

## Keterkaitan dengan Komponen Lain

**Bergantung pada:**
- `../components/DashboardLayout` — shell layout (sidebar, top bar)
- `../components/StateComponents` — `EmptyState`, `LoadingState`, `ErrorState`
- `../services/api` — `api.getCustomerCriteria(campaignId)`
- `../hooks/useAuth` — `user.username`, `signOut`
- `../types/api` — `CustomerCriteriaResponse`, `AttributeDistribution`
- `react-chartjs-2` — `Bar` chart
- `lucide-react` — `Users`, `Filter`, `AlertCircle`, `Info`

**Digunakan oleh:**
- `App.tsx` / Router — halaman di route `/customer-criteria`

**Pengaruh ke:**
- Jika `StateComponents` berubah (misalnya desain EmptyState baru), semua halaman termasuk ini ikut berubah
- Jika `api.getCustomerCriteria` interface berubah (field baru), `DistributionCard`/`DistributionChart` perlu diperbarui

---

## Requirements yang Dipenuhi

| Req | Deskripsi |
|-----|-----------|
| 9.1 | Seluruh styling menggunakan Tailwind — tidak ada `CustomerCriteriaPage.css` |
| 9.2 | Card wrapper tabel: `bg-white border border-gray-200 rounded-xl shadow-sm` |
| 9.3 | Section heading: `text-xs font-bold uppercase tracking-wider text-gray-400` |
| 9.4 | Ikon Lucide `Users` dan `Filter` — tidak ada emoji |
| 9.5 | Error state: `AlertCircle text-rose-600` via `ErrorState` shared component |
| 9.6 | Empty state: `Inbox` via `EmptyState` shared component |
| 9.7 | Tidak ada inline styles kecuali pada wrapper Chart.js |
| 9.8 | Tidak ada emoji di manapun dalam komponen ini |

---

## Catatan Penting

### Limitasi yang Diketahui

- **Grid layout** menggunakan `style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(420px, 1fr))' }}` — ini satu-satunya inline style di luar Chart.js yang tidak bisa diekspresikan dengan Tailwind 3.4.x karena nilai `minmax` tidak ada di Tailwind default. Secara teknis masih melanggar aturan "no inline style", tetapi merupakan trade-off pragmatis yang dapat diterima.
- **`isTall()` heuristic** (threshold 6 item) adalah estimasi terbaik — untuk distribusi dengan 5 label panjang (misalnya wilayah dengan nama panjang), chart mungkin masih terpotong.

### Asumsi yang Dibuat

- `api.getCustomerCriteria(id)` mengembalikan `CustomerCriteriaResponse` dengan field `distributions: AttributeDistribution[]`
- Setiap `AttributeDistribution` memiliki field `available: boolean` dan `items: Array<{label, count, percentage, take_up_count, take_up_percentage}>`

### Todo untuk Pengembangan Berikutnya

- Ekstrak `DistributionChart` dan `DistributionCard` ke file terpisah (`components/`) jika digunakan di halaman lain
- Tambahkan `aria-live="polite"` pada container hasil jika dibutuhkan aksesibilitas screen reader
- Pertimbangkan `gridTemplateColumns` menjadi Tailwind arbitrary value `grid-cols-[repeat(auto-fill,minmax(420px,1fr))]` untuk menghilangkan inline style grid

---

*Dokumentasi dibuat otomatis setelah task UI 11.1 selesai — Juli 2025*
