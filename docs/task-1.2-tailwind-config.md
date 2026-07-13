# Task UI 1.2 — Tailwind CSS Configuration (BNI Design System)

## Ringkasan Singkat

File `tailwind.config.js` adalah konfigurasi inti Tailwind CSS untuk project frontend Campaign Insight Generator. File ini mendefinisikan token desain BNI (warna brand dan tipografi Inter) serta menentukan path scan konten agar Tailwind hanya menghasilkan CSS yang benar-benar dipakai.

---

## Penjelasan Awam (Non-Technical)

Bayangkan Tailwind CSS seperti kotak cat berisi ratusan warna standar. Tapi brand BNI punya dua warna khusus — Teal (`#005E6A`, warna hijau-biru gelap yang ada di logo BNI) dan Orange (`#F15A24`, warna oranye aksen). Konfigurasi ini "menambahkan dua warna BNI tersebut ke dalam kotak cat Tailwind" sehingga seluruh tim developer bisa memakainya dengan nama yang konsisten (`bni-teal`, `bni-orange`).

Selain warna, konfigurasi ini juga menetapkan bahwa seluruh teks di aplikasi menggunakan font **Inter** — font yang terasa modern, bersih, dan profesional sesuai standar antarmuka enterprise seperti dashboard bank.

Manfaat bagi pengguna bisnis: tampilan aplikasi selalu konsisten dengan brand BNI di semua halaman, tanpa perbedaan warna atau font yang membingungkan.

---

## Penjelasan Teknis

### File yang Dibuat

- **`frontend/tailwind.config.js`** — konfigurasi utama Tailwind CSS

### Konfigurasi Content Path

```js
content: ['./src/**/*.{ts,tsx}']
```

Tailwind melakukan *purging* — hanya CSS yang kelasnya benar-benar dipakai di source file yang dimasukkan ke dalam bundle final. Path ini menginstruksikan Tailwind untuk memindai semua file `.ts` dan `.tsx` di folder `src/`. File `.js` dan `.jsx` tidak digunakan karena project ini full TypeScript.

### Token Warna BNI

```js
colors: {
  'bni-teal': '#005E6A',   // BNI primary brand color
  'bni-orange': '#F15A24', // BNI accent color
}
```

Kedua token ini di-extend ke dalam palet warna default Tailwind. Artinya, semua 500+ warna default Tailwind tetap tersedia, ditambah dua warna BNI ini. Developer bisa menggunakan class seperti `bg-bni-teal`, `text-bni-teal`, `border-bni-orange`, dll.

**Catatan penting:** Banyak komponen juga menggunakan literal hex langsung seperti `bg-[#005E6A]` (JIT arbitrary value). Token `bni-teal` dan `bni-orange` menyediakan alias semantik yang lebih readable untuk kasus-kasus yang membutuhkannya.

### Font Family Inter

```js
fontFamily: {
  sans: ['Inter', 'sans-serif'],
}
```

Ini menggantikan font `sans` default Tailwind (yang biasanya `ui-sans-serif, system-ui, ...`) dengan Inter sebagai prioritas pertama. Karena Tailwind menetapkan `font-sans` pada elemen `body` secara default, seluruh aplikasi otomatis menggunakan Inter tanpa konfigurasi tambahan di level komponen. Font Inter sendiri di-load via `@import` Google Fonts di `src/index.css`.

### Arsitektur PostCSS Pipeline

```
src/index.css
    → postcss-loader (CRA internal)
    → tailwind.config.js dibaca oleh plugin tailwindcss
    → scan konten ./src/**/*.{ts,tsx}
    → generate utility classes
    → autoprefixer menambah vendor prefix
    → bundle CSS final
```

CRA 5.x sudah menyertakan `postcss-loader` bawaan, sehingga tidak perlu ejecting atau CRACO.

---

## Struktur Kode

```js
module.exports = {
  content: [...],        // Path scan untuk purging
  theme: {
    extend: {
      colors: {...},     // Token warna BNI
      fontFamily: {...}, // Inter font stack
    },
  },
  plugins: [],           // Tidak ada plugin tambahan (untuk saat ini)
}
```

Menggunakan `theme.extend` (bukan override `theme` langsung) agar semua utilitas default Tailwind tetap tersedia.

---

## Simulasi / Skenario

### Skenario 1 — Penggunaan warna BNI di komponen

**Developer menulis:**
```tsx
<button className="bg-bni-teal hover:bg-[#004852] text-white rounded-lg px-4 py-2">
  Apply Filter
</button>
```

**Hasil:** Button dengan background hijau-biru BNI (#005E6A), berubah lebih gelap saat hover.

### Skenario 2 — Font Inter otomatis

**Tanpa konfigurasi tambahan apapun di komponen:**
```tsx
<p className="text-xs text-slate-600">Total Leads: 1,234</p>
```

**Hasil:** Teks menggunakan Inter font karena `font-sans` di-apply ke `body` oleh Tailwind preflight CSS.

### Skenario 3 — Purging CSS

**Di build production:**
- Tailwind scan semua `.ts` dan `.tsx` di `src/`
- Hanya class yang ditemukan di file tersebut yang dimasukkan ke bundle
- Class yang tidak dipakai (misalnya `bg-pink-300`) tidak muncul di CSS output
- Hasil: bundle CSS yang sangat kecil dan efisien

---

## Keterkaitan dengan Komponen Lain

- **Bergantung pada:**
  - `frontend/postcss.config.js` (Task 1.3) — menghubungkan Tailwind ke PostCSS pipeline CRA
  - `frontend/src/index.css` (Task 1.4) — memuat font Inter via Google Fonts `@import`
  - `tailwindcss@3.4.1` di `package.json` (Task 1.1) — versi library yang dipinned

- **Digunakan oleh:**
  - Semua file `.tsx` di `frontend/src/` yang menggunakan Tailwind utility classes
  - Build pipeline CRA (`npm run build` / `npm start`)

- **Pengaruh ke:**
  - Semua komponen yang menggunakan class `bni-teal` atau `bni-orange` akan kehilangan warna jika file ini diubah
  - Mengubah `content` path bisa menyebabkan class tidak di-generate (build rusak atau style hilang)

---

## Requirements yang Dipenuhi

- **Requirement 1.4** — `tailwind.config.js` mendefinisikan custom color `bni-teal` = `#005E6A`
- **Requirement 1.5** — `tailwind.config.js` mendefinisikan custom color `bni-orange` = `#F15A24`
- **Requirement 1.6** — `tailwind.config.js` mendefinisikan `fontFamily.sans` = `['Inter', 'sans-serif']`
- **Requirement 1.7** — `tailwind.config.js` menyertakan path `./src/**/*.{ts,tsx}` pada field `content`

---

## Catatan Penting

- **Versi Tailwind:** Config ini untuk Tailwind CSS 3.4.1 (format `module.exports`, bukan ESM `export default`). CRA menggunakan CommonJS, sehingga `module.exports` adalah format yang benar.
- **Arbitrary values tetap valid:** Komponen menggunakan `bg-[#005E6A]` dan `bg-[#005E6A]/20` secara langsung — ini valid di Tailwind JIT dan tidak memerlukan token terdaftar.
- **Tidak ada plugin:** Saat ini tidak ada Tailwind plugin tambahan (seperti `@tailwindcss/forms` atau `@tailwindcss/typography`) agar bundle tetap minimal.
- **Todo:** Jika desain sistem berkembang, token warna tambahan (status colors, surface colors) bisa ditambahkan di section `extend.colors`.
