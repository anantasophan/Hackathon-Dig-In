# Task UI 13 — Checkpoint: Verifikasi Semua Halaman

## Ringkasan Singkat

Task ini adalah checkpoint kualitas yang memverifikasi bahwa seluruh 6 halaman hasil refactor UI Redesign (CampaignOverviewPage, CampaignComparisonPage, TimeToTakeUpPage, RegionalPerformancePage, CustomerCriteriaPage, SimilarCampaignPage) berhasil dikompilasi tanpa TypeScript error melalui perintah `npm run build`. Selain itu, ditemukan dan diperbaiki satu isu baru: build gagal karena `@types/jest` belum tersedia, menyebabkan TypeScript tidak mengenali globals test seperti `describe`, `it`, dan `expect` saat type-checking semua file `src/`.

---

## Penjelasan Awam (Non-Technical)

**Analogi:** Bayangkan Anda baru saja merenovasi 6 ruangan di sebuah gedung bank — mengganti wallpaper lama dengan yang baru, mengganti poster emoji dengan plang profesional, dan merapikan semua kabel. Sebelum gedung dibuka untuk umum, ada seorang inspektor yang berkeliling memeriksa setiap ruangan untuk memastikan tidak ada yang rusak, tidak ada kabel terkelupas, dan semua plang terpasang benar.

Itulah yang dilakukan checkpoint ini: **inspektor digital** (TypeScript compiler + webpack) memeriksa semua 6 halaman sekaligus dan memastikan semuanya bisa "dibuka" tanpa masalah.

**Temuan dan perbaikan:** Inspektor menemukan bahwa gedung juga memiliki ruang laboratorium pengujian (test files) yang menggunakan peralatan khusus (`describe`, `expect`) — namun katalog peralatan lab itu (`@types/jest`) belum terdaftar. Solusinya: daftarkan katalog tersebut (`npm install --save-dev @types/jest@29.5.12`) sehingga inspektor tahu bahwa peralatan itu sah dan bukan barang asing.

**Manfaat bagi tim:** Setelah checkpoint ini, semua 6 halaman terbukti siap untuk dibuka ke pengguna — tidak ada komponen yang "patah" akibat proses refactor styling.

---

## Penjelasan Teknis

### Masalah yang Ditemukan

`npm run build` gagal dengan error:

```
TS2582: Cannot find name 'describe'. Do you need to install type definitions for a test runner?
Try `npm i --save-dev @types/jest` or `npm i --save-dev @types/mocha`.
  > 68 | describe('Property 7: Campaign chip has required Tailwind classes', () => {
```

**Root cause:** CRA 5.0.1 menggunakan TypeScript untuk type-checking seluruh `src/` (termasuk test files `.test.tsx`) selama `react-scripts build`. Walaupun test files tidak dimasukkan ke webpack bundle, TypeScript compiler tetap memvalidasi tipe-nya. Globals Jest (`describe`, `it`, `expect`) tidak dikenali karena `@types/jest` belum terinstal — CRA menyertakan Jest runtime secara internal, tapi tidak otomatis meng-expose `@types/jest` ke TypeScript compiler di scope build produksi.

### Solusi

Install `@types/jest@29.5.12` (versi yang kompatibel dengan `@testing-library/jest-dom@6.4.2` yang membutuhkan `@types/jest >= 28`):

```bash
npm install --save-dev @types/jest@29.5.12
```

Dicoba pertama dengan `@types/jest@27.5.2` → gagal (peer dependency conflict dengan `@testing-library/jest-dom@6.4.2` yang butuh `>= 28`).
Dicoba dengan `@types/jest@29.5.12` → berhasil.

### File yang Dimodifikasi

| File | Perubahan |
|------|-----------|
| `frontend/package.json` | Tambah `"@types/jest": "29.5.12"` ke `devDependencies` (pinned exact) |

### Hasil Build

```
Compiled successfully.

File sizes after gzip:
  167.69 kB  build/static/js/main.80820828.js
  4.2 kB     build/static/css/main.eb516b64.css
```

Build berhasil tanpa TypeScript error. Tidak ada CSS import warning.

### Mengapa `@types/jest` Belum Ada Sebelumnya

Pada awal spec, property tests diimplementasikan dengan asumsi bahwa `react-scripts test` (yang menyuntikkan Jest globals secara otomatis) sudah cukup. Namun `react-scripts build` menjalankan TypeScript compiler secara terpisah dari Jest runtime, sehingga `@types/jest` memang harus dideklarasikan secara eksplisit.

