# Task UI 15.1 — Penghapusan 9 File CSS Lama

## Ringkasan Singkat

Task ini menghapus sembilan file CSS komponen lama yang sudah tidak diperlukan karena seluruh styling telah dipindahkan ke Tailwind CSS utility classes. Penghapusan dilakukan setelah semua komponen dan halaman berhasil di-refactor, memastikan tidak ada lagi kode styling duplikat atau konflik antara CSS lama dan Tailwind.

---

## Penjelasan Awam (Non-Technical)

Bayangkan sebuah kantor yang sedang dirapikan. Sebelumnya, setiap meja karyawan punya lembar instruksi kerja sendiri-sendiri yang berbeda-beda formatnya. Setelah perusahaan membuat panduan baku yang berlaku untuk semua karyawan, lembar-lembar instruksi lama itu tidak diperlukan lagi — bahkan bisa menimbulkan kebingungan jika masih ada.

File CSS lama itu ibarat lembar instruksi per-meja tadi. Setelah seluruh tampilan aplikasi menggunakan sistem desain BNI yang terpusat (Tailwind CSS), file-file CSS lama tersebut hanya memakan tempat dan berpotensi menyebabkan konflik visual. Task ini "membuang" kesembilan lembar instruksi lama tersebut agar sistem berjalan bersih tanpa ambiguitas.

Manfaat bagi pengguna bisnis: tampilan aplikasi menjadi konsisten, tidak ada "kebocoran" gaya lama yang mungkin muncul di browser tertentu.

---

## Penjelasan Teknis

### File yang Dihapus

| File | Lokasi |
|------|--------|
| `DashboardLayout.css` | `frontend/src/components/` |
| `FilterPanel.css` | `frontend/src/components/` |
| `ExportService.css` | `frontend/src/components/` |
| `CampaignOverviewPage.css` | `frontend/src/pages/` |
| `CampaignComparisonPage.css` | `frontend/src/pages/` |
| `TimeToTakeUpPage.css` | `frontend/src/pages/` |
| `RegionalPerformancePage.css` | `frontend/src/pages/` |
| `CustomerCriteriaPage.css` | `frontend/src/pages/` |
| `SimilarCampaignPage.css` | `frontend/src/pages/` |

### Verifikasi Import

Sebelum penghapusan, dilakukan grep search pada semua file `.tsx` untuk memastikan tidak ada lagi import yang mengarah ke file CSS yang akan dihapus:

```
Pola: import.*(?:DashboardLayout|FilterPanel|ExportService|CampaignOverview|...Page)\.css
Hasil: No matches found
```

Konfirmasi ini penting — jika masih ada import yang tertinggal, build akan gagal dengan error `Cannot find module 'X.css'`.

### File CSS yang Tetap Dipertahankan

Dua file CSS global **tidak** dihapus karena masih diperlukan:

- `frontend/src/index.css` — berisi Tailwind directives (`@tailwind base/components/utilities`), Google Fonts import Inter, dan custom classes (`.bni-teal`, `.table-fixed-header th`, `.truncate-2-lines`)
- `frontend/src/App.css` — file global yang diimpor di `App.tsx`, bukan termasuk daftar penghapusan

### Import CSS yang Valid (Dibiarkan)

Hasil grep menunjukkan tiga import CSS yang sah dan tidak disentuh:

```tsx
// App.tsx — global stylesheet, valid
import './App.css';

// index.tsx — Tailwind entry point, valid
import './index.css';

// LoginPage.tsx — Amplify UI library, valid (third-party)
import '@aws-amplify/ui-react/styles.css';
```

---

## Struktur Kode (Tidak Ada)

Task ini murni penghapusan file — tidak ada kode baru yang ditulis. Seluruh logika styling sudah ada di file `.tsx` masing-masing sebagai Tailwind utility classes.

---

## Simulasi / Skenario

### Skenario 1 — Penghapusan Berhasil (Happy Path)

**Kondisi awal:**
- 9 file CSS ada di filesystem
- Semua file `.tsx` sudah tidak mengimpor file CSS tersebut (hasil refactor sebelumnya)

**Proses:**
1. Grep scan → `No matches found` → aman untuk hapus
2. Delete 9 file → semua berhasil
3. Verifikasi akhir grep → masih `No matches found`

**Hasil:**
- `frontend/src/components/` hanya berisi `.tsx` files + `__tests__/` + `.gitkeep`
- `frontend/src/pages/` hanya berisi `.tsx` files + `.gitkeep`
- Build akan berjalan tanpa warning "module not found"

### Skenario 2 — Jika Ada Import Tertinggal (Error Case)

**Kondisi:** Misalnya `RegionalPerformancePage.tsx` masih mengandung `import './RegionalPerformancePage.css'` yang terlewat saat refactor.

**Dampak jika CSS dihapus tanpa cek:**
```
ERROR in ./src/pages/RegionalPerformancePage.tsx
Module not found: Error: Can't resolve './RegionalPerformancePage.css'
```

**Pencegahan:** Grep scan wajib dilakukan sebelum penghapusan. Jika ada match ditemukan, import tersebut harus dihapus terlebih dahulu dari file `.tsx`-nya.

---

## Keterkaitan dengan Komponen Lain

**Bergantung pada:**
- Task 3.1 (DashboardLayout Tailwind rewrite) — CSS import sudah dihapus dari `.tsx`
- Task 4.1 (FilterPanel Tailwind rewrite)
- Task 5.1 (ExportService Tailwind rewrite)
- Task 7.1–12.1 (semua 6 halaman Tailwind rewrite)

**Digunakan oleh:**
- Task 16 (Final Checkpoint) — konfirmasi tidak ada file CSS yang masih diimpor dalam `src/`
- CI/CD build pipeline — `npm run build` akan berjalan lebih bersih tanpa file CSS lama yang berpotensi di-bundle

**Pengaruh ke:**
- Bundle size: sedikit lebih kecil karena tidak ada CSS komponen lama yang ikut diproses PostCSS
- Developer experience: tidak ada kebingungan "mana yang aktif, CSS lama atau Tailwind?"

---

## Requirements yang Dipenuhi

| Requirement | Deskripsi |
|-------------|-----------|
| 13.1 | Tidak ada import `DashboardLayout.css` di codebase |
| 13.2 | Tidak ada import `FilterPanel.css` di codebase |
| 13.3 | Tidak ada import `ExportService.css` di codebase |
| 13.4 | Tidak ada import file CSS halaman di codebase |
| 13.5 | Jika file CSS lama masih ada di filesystem, tidak ada komponen yang mereferensikannya (kondisi ini kini tidak relevan karena file sudah dihapus) |

---

## Catatan Penting

- **Tidak reversible tanpa Git:** File yang dihapus tidak bisa dikembalikan kecuali via `git restore` atau `git checkout`. Pastikan semua refactor sudah selesai sebelum menjalankan task ini.
- **Urutan wajib:** Task ini harus dijalankan **setelah** semua task refactor halaman (7.1–12.1) dan shared components (3.1, 4.1, 5.1) selesai — bukan sebelumnya.
- **index.css dan App.css tidak dihapus** — keduanya bukan CSS komponen lama, melainkan entry point global yang masih dibutuhkan Tailwind.
- **Todo:** Jalankan `npm run build` setelah penghapusan (Task 16) untuk konfirmasi final bahwa tidak ada error akibat penghapusan ini.
