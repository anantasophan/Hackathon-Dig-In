# Task 11.3 — Time to Take Up Page

## Ringkasan Singkat

Halaman **Time to Take Up** menampilkan analisis distribusi waktu yang dibutuhkan nasabah untuk melakukan take up setelah menerima kampanye. Pengguna memasukkan Campaign ID, memilih filter channel dan wilayah opsional, lalu menekan tombol "Lihat Analisis" untuk memuat histogram distribusi dan kartu statistik ringkasan.

---

## Penjelasan Awam (Non-Technical)

Bayangkan sebuah kampanye bank mengirimkan penawaran kepada 10.000 nasabah. Beberapa nasabah langsung merespons dalam 1–7 hari; yang lain baru merespons setelah 60–90 hari; sebagian tidak merespons sama sekali.

Halaman ini menjawab pertanyaan: **"Berapa lama biasanya nasabah butuh waktu sebelum memutuskan ikut?"**

Jawabannya ditampilkan dalam bentuk:
- **Grafik batang (histogram)** — setiap batang mewakili satu rentang waktu (mis. 0–7 hari, 7–14 hari, dst.) dan tingginya menunjukkan berapa persen nasabah take up di rentang itu.
- **Kartu statistik** — angka median, rata-rata, minimum, maksimum, dan total nasabah yang take up.

Pengguna bisnis bisa menyaring data berdasarkan **channel** (mis. WhatsApp, email) dan **wilayah** untuk memahami apakah ada perbedaan perilaku antar segmen.

---

## Penjelasan Teknis

### File yang Dibuat / Dimodifikasi

| File | Tindakan |
|------|----------|
| `frontend/src/pages/TimeToTakeUpPage.tsx` | **Dibuat** — komponen utama halaman |
| `frontend/src/pages/TimeToTakeUpPage.css` | **Dibuat** — scoped CSS tanpa Tailwind |
| `frontend/src/App.tsx` | **Dimodifikasi** — rute `/time-analysis` diganti dari `PlaceholderPage` ke `TimeToTakeUpPage` |

### Library / Framework

- **React 18** — functional component dengan hooks (`useState`, `useCallback`)
- **Chart.js + react-chartjs-2** — rendering histogram `Bar` chart
- **Axios** (via `api.ts`) — pemanggilan `GET /api/campaigns/time-analysis/{id}`

### Arsitektur Komponen

```
TimeToTakeUpPage
├── DashboardLayout (wrapper layout & navigasi)
├── Input card
│   ├── Campaign ID input (required)
│   ├── Channel select (optional, enum: wa/digisales/telesales/email/push notif/sms)
│   └── Region text input (optional, angka 1–17)
├── State boxes (pre-fetch / loading / error / empty)
├── StatCard × 5 (Median, Rata-rata, Min, Max, Total Take Up)
└── Histogram card
    └── <Bar> chart (Chart.js)
```

### Keputusan Desain

1. **Campaign ID input wajib + tombol fetch terpisah** — mengikuti pola `CampaignComparisonPage`. Data tidak dimuat otomatis saat load karena membutuhkan Campaign ID eksplisit.
2. **Region dibatasi input numerik 1–17** — validasi via regex di `onChange`, bukan validasi server-side saja, agar UX lebih responsif.
3. **`void handleFetch()`** — async handler dibungkus dengan `void` untuk menghindari floating promise saat dipanggil dari event handler (`onClick`/`onKeyDown`).
4. **Bucket labels hardcoded** — label `BUCKET_LABELS` sejajar urutan yang dikembalikan API, di-slice sesuai panjang `histogram` untuk fleksibilitas.
5. **Count di tooltip** — dataset diisi field custom `counts` agar tooltip bisa menampilkan jumlah nasabah di samping persentase tanpa memanipulasi data utama Chart.js.
6. **Tidak ada auto-refetch saat filter berubah** — pengguna harus menekan "Lihat Analisis" lagi, menghindari panggilan API berlebihan (terutama penting karena Athena memiliki biaya per query).

### Edge Cases yang Ditangani

| Kondisi | Penanganan |
|---------|-----------|
| Campaign ID kosong | Tombol disabled, tidak ada panggilan API |
| API mengembalikan field `message` | Pesan dari API ditampilkan di state box empty |
| `histogram` kosong atau null | State box "Tidak ada data take up untuk filter tersebut" |
| Error jaringan / HTTP | State box error dengan pesan dari Error object |
| Loading state | Spinner + `aria-busy="true"` |

---

## Struktur Kode

