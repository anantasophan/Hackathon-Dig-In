# Task 11.2 — Campaign Comparison Page

## Ringkasan Singkat

Halaman perbandingan kampanye (Campaign Comparison) memungkinkan pengguna memilih 2 hingga 5 kampanye untuk dibandingkan secara berdampingan. Hasil ditampilkan dalam tabel metrik lengkap dan grafik batang interaktif. Halaman ini digunakan oleh tim bisnis untuk mengevaluasi efektivitas relatif antar kampanye secara cepat.

---

## Penjelasan Awam (Non-Technical)

Bayangkan Anda ingin membandingkan beberapa program tabungan dari cabang yang berbeda: mana yang menghasilkan lebih banyak peserta, mana yang nilai transaksinya lebih tinggi, dan mana yang waktunya paling efisien.

Halaman ini bekerja persis seperti itu. Anda cukup:
1. Ketik ID kampanye yang ingin dibandingkan (misalnya "CAMP-001")
2. Tekan tombol **Tambah** — kampanye muncul sebagai label berwarna
3. Pilih cara pengelompokan data jika diinginkan (berdasarkan jenis program, wilayah, atau channel)
4. Tekan **Bandingkan** — sistem akan langsung menampilkan tabel dan grafik perbandingan

Sistem membatasi maksimal 5 kampanye sekaligus, dan akan menampilkan peringatan jika Anda mencoba menambah lebih dari itu. Minimal 2 kampanye diperlukan sebelum tombol Bandingkan aktif.

**Manfaat untuk pengguna bisnis:**
- Langsung lihat kampanye mana yang paling banyak menghasilkan leads
- Bandingkan take-up rate antar kampanye dalam satu tampilan
- Identifikasi kampanye dengan nilai transaksi tertinggi secara visual

---

## Penjelasan Teknis

### File yang Dibuat

| File | Deskripsi |
|------|-----------|
| `frontend/src/pages/CampaignComparisonPage.tsx` | Komponen React utama halaman perbandingan |
| `frontend/src/pages/CampaignComparisonPage.css` | CSS animasi spinner dan responsif breakpoint |

### Library / Framework

- **React 18** — komponen fungsional dengan hooks (`useState`, `useCallback`, `useRef`)
- **react-chartjs-2** + **Chart.js** — grafik batang dengan plugin: `CategoryScale`, `LinearScale`, `BarElement`, `Title`, `Tooltip`, `Legend`
- **TypeScript strict mode** — semua state dan props bertipe penuh
- **Plain CSS** — tidak menggunakan Tailwind; styling via inline style objects + keyframe di `.css`

### Pola Arsitektur

- **Controlled inputs** — nilai input dikontrol via React state (`inputValue`, `groupBy`)
- **Optimistic chip list** — campaign yang dipilih disimpan di `selectedIds: string[]` dan ditampilkan sebagai chip/tag
- **Async fetch on demand** — API dipanggil hanya saat tombol Bandingkan ditekan (bukan real-time)
- **Immutable sort** — hasil API di-spread (`[...response.campaigns]`) sebelum di-sort agar tidak memutasi state

### State Management

```typescript
const [selectedIds, setSelectedIds] = useState<string[]>([]);
const [inputValue, setInputValue] = useState('');           // ID yang sedang diketik
const [maxLimitError, setMaxLimitError] = useState(false);  // Maks 5 campaign
const [duplicateError, setDuplicateError] = useState(false);
const [emptyError, setEmptyError] = useState(false);
const [groupBy, setGroupBy] = useState<GroupByValue>('');
const [isLoading, setIsLoading] = useState(false);
const [apiError, setApiError] = useState<string | null>(null);
const [result, setResult] = useState<CampaignComparisonResponse | null>(null);
```

### Validasi UI

| Kondisi | Pesan yang Ditampilkan |
|---------|----------------------|
| Input kosong lalu klik Tambah | "Masukkan Campaign ID terlebih dahulu." |
| Campaign sudah ada di daftar | "Campaign ID ini sudah ditambahkan." |
| Sudah 5 campaign, coba tambah lagi | "Maksimal 5 campaign dapat dipilih." |
| Kurang dari 2 campaign | Tombol Bandingkan non-aktif (abu-abu) |

### Group-by Options

```typescript
const GROUP_BY_OPTIONS = [
  { value: '', label: '-- Tidak ada --' },
  { value: 'flag_program', label: 'Jenis Program' },
  { value: 'wilayah', label: 'Wilayah' },
  { value: 'media_blasting', label: 'Channel' },
];
```

Nilai dikirim ke API sebagai `group_by` field dalam `CampaignComparisonRequest`. Jika `''` dipilih, field tidak disertakan dalam request.

### Kolom Tabel Perbandingan