---

## Struktur Kode (yang Relevan)

### `frontend/package.json` — devDependencies setelah update

```json
"devDependencies": {
  "@testing-library/jest-dom": "^6.4.2",
  "@testing-library/react": "^14.2.2",
  "@testing-library/user-event": "^14.5.2",
  "@types/jest": "29.5.12",           // ← baru ditambahkan
  "@types/node": "16.18.96",
  "@types/react": "18.2.73",
  "@types/react-dom": "18.2.23",
  "autoprefixer": "10.4.19",
  "fast-check": "^3.19.0",
  "postcss": "8.4.38"
  // ...
}
```

---

## Simulasi / Skenario

### Skenario 1 — Build Gagal (Sebelum Fix)

**Konteks:** Developer menjalankan `npm run build` untuk deployment setelah menyelesaikan seluruh refactor halaman.

```
Input : npm run build
Proses: react-scripts → TypeScript compiler → menemukan describe() di CampaignChip.property.test.tsx
Output: TS2582: Cannot find name 'describe'. Exit Code: 1
```

Seluruh pipeline CI/CD terhenti. Build artifact tidak dihasilkan.

---

### Skenario 2 — Build Berhasil (Setelah Fix)

**Konteks:** Setelah `@types/jest@29.5.12` terinstal.

```
Input : npm run build
Proses: react-scripts → TypeScript compiler (mengenali describe/it/expect dari @types/jest)
        → webpack bundling 6 halaman + 3 shared components
        → Tailwind CSS purge (hanya utility classes yang digunakan)
Output: Compiled successfully.
        main.js: 167.69 kB (gzip)
        main.css:   4.20 kB (gzip)
        Exit Code: 0
```

Semua 6 halaman (CampaignOverview, CampaignComparison, TimeToTakeUp, RegionalPerformance, CustomerCriteria, SimilarCampaign) dikompilasi bersih.

---

### Skenario 3 — Pengecekan Kompatibilitas Peer Dependency

**Konteks:** Percobaan install `@types/jest@27.5.2` (versi lama).

```
Input : npm install --save-dev @types/jest@27.5.2
Output: npm error ERESOLVE could not resolve
        @testing-library/jest-dom@6.4.2 membutuhkan @types/jest >= 28
        → Gagal dengan peer dependency conflict
```

Solusi: gunakan `@types/jest@29.5.12` yang memenuhi semua peer deps.

---

## Keterkaitan dengan Komponen Lain

- **Bergantung pada:** Semua task 7.x–12.x (refactor halaman) dan task 14.1 (EmptyState/LoadingState/ErrorState), 15.1 (hapus CSS lama) — checkpoint ini memverifikasi semua output mereka
- **Digunakan oleh:** Task 16 (Final Checkpoint) — jika task 13 gagal, task 16 tidak akan dijalankan
- **Pengaruh ke:** Pipeline CI/CD dan deployment — `npm run build` adalah gate utama sebelum artefak diunggah ke S3/CDN

---

## Requirements yang Dipenuhi

Checkpoint ini tidak secara langsung mengimplementasikan requirement fungsional, namun memvalidasi bahwa semua requirement dari `requirements.md` yang telah diimplementasikan di task 7–15 berfungsi bersama:

- Requirement 5–10: Semua 6 halaman ter-refactor tanpa error TypeScript
- Requirement 13: CSS lama sudah dihapus (tidak ada import warning)
- Requirement 11: Shared components (EmptyState, LoadingState, ErrorState) terintegrasi benar

---

## Catatan Penting

- **Limitasi:** `npm run build` hanya memverifikasi kompilasi TypeScript + bundling, bukan runtime behavior. Untuk memverifikasi fungsionalitas aktual di browser, masih perlu `npm start` dan manual QA.
- **`@types/jest` vs CRA internal:** CRA 5 menyertakan Jest secara internal untuk `npm test`, namun `@types/jest` perlu di-declare eksplisit agar TypeScript compiler (yang dijalankan terpisah saat `build`) tidak error.
- **Versi pinned:** `@types/jest` di-pin ke `29.5.12` (exact, tanpa `^`) sesuai konvensi pinned versions di spec ini.
- **Todo:** Jalankan `npm test` secara terpisah untuk memverifikasi semua 10 property tests lulus secara runtime (membutuhkan environment browser/jsdom).
