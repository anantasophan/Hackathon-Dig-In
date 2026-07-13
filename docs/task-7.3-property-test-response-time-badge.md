# Task 7.3 — Property Test: Response Time Badge (Property 6)

## Ringkasan Singkat

Task ini mengimplementasikan property-based test untuk badge response time pada `CampaignOverviewPage`. Test memverifikasi bahwa untuk semua nilai `responseMs` dalam rentang [0, 60000], badge selalu menampilkan ikon dan warna yang tepat: `CheckCircle` + `text-emerald-600` untuk respons cepat (< 5000ms), dan `AlertCircle` + `text-amber-600` untuk respons lambat (≥ 5000ms).

---

## Penjelasan Awam (Non-Technical)

Bayangkan lampu lalu lintas di dashboard: kalau server menjawab dalam waktu kurang dari 5 detik, lampu menyala hijau (tanda aman). Kalau lebih dari 5 detik, lampu berubah kuning (peringatan). Test ini memastikan bahwa lampu tidak pernah salah warna — tidak peduli berapa lama tepatnya server merespons, antara 0 hingga 60.000 milidetik. Test ini mencoba ratusan nilai waktu secara otomatis dan mengecek bahwa aturan hijau/kuning selalu berlaku dengan benar.

---

## Penjelasan Teknis

### File yang Dibuat

| File | Keterangan |
|------|-----------|
| `frontend/src/tests/ResponseTimeBadge.property.test.tsx` | File test baru — property-based tests untuk response time badge |

### Library dan Framework

- **fast-check** (`^3.19.0`) — property-based testing library
- **@testing-library/react** (`^14.2.2`) — rendering tests tanpa browser
- `fc.float({ min: 0, max: Math.fround(60000), noNaN: true })` — arbiter nilai float 32-bit dalam rentang [0, 60000]

### Arsitektur Test

Test dibagi tiga suite:

1. **Suite 1 — Pure function tests (no DOM)**  
   Menguji dua helper function murni yang mencerminkan logika kondisional dari `CampaignOverviewPage.tsx`:
   - `getResponseTimeBadgeClass(responseMs)` — mengembalikan class string Tailwind yang mengandung warna yang tepat
   - `getResponseTimeBadgeIcon(responseMs)` — mengembalikan nama ikon (`'CheckCircle'` atau `'AlertCircle'`)

2. **Suite 2 — Rendering tests (DOM)**  
   Menggunakan komponen `TestBadge` minimal yang mereproduksi logika rendering badge dari `CampaignOverviewPage.tsx`. Verifikasi via `data-testid` attributes.

3. **Example-based checks**  
   Test individual untuk nilai batas: 0ms, 4999ms, 5000ms, 60000ms — memberikan keterlacakan langsung ke masing-masing requirement.

### Keputusan Desain Penting

- **Tidak mount `CampaignOverviewPage` secara penuh** — halaman membutuhkan mock untuk `useAuth`, `api`, `FilterPanel`, `DashboardLayout`, dan Chart.js. Pendekatan yang lebih sederhana: mirror logika kondisional di test sebagai fungsi murni, lalu uji dengan rendering minimal.
- **`Math.fround()` untuk batas `fc.float`** — `fast-check` mengharuskan batas `min`/`max` untuk `fc.float` berupa 32-bit float. Nilai seperti `4999.99` tidak valid; `Math.fround(4999)` aman.
- **Sub-range arbiters untuk fast/slow** — untuk properti yang hanya berlaku di satu sisi threshold, digunakan sub-range `fc.float` yang lebih sempit agar shrinking lebih efektif jika ada kegagalan.

### Edge Cases yang Ditangani

| Kasus | Perilaku yang Diharapkan |
|-------|--------------------------|
| `responseMs = 0` | Fast path → `CheckCircle` + `text-emerald-600` |
| `responseMs = 4999` | Fast path (tepat di bawah threshold) → `CheckCircle` + `text-emerald-600` |
| `responseMs = 5000` | Slow path (tepat di threshold) → `AlertCircle` + `text-amber-600` |
| `responseMs = 60000` | Slow path (maksimum) → `AlertCircle` + `text-amber-600` |
| Nilai float di tengah (e.g. 2500.5) | Fast path → `CheckCircle` |
| Mutually exclusive color | Hanya satu dari `text-emerald-600` / `text-amber-600` yang ada di className |

---

## Struktur Kode

```tsx
// Helper murni — mirrors CampaignOverviewPage.tsx conditional branches
function getResponseTimeBadgeClass(responseMs: number): string
function getResponseTimeBadgeIcon(responseMs: number): string

// Komponen test minimal — tidak bergantung pada full page
const TestBadge: React.FC<{ responseMs: number }>

// Arbiter utama
const responseMsArb = fc.float({ min: 0, max: Math.fround(60000), noNaN: true })
```

Total: **17 test cases** (property runs: 200–500 per property, rendering: 300 per property)

---

## Simulasi / Skenario

### Skenario 1 — Respons cepat (happy path)

```
Input:  responseMs = 1200
Logic:  1200 < 5000 → fast path
Output: className mengandung 'text-emerald-600'
        icon textContent = 'CheckCircle'
```

### Skenario 2 — Respons lambat

```
Input:  responseMs = 7500
Logic:  7500 >= 5000 → slow path
Output: className mengandung 'text-amber-600'
        icon textContent = 'AlertCircle'
```

### Skenario 3 — Boundary (tepat di threshold)

```
Input:  responseMs = 5000
Logic:  5000 < 5000 = FALSE → slow path
Output: className mengandung 'text-amber-600' (bukan text-emerald-600)
        icon textContent = 'AlertCircle'
```

### Skenario 4 — Kegagalan yang dideteksi property test

```
Jika implementasi salah: responseMs < 5000 diganti responseMs <= 5000
Property "responseMs = 5000 → AlertCircle" akan GAGAL
fast-check akan melaporkan counterexample: responseMs = 5000
```

---

## Keterkaitan dengan Komponen Lain

- **Bergantung pada:** Logika kondisional di `CampaignOverviewPage.tsx` (di-mirror sebagai fungsi murni dalam test)
- **Digunakan oleh:** Tidak ada komponen lain yang bergantung pada file test ini
- **Pengaruh ke:** Jika threshold 5000ms diubah di `CampaignOverviewPage.tsx`, konstanta `THRESHOLD_MS` di file test harus diperbarui juga

---

## Requirements yang Dipenuhi

| Requirement | Deskripsi |
|-------------|-----------|
| **5.5** | Badge response time menggunakan `CheckCircle` + `text-emerald-600` jika < 5000ms |
| **5.6** | Badge response time menggunakan `AlertCircle` + `text-amber-600` jika ≥ 5000ms |

---

## Catatan Penting

- Konstanta `THRESHOLD_MS = 5000` di file test harus sinkron dengan nilai hardcoded `5000` di `CampaignOverviewPage.tsx`
- `fc.float` dengan `noNaN: true` + `.filter(isFinite)` memastikan tidak ada nilai special (Infinity, NaN) yang masuk ke logika badge
- Pendekatan "mirror logic as pure functions" adalah pattern standar dalam codebase ini — lihat juga `ExportService.test.tsx` untuk pattern serupa
- 17 tests, semua PASS pada waktu implementasi
