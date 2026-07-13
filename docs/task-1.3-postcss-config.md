# Task 1.3 (UI Redesign) — PostCSS Config untuk CRA Pipeline

## Ringkasan Singkat

File `frontend/postcss.config.js` mengkonfigurasi PostCSS pipeline untuk Create React App agar Tailwind CSS dapat memproses file CSS secara otomatis setiap kali project di-build atau di-run. File ini adalah jembatan antara Tailwind CSS dan sistem build CRA yang sudah ada.

## Penjelasan Awam (Non-Technical)

Bayangkan Tailwind CSS seperti sebuah mesin cetak kain dengan ribuan pola warna dan ukuran yang siap digunakan. Namun mesin ini perlu "dihubungkan ke jalur listrik" agar bisa bekerja otomatis setiap kali kita menjahit baju (membangun aplikasi).

File `postcss.config.js` adalah **kabel penghubung** itu. Ia memberitahu alat build CRA:
1. "Pertama, proses semua utility class Tailwind CSS dari kode saya"
2. "Lalu, tambahkan prefix otomatis agar semua browser bisa membacanya"

Tanpa file ini, class seperti `bg-[#005E6A]` atau `text-xs` tidak akan menghasilkan CSS apapun — seolah lampu dipasang tanpa disambungkan ke sakelar.

## Penjelasan Teknis

### File yang Dibuat

- **`frontend/postcss.config.js`** — konfigurasi PostCSS root-level yang dibaca oleh `postcss-loader` milik CRA

### Cara Kerja

Create React App 5.x sudah menyertakan `postcss-loader` di dalam webpack config bawaan. `postcss-loader` secara otomatis mencari file `postcss.config.js` di root project. Tidak perlu `craco`, `react-app-rewired`, atau ejecting.

**Urutan plugin yang dikonfigurasi:**

```js
module.exports = {
  plugins: {
    tailwindcss: {},   // 1. Generate utility classes dari @tailwind directives
    autoprefixer: {},  // 2. Tambahkan vendor prefix (e.g., -webkit-, -moz-)
  },
};
```

**Mengapa urutan ini penting:**
- `tailwindcss` harus berjalan **pertama** karena ia mengubah `@tailwind base/components/utilities` menjadi CSS nyata
- `autoprefixer` harus berjalan **setelah** tailwindcss agar ia bisa memproses CSS yang sudah di-generate, bukan direktif mentah

### PostCSS Pipeline Flow

```
src/index.css (@tailwind directives)
    → PostCSS reads postcss.config.js
    → tailwindcss plugin: scan content paths → generate utility classes
    → autoprefixer plugin: tambah vendor prefixes
    → CRA webpack bundle: inject CSS ke dalam aplikasi
```

### Dependency

Plugin ini bergantung pada package yang sudah dipinned di `package.json` (Task 1.1):
- `tailwindcss: "3.4.1"` (dependency)
- `autoprefixer: "10.4.19"` (devDependency)

## Struktur Kode

```js
module.exports = {
  plugins: {
    tailwindcss: {},   // Opsi kosong = gunakan tailwind.config.js dari root
    autoprefixer: {},  // Opsi kosong = autoprefixer default (browserslist dari package.json)
  },
};
```

Kedua plugin menggunakan opsi kosong `{}` karena konfigurasi masing-masing sudah diatur di file terpisah:
- `tailwindcss` → baca `tailwind.config.js`
- `autoprefixer` → baca `browserslist` dari `package.json` atau `.browserslistrc`

## Simulasi / Skenario

### Skenario 1: Build Normal

```
Input:  src/index.css berisi "@tailwind utilities"
Proses: tailwindcss scan ./src/**/*.{ts,tsx} → generate .bg-white, .text-xs, dll
        autoprefixer tambah -webkit-flex untuk Safari compatibility
Output: CSS bundle lengkap di build/static/css/main.*.css
```

### Skenario 2: Class Kustom BNI

```tsx
// Di CampaignOverviewPage.tsx:
<div className="bg-[#005E6A] text-white rounded-xl">
```

```
Proses: tailwindcss deteksi class → generate CSS:
        .bg-\[\#005E6A\] { background-color: #005E6A; }
        autoprefixer: tidak ada prefix yang dibutuhkan untuk background-color
Output: CSS class tersedia di browser
```

### Skenario 3: Jika File Tidak Ada

```
Error: CRA build akan mengabaikan Tailwind → semua @tailwind directives
       di index.css tidak menghasilkan CSS
       Seluruh UI akan kehilangan styling Tailwind
```

## Keterkaitan dengan Komponen Lain

- **Bergantung pada:**
  - `frontend/tailwind.config.js` (Task 1.2) — tailwindcss plugin membaca config ini
  - `package.json` (Task 1.1) — tailwindcss dan autoprefixer harus sudah terinstall
- **Digunakan oleh:**
  - CRA webpack pipeline secara otomatis
  - `frontend/src/index.css` (Task 1.4) — @tailwind directives diproses melalui pipeline ini
- **Pengaruh ke:**
  - Seluruh komponen frontend yang menggunakan Tailwind utility classes
  - Jika file ini dihapus atau salah, seluruh styling Tailwind akan gagal

## Requirements yang Dipenuhi

- **Requirement 1.1** — Frontend Project dapat menggunakan Tailwind CSS sebagai PostCSS plugin dalam CRA pipeline

## Catatan Penting

- File ini harus berada di **root** folder `frontend/` (sejajar dengan `package.json`), bukan di dalam `src/`
- Urutan plugin **tailwindcss → autoprefixer** bersifat wajib; membalik urutan menyebabkan autoprefixer memproses direktif `@tailwind` yang belum dikonversi
- Flag `-p` pada `npx tailwindcss init -p` akan menghasilkan file ini secara otomatis (sudah dilakukan di Task 1.2)
- Konfigurasi ini kompatibel dengan CRA 5.x tanpa perlu ejecting atau menggunakan craco
