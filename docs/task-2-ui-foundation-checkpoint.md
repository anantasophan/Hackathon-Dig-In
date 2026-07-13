# Task 2 — Checkpoint Verifikasi Foundation

## Ringkasan Singkat

Task ini adalah checkpoint verifikasi yang memastikan bahwa semua 4 file foundation untuk UI Redesign (BNI Design System) telah terpasang dengan benar dan memiliki konten yang sesuai spesifikasi, sebelum implementasi komponen dan halaman dilanjutkan.

## Penjelasan Awam (Non-Technical)

Bayangkan sedang membangun sebuah rumah. Sebelum mendirikan dinding dan memasang atap, kita harus memastikan pondasi sudah benar — lantai rata, tiang kokoh, pipa air terpasang. Checkpoint ini adalah momen "memeriksa pondasi" tersebut.

Keempat file yang diverifikasi ibarat:
- **package.json** → daftar belanja material bangunan (versi library yang dipakai)
- **tailwind.config.js** → palet warna dan font resmi BNI yang harus digunakan
- **postcss.config.js** → mesin pengolah CSS agar semua browser bisa membacanya
- **index.css** → fondasi gaya visual global yang diterapkan ke seluruh aplikasi

Jika salah satu fondasi ini salah, seluruh tampilan aplikasi akan ikut rusak.

## Penjelasan Teknis

### File yang Diverifikasi

**1. `frontend/package.json`**

Memastikan dependensi yang dipinned (versi tetap) sudah benar:
- `dependencies`:
  - `tailwindcss: 3.4.1` ✅
  - `lucide-react: 0.378.0` ✅
- `devDependencies`:
  - `autoprefixer: 10.4.19` ✅
  - `postcss: 8.4.38` ✅

Versi di-pin secara eksplisit (tanpa `^` atau `~`) untuk memastikan reproducible builds di semua environment.

**2. `frontend/tailwind.config.js`**

Memastikan konfigurasi Tailwind sesuai BNI Design System:
- `content: ['./src/**/*.{ts,tsx}']` — scan hanya file TypeScript React ✅
- `colors.bni-teal: '#005E6A'` — warna primary BNI (teal/hijau gelap) ✅
- `colors.bni-orange: '#F15A24'` — warna aksen BNI (oranye) ✅
- `fontFamily.sans: ['Inter', 'sans-serif']` — font Inter sebagai default ✅

**3. `frontend/postcss.config.js`**

Memastikan PostCSS pipeline benar untuk Create React App (CRA):
- Plugin `tailwindcss` terdaftar lebih dulu ✅
- Plugin `autoprefixer` terdaftar setelah tailwindcss ✅
- Urutan ini penting: Tailwind menghasilkan CSS, autoprefixer menambahkan vendor prefix

**4. `frontend/src/index.css`**

Memastikan semua elemen global CSS sudah ada:
- `@import` Google Fonts Inter (weights 300–700) ✅
- `@tailwind base` ✅
- `@tailwind components` ✅
- `@tailwind utilities` ✅
- Custom classes BNI: `.bni-teal`, `.bg-bni-teal`, `.bni-orange`, `.bg-bni-orange` ✅
- `.table-fixed-header th` dengan `position: sticky`, `top: 0`, `z-index: 10` ✅
- `.truncate-2-lines` dengan `-webkit-line-clamp: 2` ✅

### Metode Verifikasi

Checkpoint ini dilakukan dengan **pembacaan dan inspeksi konten file** secara langsung (file read), bukan dengan menjalankan `npm run build`. Pendekatan ini dipilih karena:
1. Verifikasi konten file lebih cepat dan tidak memerlukan runtime Node.js
2. Tidak ada perubahan kode yang dilakukan — murni checkpoint
3. `npm run build` akan diverifikasi di checkpoint wave selanjutnya (Task 6 dan Task 13)

## Struktur Kode (relevan)

```
frontend/
├── package.json              # Dependensi + versi
├── tailwind.config.js        # Konfigurasi Tailwind + BNI tokens
├── postcss.config.js         # Pipeline PostCSS (CRA)
└── src/
    └── index.css             # Global styles + Tailwind directives
```

## Simulasi / Skenario

**Skenario 1 — Semua file valid (happy path)**

```
Verifikasi package.json → tailwindcss: 3.4.1 ✅, lucide-react: 0.378.0 ✅
Verifikasi tailwind.config.js → bni-teal: #005E6A ✅, Inter font ✅
Verifikasi postcss.config.js → tailwindcss {} dan autoprefixer {} ✅
Verifikasi index.css → @tailwind directives ✅, custom classes ✅
→ Hasil: CHECKPOINT LULUS — lanjut ke Task 3
```

**Skenario 2 — Versi dependensi salah**

```
package.json memiliki tailwindcss: "^3.0.0" (bukan 3.4.1 exact)
→ Risiko: versi minor berbeda bisa menghasilkan utility classes berbeda
→ Tindakan: perbarui ke "3.4.1" tanpa caret
```

**Skenario 3 — Urutan PostCSS plugin terbalik**

```
postcss.config.js memiliki autoprefixer sebelum tailwindcss
→ Autoprefixer tidak dapat mengolah class Tailwind yang belum dibuat
→ Tindakan: pindahkan tailwindcss ke posisi pertama
```

## Keterkaitan dengan Komponen Lain

- **Bergantung pada**: Task 1.1–1.4 (instalasi dan pembuatan file foundation)
- **Digunakan oleh**: Semua task selanjutnya (Task 3–16) — setiap komponen React akan menggunakan Tailwind classes, Lucide icons, dan Inter font yang dikonfigurasi di sini
- **Pengaruh ke**: Jika `tailwind.config.js` diubah (misalnya content path), Tailwind tidak akan men-generate class yang digunakan di komponen

## Requirements yang Dipenuhi

- **1.1** — Tailwind CSS 3.4.1 dan PostCSS pipeline terpasang dengan benar
- **1.2** — Lucide React 0.378.0 tersedia sebagai dependensi
- **1.3** — Versi autoprefixer dan postcss di-pin di devDependencies
- **1.4** — Tailwind content scan dikonfigurasi ke `src/**/*.{ts,tsx}`
- **1.5** — BNI Teal color token `#005E6A` tersedia sebagai `bni-teal`
- **1.6** — BNI Orange color token `#F15A24` tersedia sebagai `bni-orange`
- **1.7** — Font Inter dikonfigurasi sebagai font sans default
- **1.8** — `@tailwind base/components/utilities` directives ada di index.css
- **1.9** — Google Fonts Inter (weights 300–700) di-import di index.css
- **1.10** — BNI custom color classes tersedia secara global
- **1.11** — `.table-fixed-header` dan `.truncate-2-lines` utility classes tersedia

## Catatan Penting

- **Verifikasi ini bersifat read-only** — tidak ada file yang diubah, semua sudah benar sejak Task 1
- **`npm run build` tidak dijalankan** pada checkpoint ini sesuai instruksi task; build verification dilakukan di checkpoint wave berikutnya
- **`tailwindcss` ada di `dependencies` bukan `devDependencies`** — ini disengaja karena CRA (react-scripts) membutuhkan Tailwind di runtime build, bukan hanya dev
- Semua 4 file telah diverifikasi dan hasilnya: **SEMUA LULUS**
