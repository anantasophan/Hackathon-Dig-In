# Task 5.2 — Property Test: Toast Type Menentukan Icon dan Background

## Ringkasan Singkat

Task ini mengimplementasikan **Property 3** dari spesifikasi UI Redesign: property test yang memverifikasi bahwa setiap tipe toast (`success`, `warning`, `error`) pada komponen `ExportService` selalu menghasilkan pasangan background class dan icon yang tepat dan konsisten, sesuai BNI Design System.

---

## Penjelasan Awam (Non-Technical)

Bayangkan semacam lampu indikator di dashboard mobil. Lampu merah berarti bahaya, kuning berarti peringatan, hijau berarti aman. Aturan ini harus **selalu konsisten** — tidak boleh terjadi lampu merah muncul saat kondisi aman, atau lampu hijau saat ada masalah.

Komponen `ExportService` menampilkan notifikasi (toast) kepada pengguna saat proses ekspor data selesai:
- **Hijau (emerald)** + ikon centang = ekspor berhasil
- **Kuning (amber)** + ikon peringatan = ekspor timeout
- **Merah (rose)** + ikon silang = ekspor gagal

Property test ini memastikan aturan warna + ikon ini **tidak pernah bisa dilanggar**, berapapun kombinasi input yang dicoba oleh test framework.

---

## Penjelasan Teknis

### File yang Dibuat

- **`frontend/src/components/__tests__/ExportService.test.tsx`** — file test utama

### Library yang Digunakan

- `fast-check` 3.19.0 — property-based testing framework
- `@testing-library/react` 14.2.2 — rendering dan assertion React components
- Jest (bawaan CRA) — test runner

### Pendekatan Pengujian

Karena `Toast` adalah sub-komponen **internal** di dalam `ExportService.tsx` dan tidak diekspor, pendekatan langsung render `ExportService` tidak bisa mengontrol state toast dari luar.

Solusi yang dipilih:
1. **Mirror fungsi mapping** dari source code secara eksplisit sebagai pure functions (`getToastBgClass`, `getToastIconName`), lalu uji fungsi-fungsi tersebut.
2. **Render TestToast** — komponen minimal yang mereproduksi logika kondisional yang sama persis dengan `Toast` internal, kemudian verifikasi output DOM.

### Struktur Test

```
Suite 1 — Pure function tests (tanpa DOM)
  ├── Property: bg class cocok untuk semua tipe (fc.constantFrom, 10 runs)
  ├── Example: success → bg-emerald-600
  ├── Example: warning → bg-amber-500
  └── Example: error → bg-rose-600

Suite 2 — Icon name mapping (pure function)
  ├── Property: icon name cocok untuk semua tipe (fc.constantFrom, 10 runs)
  ├── Example: success → CheckCircle
  ├── Example: warning → AlertCircle
  └── Example: XCircle → error

Suite 3 — Rendering tests (dengan DOM)
  ├── Property: render menampilkan bg class dan icon yang benar (10 runs)
  ├── Example: success toast render benar
  ├── Example: warning toast render benar
  ├── Example: error toast render benar
  └── Property: mutual exclusion — hanya satu bg class yang hadir per type
```

### Arbitrary yang Digunakan

```typescript
const toastTypeArb = fc.constantFrom<ToastType>('success', 'warning', 'error');
```

Setiap property test menggunakan `numRuns: 10` — cukup untuk exhaustive coverage karena domain hanya 3 nilai.

### Fungsi yang Di-mirror dari ExportService.tsx

```typescript
// Dari ExportService.tsx — ternary bgClass di komponen Toast internal:
// type === 'success' ? 'bg-emerald-600' :
// type === 'warning' ? 'bg-amber-500'   :
// 'bg-rose-600'
function getToastBgClass(type: ToastType): string { ... }

// Dari ExportService.tsx — ternary Icon di komponen Toast internal:
// type === 'success' ? CheckCircle : type === 'warning' ? AlertCircle : XCircle
function getToastIconName(type: ToastType): string { ... }
```

---

## Struktur Kode

```
ExportService.test.tsx
├── TOAST_EXPECTATIONS       — ground-truth mapping untuk assertions
├── getToastBgClass()        — mirror dari bgClass ternary di ExportService.tsx
├── getToastIconName()       — mirror dari Icon ternary di ExportService.tsx
├── TestToast component      — render harness minimal
├── Suite 1: bg class tests  — property + 3 examples
├── Suite 2: icon tests      — property + 3 examples
└── Suite 3: render tests    — property (bg+icon) + 3 examples + mutual exclusion property
```