| Kolom | Sumber Data | Format |
|-------|-------------|--------|
| Campaign ID | `campaign_id` | String |
| Nama Campaign | `campaign_name` | String |
| Flag Program | `flag_program` | String |
| Total Leads | `total_leads` | Number (id-ID locale) |
| Total Take Up | `total_take_up` | Number (id-ID locale) |
| Take-Up Rate (%) | `take_up_rate` | `xx.xx%` |
| Nilai Transaksi (Rp) | `total_transaction_value` | IDR currency format |
| Durasi (hari) | `duration_days` | Number |

### Grafik Batang

- Satu grup bar per metrik (sumbu X), satu bar per campaign (warna berbeda)
- Nilai Transaksi diskala ke jutaan Rupiah untuk keterbacaan grafik
- 5 warna berbeda per campaign: navy, biru, hijau, oranye, ungu
- Jika `result.campaigns` kosong, tidak ada data ditampilkan

---

## Struktur Kode

```typescript
// Fungsi utama
CampaignComparisonPage: React.FC     // Komponen halaman utama

// Helper functions
formatNumber(value: number): string  // Angka dengan separator ribuan (id-ID)
formatCurrency(value: number): string // Format IDR dengan Intl.NumberFormat
formatPercent(value: number): string  // "xx.xx%"
buildChartData(campaigns: CampaignMetric[]) // Membangun data Chart.js

// Handlers (dalam komponen)
handleAddCampaign()                  // Validasi & tambah ID ke daftar
handleRemoveCampaign(id: string)     // Hapus ID dari daftar
handleInputKeyDown(e)                // Enter key → handleAddCampaign
handleCompare()                      // Panggil API, sort, simpan hasil
```

---

## Simulasi / Skenario

### Skenario 1: Perbandingan Normal (Happy Path)

**Input:**
- User mengetik `CAMP-001`, klik Tambah → chip muncul
- User mengetik `CAMP-002`, klik Tambah → chip kedua muncul
- Group by: `Jenis Program`
- Klik Bandingkan

**Proses:**
```
POST /api/campaigns/comparison
Body: { campaign_ids: ["CAMP-001", "CAMP-002"], group_by: "flag_program" }
```

**Output:**
- Tabel dengan 2 baris, semua 5 metrik terisi
- Grafik batang dengan 2 warna (navy = CAMP-001, biru = CAMP-002)

---

### Skenario 2: Mencoba Menambah Campaign ke-6

**Input:**
- 5 chip sudah ada di daftar
- User mengetik `CAMP-006` dan klik Tambah

**Output:**
- Pesan merah muncul: *"Maksimal 5 campaign dapat dipilih."*
- Input dinonaktifkan (disabled)
- Tombol Tambah juga dinonaktifkan

---

### Skenario 3: API Error

**Input:**
- 3 campaign dipilih, klik Bandingkan
- Backend mengembalikan error 500

**Output:**
- Tabel dan grafik tidak muncul
- Banner merah: *"Gagal memuat data: [pesan error]"*
- Pengguna bisa mengubah pilihan dan mencoba lagi

---

## Keterkaitan dengan Komponen Lain

- **Bergantung pada:**
  - `DashboardLayout` — wrapper layout aplikasi (header + sidebar)
  - `api.compareCampaigns()` — method service layer yang memanggil `POST /api/campaigns/comparison`
  - `CampaignComparisonRequest`, `CampaignMetric`, `CampaignComparisonResponse` — tipe dari `../types/api`
  - `react-chartjs-2` Bar + Chart.js — rendering grafik batang

- **Digunakan oleh:**
  - `App.tsx` — di-render pada route `/comparison`

- **Pengaruh ke:**
  - Tidak ada dependensi downstream langsung; ini adalah leaf component di frontend

---

## Requirements yang Dipenuhi

| Requirement | Deskripsi |
|-------------|-----------|
| 2.1 | Perbandingan 5 metrik per campaign (leads, take-up, rate, transaksi, durasi) |
| 2.2 | Visualisasi grafik batang berdampingan |
| 2.3 | Validasi seleksi 2–5 campaign |
| 2.4 | Group-by dropdown dengan sort ascending |
| 2.5 | Blokir seleksi ke-6 dengan pesan limit maksimal |

---

## Catatan Penting

- **Aksesibilitas:** Semua elemen interaktif memiliki `aria-label`, pesan error menggunakan `role="alert"` dengan `aria-live="polite"`, tabel memiliki `aria-label`
- **Keyboard navigation:** Menekan Enter di input otomatis memicu Tambah
- **Sorting:** Hasil dari API di-sort ascending berdasarkan `campaign_id` setelah diterima
- **Chart scaling:** Nilai Transaksi dibagi 1.000.000 di grafik (ditampilkan dalam Rp juta) agar skala tidak merusak metrik lain — catatan kaki ditampilkan di bawah grafik
- **No Tailwind:** Semua styling menggunakan inline style objects + satu file `.css` untuk keyframe animasi spinner
- **Spinner animation:** Keyframe `@keyframes spin` didefinisikan di `CampaignComparisonPage.css` dan juga di-inject inline via `<style>` tag untuk kompatibilitas saat CSS file mungkin belum dimuat
