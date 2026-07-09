# Task 11.6 — SimilarCampaignPage: Halaman Campaign Serupa

## Ringkasan Singkat

`SimilarCampaignPage` adalah halaman dashboard yang memungkinkan pengguna menemukan campaign bank yang memiliki karakteristik serupa dengan campaign tertentu. Pengguna memasukkan ID campaign referensi, memilih dimensi kesamaan (jenis program, channel, atau jenis leads), lalu sistem menampilkan hingga 20 campaign yang paling mirip. Halaman ini ditujukan untuk divisi bisnis yang ingin belajar dari campaign sukses sebelumnya.

---

## Penjelasan Awam (Non-Technical)

Bayangkan Anda ingin meniru keberhasilan sebuah kampanye promosi QRIS yang berjalan dengan baik. Daripada mencari secara manual dari ratusan kampanye yang pernah ada, halaman ini otomatis menemukan kampanye-kampanye lain yang "mirip" — misalnya yang menggunakan channel yang sama (WhatsApp), atau menyasar jenis nasabah yang serupa.

- **Fungsi utama**: Cari kampanye yang mirip berdasarkan dimensi tertentu
- **Analogi nyata**: Seperti fitur "film serupa" di Netflix, tapi untuk kampanye bank
- **Manfaat bisnis**: Divisi bisnis bisa belajar dari strategi kampanye terdahulu yang sukses, tanpa harus mengingat semua ID kampanye secara manual

---

## Penjelasan Teknis

### File yang Dibuat / Dimodifikasi

| File | Aksi |
|------|------|
| `frontend/src/pages/SimilarCampaignPage.tsx` | Dibuat baru |
| `frontend/src/pages/SimilarCampaignPage.css` | Dibuat baru |
| `frontend/src/App.tsx` | Dimodifikasi — ganti `PlaceholderPage` untuk `/similar-campaigns` |

### Library / Framework

- **React 18** — functional components + hooks (`useState`, `useCallback`)
- **TypeScript strict mode** — no implicit `any`, fully typed state
- **CSS plain** — tidak menggunakan Tailwind
- **api.ts** — memanggil `api.getSimilarCampaigns()` via POST `/api/campaigns/similar`

### Tipe yang Digunakan

```typescript
// Dari types/api.ts
SimilarCampaignRequest   // body POST: reference_campaign_id, dimensions, limit
SimilarCampaignResponse  // { similar_campaigns: SimilarCampaignResult[] }
SimilarCampaignResult    // per-campaign: id, name, matching_dimensions, scores, metrics

// Tipe lokal
interface LearningSum {
  take_up_rate_formatted: string;
  top_segment: string;
  top_region: string;
}
```

### Dimensi yang Valid

Tepat 3 nilai, sesuai `SIMILAR_CAMPAIGN_DIMENSIONS` di backend:
- `flag_program` — Jenis Program
- `media_blasting` — Channel  
- `jenis_leads` — Jenis Leads

### Arsitektur Komponen

```
SimilarCampaignPage         ← halaman utama
  ├─ DashboardLayout        ← layout shell (header + sidebar)
  ├─ form-card              ← input referensi + checkbox dimensi
  ├─ sc-learning-summary    ← kotak ringkasan (opsional, dari API)
  ├─ sc-results-layout      ← grid 2-kolom (list | detail)
  │   ├─ CampaignCard[]     ← kartu hasil, clickable
  │   └─ ComparisonView     ← panel detail side-by-side (saat ada yang dipilih)
  └─ state boxes            ← loading / error / empty / idle
```

### Keputusan Desain Penting

1. **Toggling selection**: Mengklik kartu yang sudah terpilih akan deselect (menghapus panel detail). Ini memungkinkan pengguna menutup panel tanpa elemen UI tambahan.
2. **Sticky detail pane**: Panel detail menggunakan `position: sticky` agar tetap terlihat saat list di-scroll.
3. **Responsive grid**: Menggunakan CSS `grid-template-columns` dengan media query 900px. Di bawah 900px tampil 1 kolom, di atas tampil 2 kolom (list + detail).
4. **`has()` selector** untuk grid: Kolom kedua hanya muncul ketika `.sc-detail-pane` ada di DOM (artinya campaign sudah dipilih).
5. **`learning_summary` opsional**: Tipe response di-extend secara lokal (`SimilarCampaignResponse & { learning_summary?: LearningSum }`) karena field ini tidak ada di interface API utama.

---

## Struktur Kode

### Komponen Utama

| Fungsi/Komponen | Deskripsi |
|----------------|-----------|
| `SimilarCampaignPage` | Komponen halaman utama, mengelola semua state |
| `CampaignCard` | Kartu hasil campaign (clickable, menampilkan 4 metrik + badges) |
| `ComparisonView` | Panel detail 4 seksi saat campaign dipilih |
| `handleDimensionChange` | Toggle checkbox dimensi (tambah/hapus dari array) |
| `handleSearch` | Panggil API dan update state |
| `handleSelectCampaign` | Toggle selected campaign (deselect jika sama) |
| `fmtPct` / `fmtScore` / `fmtNum` / `fmtCurrency` | Helper format angka |