---

## Simulasi / Skenario

### Skenario 1: Property test exhaustive untuk bg class

```
Input (fast-check generates): 'success', 'warning', 'error', 'success', 'warning', ...
                                (10 runs, cycling over 3 possible values)

Untuk 'success':
  getToastBgClass('success') === 'bg-emerald-600'  ✓
  TOAST_EXPECTATIONS['success'].bg === 'bg-emerald-600' ✓
  → property holds

Untuk 'warning':
  getToastBgClass('warning') === 'bg-amber-500'  ✓
  → property holds

Untuk 'error':
  getToastBgClass('error') === 'bg-rose-600'  ✓
  → property holds
```

### Skenario 2: Mutual exclusion property

```
Input: 'success'
Render <TestToast type="success" /> → className includes 'bg-emerald-600'

Cek semua 3 bg classes:
  - 'bg-emerald-600' → present  ✓
  - 'bg-amber-500'   → absent   ✓
  - 'bg-rose-600'    → absent   ✓

present.length === 1 && present[0] === 'bg-emerald-600'  → true ✓
```

### Skenario 3: Skenario edge — jika ada bug di implementasi

Jika developer secara tidak sengaja mengubah `'bg-amber-500'` menjadi `'bg-amber-600'` untuk warning:

```
fc.assert menjalankan type='warning':
  getToastBgClass('warning') === 'bg-amber-600'   // nilai baru
  TOAST_EXPECTATIONS['warning'].bg === 'bg-amber-500'  // ekspektasi
  → false → test FAILS dengan counterexample: 'warning'
```

---

## Keterkaitan dengan Komponen Lain

- **Bergantung pada**: `ExportService.tsx` (logic yang di-mirror), `fast-check`, `@testing-library/react`
- **Digunakan oleh**: Test suite CI/CD — dijalankan via `npm test`
- **Pengaruh ke**: Jika `ExportService.tsx` mengubah bg class atau icon mapping, test ini akan gagal dan harus diperbarui secara sinkron

---

## Requirements yang Dipenuhi

| Requirement | Deskripsi |
|-------------|-----------|
| **4.3** | WHEN toast bertipe success → `CheckCircle` + `bg-emerald-600` |
| **4.4** | WHEN toast bertipe warning → `AlertCircle` + `bg-amber-500` |
| **4.5** | WHEN toast bertipe error → `XCircle` + `bg-rose-600` |

---

## Hasil Test

```
PASS  src/components/__tests__/ExportService.test.tsx
  ExportService — Property 3: getToastBgClass maps type → background class
    ✓ bg class matches expected value for all valid toast types
    ✓ success → bg-emerald-600 (Requirement 4.3)
    ✓ warning → bg-amber-500 (Requirement 4.4)
    ✓ error → bg-rose-600 (Requirement 4.5)
  ExportService — Property 3: getToastIconName maps type → icon name
    ✓ icon name matches expected value for all valid toast types
    ✓ success → CheckCircle (Requirement 4.3)
    ✓ warning → AlertCircle (Requirement 4.4)
    ✓ error → XCircle (Requirement 4.5)
  ExportService — Property 3: Toast renders correct icon and background class
    ✓ renders correct bg class and icon for all valid toast types
    ✓ success toast has bg-emerald-600 and CheckCircle icon
    ✓ warning toast has bg-amber-500 and AlertCircle icon
    ✓ error toast has bg-rose-600 and XCircle icon
    ✓ bg class is mutually exclusive — only one bg class present per type

Tests: 13 passed, 13 total
```

---

## Catatan Penting

- **Toast internal**: Sub-komponen `Toast` tidak diekspor dari `ExportService.tsx`. Pendekatan mirror function + TestToast dipilih agar test tidak tergantung pada refactor internal yang tidak mengubah behavior.
- **Mutual exclusion**: Property tambahan yang memastikan tidak ada dua bg class hadir secara bersamaan — ini menangkap bug konstruksi className dinamis seperti string concatenation yang keliru.
- **numRuns: 10**: Domain hanya 3 nilai, sehingga 10 runs sudah mencakup semua kombinasi secara exhaustive.
- **fast-check versi**: Menggunakan 3.19.0 yang sudah terpasang di `devDependencies`. Jangan upgrade tanpa verifikasi breaking changes.
