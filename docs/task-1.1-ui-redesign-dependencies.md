# Task 1.1 — Update `frontend/package.json` dengan Versi Dependensi yang Dipinned

## Ringkasan Singkat
Task ini menambahkan dependensi Tailwind CSS dan Lucide React ke file konfigurasi project frontend (`frontend/package.json`). Keempat paket ditambahkan dengan versi yang di-_pin_ (tidak menggunakan `^` atau `~`) agar build tetap deterministik dan tidak terdampak pembaruan otomatis.

## Penjelasan Awam (Non-Technical)
Bayangkan sebuah resep masakan yang menyebutkan bahan-bahan beserta takarannya. `package.json` adalah "daftar belanja" project frontend — ia mendaftar semua library (alat) yang dibutuhkan aplikasi beserta versi spesifiknya.

Task ini menambahkan dua "alat baru" ke daftar belanja:
- **Tailwind CSS** — alat untuk mempercantik tampilan aplikasi dengan cara yang cepat dan konsisten, menggunakan class-class siap pakai seperti `bg-blue-500` atau `text-center`.
- **Lucide React** — kumpulan ikon SVG profesional (seperti tanda panah, lonceng, kunci, dll) yang menggantikan emoji 🎉 ✅ ⚠️ di UI.
- **Autoprefixer & PostCSS** — alat teknis di balik layar yang memastikan CSS yang dihasilkan Tailwind bekerja di semua browser modern.

Manfaat bagi pengguna bisnis: tampilan aplikasi akan lebih profesional, konsisten, dan sesuai brand BNI setelah refactor UI selesai.

## Penjelasan Teknis
**File yang dimodifikasi:**
- `frontend/package.json`

**Perubahan:**
- Menambahkan ke `dependencies` (dipakai saat runtime/produksi):
  - `"lucide-react": "0.378.0"` — library ikon SVG untuk React
  - `"tailwindcss": "3.4.1"` — framework CSS utility-first
- Menambahkan ke `devDependencies` (hanya dipakai saat build/development):
  - `"autoprefixer": "10.4.19"` — PostCSS plugin untuk vendor prefix otomatis
  - `"postcss": "8.4.38"` — tool transformasi CSS, diperlukan oleh Tailwind

**Keputusan desain:**
- Semua versi di-_pin_ tanpa `^` atau `~` agar setiap `npm install` menghasilkan dependency tree yang identik, mencegah breaking change tak terduga dari minor/patch update.
- `tailwindcss` masuk ke `dependencies` (bukan `devDependencies`) karena CRA (`react-scripts`) memproses Tailwind sebagai bagian dari build pipeline produksi.

**Catatan:** Task ini hanya memperbarui `package.json`. `npm install` belum dijalankan — ini dilakukan secara terpisah oleh developer.

## Struktur Kode (tidak relevan)
Task ini hanya mengubah konfigurasi JSON, tidak ada fungsi/class baru.

## Simulasi / Skenario

**Sebelum task:**
```json
"dependencies": {
  "react": "18.2.0",
  ...
}
"devDependencies": {
  "prettier": "3.2.5",
  ...
}
```

**Setelah task:**
```json
"dependencies": {
  "lucide-react": "0.378.0",   // ← ditambahkan
  "tailwindcss": "3.4.1",      // ← ditambahkan
  "react": "18.2.0",
  ...
}
"devDependencies": {
  "autoprefixer": "10.4.19",   // ← ditambahkan
  "postcss": "8.4.38",         // ← ditambahkan
  "prettier": "3.2.5",
  ...
}
```

**Setelah developer menjalankan `npm install`:** Semua paket terunduh ke `node_modules/`, dan task-task selanjutnya (konfigurasi Tailwind, penulisan komponen) dapat berjalan.

## Keterkaitan dengan Komponen Lain
- **Bergantung pada:** Tidak ada dependensi lain dari task ini.
- **Digunakan oleh:**
  - Task 1.2 — `tailwind.config.js` memerlukan `tailwindcss` terpasang
  - Task 1.3 — `postcss.config.js` memerlukan `tailwindcss` dan `autoprefixer`
  - Task 1.4 — `index.css` menggunakan `@tailwind` directives
  - Semua task komponen (3.x – 15.x) yang menggunakan Tailwind classes dan Lucide icons
- **Pengaruh ke:** Jika versi diubah, seluruh build pipeline Tailwind dan semua ikon Lucide yang digunakan di 9 halaman + 3 komponen bersama akan terdampak.

## Requirements yang Dipenuhi
- **Requirement 1.1**: Frontend project menyertakan `tailwindcss` versi `3.4.1` sebagai dependency
- **Requirement 1.2**: Frontend project menyertakan `lucide-react` versi `0.378.0` sebagai dependency
- **Requirement 1.3**: Frontend project menyertakan `autoprefixer` versi `10.4.19` dan `postcss` versi `8.4.38` sebagai devDependency

## Catatan Penting
- **Jangan jalankan `npm install` secara otomatis** — biarkan developer memutuskan kapan melakukan install.
- Versi dipilih sesuai spec: Tailwind `3.4.1` (bukan v4 yang masih dalam beta), Lucide `0.378.0`.
- `tailwindcss` ditempatkan di `dependencies` (bukan `devDependencies`) karena ini adalah konvensi yang umum untuk CRA-based projects — CRA tidak memisahkan dev/prod build dependencies secara ketat.