### State

```typescript
referenceId: string                                 // ID campaign referensi
dimensions: Array<'media_blasting' | 'jenis_leads' | 'flag_program'>
data: SimilarCampaignData | null                    // response API
selectedCampaign: SimilarCampaignResult | null      // kartu yang sedang dipilih
loading: boolean
error: string | null
```

---

## Simulasi / Skenario

### Skenario 1: Happy Path — Menemukan Campaign Serupa

**Input:**
- Campaign ID Referensi: `PROG-QRIS-2024-01`
- Dimensi: `flag_program`, `media_blasting`

**Proses:**
1. User klik "Cari Campaign Serupa"
2. API dipanggil: `POST /api/campaigns/similar` dengan body `{ reference_campaign_id: "PROG-QRIS-2024-01", dimensions: ["flag_program", "media_blasting"], limit: 20 }`
3. API mengembalikan 15 campaign, diurutkan berdasarkan `dimension_count` DESC

**Output:**
```
Ditemukan 15 campaign serupa (diurutkan berdasarkan jumlah dimensi yang cocok)

[Kartu 1] Program QRIS Nasabah Baru Q3
         PROG-QRIS-2024-07
         Dimensi Cocok: 2 | Skor: 100.0% | Take-Up Rate: 18.45% | Total Leads: 5.240
         Badges: [flag_program] [media_blasting]
```

### Skenario 2: Memilih Kartu untuk Detail

**Input:** User klik kartu "Program QRIS Nasabah Baru Q3"

**Output (panel detail di sebelah kanan):**
```
Detail Campaign: Program QRIS Nasabah Baru Q3

📊 Metrik Utama
  Total Leads:     5.240
  Total Take Up:   967
  Take-Up Rate:    18,45%
  Nilai Transaksi: Rp 4.835.000.000

🔗 Dimensi yang Cocok
  [flag_program] [media_blasting]

📐 Skor Kesamaan
  Jumlah Dimensi Cocok: 2
  Skor Kesamaan:        100,0%

ℹ️ Data Lanjutan
  Data detail segmen/regional/waktu memerlukan query lanjutan ke Athena (post-MVP)
```

### Skenario 3: Tidak Ada Campaign Serupa

**Input:** Campaign ID yang tidak memiliki padanan

**Output:**
```
🔍 Tidak Ditemukan
Tidak ada campaign serupa ditemukan. Coba perluas dimensi pencarian.
```

---

## Keterkaitan dengan Komponen Lain

- **Bergantung pada:**
  - `DashboardLayout` — layout shell halaman
  - `api.getSimilarCampaigns()` — service layer Axios
  - `types/api.ts` → `SimilarCampaignRequest`, `SimilarCampaignResponse`, `SimilarCampaignResult`
  - `useAuth` hook — mengambil username + signOut untuk header

- **Digunakan oleh:**
  - `App.tsx` — di-render pada route `/similar-campaigns`

- **Pengaruh ke:**
  - Jika `SimilarCampaignResult` di `types/api.ts` diubah (tambah field), `ComparisonView` perlu diperbarui untuk menampilkan field baru

---

## Requirements yang Dipenuhi

| Requirement | Deskripsi |
|-------------|-----------|
| 6.1 | Reference campaign selector (input ID + tombol) |
| 6.2 | Dimension filter checkboxes (3 dimensi valid) |
| 6.3 | Similar campaign list (maks 20, sorted by dimension_count DESC) |
| 6.4 | Side-by-side comparison view (4 seksi) |
| 6.5 | Learning summary display + empty state messaging |

---

## Catatan Penting

1. **`learning_summary` tidak ada di interface API resmi** — field ini di-extend secara lokal. Jika backend mulai mengembalikannya secara konsisten, pertimbangkan untuk menambahkan ke `SimilarCampaignResponse` di `types/api.ts`.
2. **`total_transaction_value` tidak ada di `SimilarCampaignResult`** — ditampilkan dengan type cast aman; akan menampilkan `—` jika tidak ada.
3. **`has()` CSS selector** digunakan untuk responsive grid — didukung semua browser modern (Chrome 105+, Firefox 121+, Safari 15.4+). Jika perlu support browser lama, ganti dengan state-based class.
4. **Dimensi minimal 1** — tombol "Cari" akan disabled jika tidak ada dimensi yang dipilih (`canSearch` check).
5. **Post-MVP note** di section 4 ComparisonView adalah placeholder eksplisit — data segmen/regional/waktu belum tersedia dari API.