```typescript
// Konstanta
CHANNEL_OPTIONS: string[]    // ['wa', 'digisales', 'telesales', 'email', 'push notif', 'sms']
BUCKET_LABELS: string[]      // label 7 bucket histogram

// Helpers
buildChartData(data: TimeAnalysisResponse): ChartData
  // Mengonversi histogram API ke format Chart.js; menyisipkan counts sebagai field custom

chartOptions: ChartOptions   // Config Chart.js: Y-axis 0–100%, tooltip dengan count

// Sub-component
StatCard({ label, value, icon }): JSX.Element
  // Kartu statistik tunggal

// Main component
TimeToTakeUpPage(): JSX.Element
  // State: campaignId, channel, region, data, emptyMessage, loading, error, hasFetched
  // handleFetch(): async — memanggil api.getTimeAnalysis() dan mengisi state
  // handleKeyDown(): trigger handleFetch saat Enter di input Campaign ID
```

---

## Simulasi / Skenario

### Skenario 1 — Happy Path

**Input:**
- Campaign ID: `KMP-2024-001`
- Channel: `wa`
- Wilayah: `5`

**Proses:**
1. Pengguna isi Campaign ID, pilih channel `wa`, region `5`, klik "Lihat Analisis"
2. Komponen memanggil `api.getTimeAnalysis("KMP-2024-001", "wa", "5")`
3. API merespons dengan histogram 7 bucket dan stats

**Output:**
```
Kampanye: Program QRIS WA Region 5

[ Median: 12 hari ] [ Rata-rata: 18.3 hari ] [ Min: 1 hari ] [ Max: 87 hari ] [ Total: 3.241 nasabah ]

Histogram:
0-7 hari    ████████░░ 35%
7-14 hari   ██████░░░░ 28%
14-21 hari  ███░░░░░░░ 14%
21-30 hari  ██░░░░░░░░ 9%
30-60 hari  ██░░░░░░░░ 8%
60-90 hari  █░░░░░░░░░ 4%
90+ hari    ░░░░░░░░░░ 2%
```

### Skenario 2 — Empty State (Filter Terlalu Ketat)

**Input:**
- Campaign ID: `KMP-2024-001`
- Channel: `sms`
- Wilayah: `17`

**Output:**
```
📭 Tidak ada data take up untuk filter tersebut
```

### Skenario 3 — Campaign ID Tidak Ditemukan

**Input:**
- Campaign ID: `KMP-TIDAK-ADA`

**Output API:**
```json
{ "message": "Campaign KMP-TIDAK-ADA tidak ditemukan" }
```

**Output UI:**
```
📭 Campaign KMP-TIDAK-ADA tidak ditemukan
```

---

## Keterkaitan dengan Komponen Lain

- **Bergantung pada:**
  - `DashboardLayout` — wrapper layout & navigasi sidebar
  - `api.getTimeAnalysis()` di `frontend/src/services/api.ts`
  - `TimeAnalysisResponse`, `TimeHistogramBucket`, `TimeAnalysisStats` dari `frontend/src/types/api.ts`
  - Chart.js + react-chartjs-2

- **Digunakan oleh:**
  - `App.tsx` — di-render pada rute `/time-analysis`

- **Pengaruh ke:**
  - Jika `TimeAnalysisResponse` berubah (field baru/dihapus), update `buildChartData` dan `StatCard` values

---

## Requirements yang Dipenuhi

| Requirement | Keterangan |
|-------------|-----------|
| 3.1 | Halaman Time to Take Up tersedia di rute `/time-analysis` |
| 3.2 | Histogram distribusi waktu take up ditampilkan dengan Chart.js Bar |
| 3.3 | Statistik median, mean, min, max, total take up ditampilkan sebagai kartu |
| 3.4 | Filter channel (dropdown enum) terintegrasi |
| 3.5 | Filter region (input numerik 1–17) terintegrasi |
| 3.6 | State kosong yang informatif ditampilkan untuk semua kondisi (pre-fetch, empty, error) |

---

## Catatan Penting

- **Region input** menerima string, diteruskan ke API sebagai query param string. Backend Time Analysis Lambda mengonversi ke integer internal.
- **Tidak ada auto-fetch** — berbeda dengan `CampaignOverviewPage` yang auto-fetch saat load karena tidak memerlukan ID eksplisit.
- Tooltip Chart.js menggunakan field `counts` yang disisipkan sebagai property custom pada dataset. Ini adalah pola yang didukung Chart.js tapi perlu dijaga konsistensinya jika struktur dataset berubah.
- Jika API mengembalikan lebih atau lebih sedikit dari 7 bucket, `BUCKET_LABELS.slice(0, histogram.length)` memastikan label tetap sinkron dengan data.
