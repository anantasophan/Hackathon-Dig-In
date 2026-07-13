# Task UI 1.4 — `index.css`: Tailwind Directives, Inter Font, dan Custom Classes

## Ringkasan Singkat

Task ini menimpa file `frontend/src/index.css` — titik masuk utama CSS aplikasi React — dengan konten baru yang mengintegrasikan Tailwind CSS ke dalam pipeline CRA (Create React App), mengimpor font Inter dari Google Fonts, dan mendefinisikan beberapa custom utility class yang dibutuhkan oleh design system BNI.

---

## Penjelasan Awam (Non-Technical)

Bayangkan aplikasi seperti sebuah buku. Sebelum isinya ditulis, perlu ada "panduan tipografi" di halaman awal: jenis font apa yang dipakai, warna apa yang menjadi standar, dan aturan-aturan visual dasar. File `index.css` berperan seperti panduan itu.

Dengan update ini:
- **Font Inter** (font modern dan bersih khas aplikasi enterprise) diunduh otomatis dari Google setiap kali aplikasi dibuka.
- **Tailwind CSS** diaktifkan — ini yang memungkinkan semua class seperti `bg-white`, `rounded-xl`, dan `text-xs` bekerja di seluruh aplikasi.
- **Warna BNI Teal (#005E6A) dan BNI Orange (#F15A24)** didefinisikan sebagai class siap pakai.
- **Header tabel** dikonfigurasi agar tetap terlihat saat pengguna men-scroll tabel ke bawah (sticky header).
- **Teks panjang** bisa otomatis dipotong setelah 2 baris (truncate).

---

## Penjelasan Teknis

### File yang Dimodifikasi

- **`frontend/src/index.css`** — ditimpa sepenuhnya; konten lama (reset CSS manual, font stack system) dihapus dan digantikan dengan konten baru.

### Struktur Konten Baru

#### 1. Google Fonts Import
```css
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
```
Mengimpor font Inter dengan 5 weight (light 300, regular 400, medium 500, semibold 600, bold 700). Import harus berada **paling atas file**, sebelum `@tailwind` directives, karena PostCSS memproses file dari atas ke bawah.

#### 2. Tailwind Directives
```css
@tailwind base;
@tailwind components;
@tailwind utilities;
```
Tiga baris wajib yang menginstruksikan PostCSS/Tailwind untuk menyuntikkan:
- `base` — CSS reset (Preflight) berbasis modern-normalize
- `components` — slot untuk komponen Tailwind custom (jarang dipakai di sini)
- `utilities` — seluruh utility class yang digunakan di TSX files

#### 3. Body Font Override
```css
body {
  font-family: 'Inter', sans-serif;
}
```
Memastikan font Inter diterapkan ke seluruh elemen `body` secara global.

#### 4. BNI Color Utility Classes
```css
.bni-teal { color: #005E6A; }
.bg-bni-teal { background-color: #005E6A; }
.bni-orange { color: #F15A24; }
.bg-bni-orange { background-color: #F15A24; }
```
Class helper untuk warna brand BNI di luar nilai yang sudah dikonfigurasi di `tailwind.config.js`. Berguna untuk komponen legacy yang tidak dapat menggunakan Tailwind JIT secara langsung.

#### 5. Sticky Table Header
```css
.table-fixed-header th {
  position: sticky;
  top: 0;
  background: #F9FAFB;
  z-index: 10;
}
```
Kelas ini diterapkan pada elemen `<table>` yang membutuhkan header tetap terlihat saat tabel discroll. `z-index: 10` memastikan header tidak tertutup oleh konten sel tabel.

#### 6. Truncate 2 Lines
```css
.truncate-2-lines {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
```
Menggunakan properti CSS `-webkit-line-clamp` untuk memotong teks setelah baris ke-2 dan menambahkan ellipsis (`...`). Digunakan pada kartu campaign yang menampilkan deskripsi panjang.

### Keputusan Desain

- **Mengapa `@import` sebelum `@tailwind`?** PostCSS menjalankan Tailwind setelah resolusi import. Jika `@import` ditempatkan setelah directives, browser mungkin mengabaikannya karena `@import` harus menjadi pernyataan pertama dalam CSS file.
- **Mengapa font juga di `tailwind.config.js` dan juga di `body {}` CSS?** `tailwind.config.js` mendefinisikan `fontFamily.sans` untuk digunakan via class `font-sans`, sedangkan deklarasi `body { font-family }` memastikan elemen yang tidak memiliki class Tailwind juga menggunakan Inter.
- **Mengapa tidak hanya Tailwind config saja?** Karena Preflight (`@tailwind base`) me-reset `font-family` ke system font stack, deklarasi `body {}` di sini akan di-cascade setelah Preflight dan menang.

---

## Simulasi / Skenario

### Skenario 1 — Sticky Header Tabel Regional

**Input:** Pengguna membuka halaman Regional Performance yang menampilkan tabel dengan 50+ baris.

**Proses:** Tabel merender dengan class `table-fixed-header` di elemen `<table>`. Saat pengguna scroll ke bawah, CSS `position: sticky; top: 0` mempertahankan posisi `<th>` di viewport.

**Output:** Header kolom (Wilayah, Total Leads, Take Up Rate, dll) tetap terlihat di bagian atas tabel meski konten sudah discroll 30 baris ke bawah.

---

### Skenario 2 — Truncate Deskripsi Campaign Serupa

**Input:** Komponen kartu di SimilarCampaignPage menerima deskripsi campaign sepanjang 200 karakter.

**Proses:** Elemen `<p className="truncate-2-lines">` menerapkan `-webkit-line-clamp: 2`. CSS mengkalkulasi dua baris teks berdasarkan `line-height` aktif.

**Output:** Deskripsi ditampilkan maksimal 2 baris diikuti `...` tanpa overflow ke area kartu di bawahnya.

---

### Skenario 3 — Font Inter di Seluruh Aplikasi

**Input:** Browser membuka aplikasi untuk pertama kali.

**Proses:** `@import url('https://fonts.googleapis.com/')` men-trigger request ke Google Fonts CDN. Font Inter weight 300–700 di-cache browser. `body { font-family: 'Inter', sans-serif; }` menerapkan font ke semua teks.

**Output:** Seluruh UI menggunakan Inter — dari label filter `text-xs` hingga angka KPI `text-2xl font-bold`.

---

## Keterkaitan dengan Komponen Lain

- **Bergantung pada:** `frontend/postcss.config.js` (task 1.3) — PostCSS harus dikonfigurasi agar `@tailwind` directives dapat diproses. `frontend/tailwind.config.js` (task 1.2) — config menentukan class apa saja yang di-generate.
- **Digunakan oleh:** Semua file `.tsx` di `frontend/src/` — setiap komponen yang menggunakan Tailwind class bergantung pada file ini.
- **Pengaruh ke:** Jika `@tailwind utilities` dihapus dari file ini, seluruh class Tailwind di aplikasi akan berhenti bekerja. Jika `@import` Google Fonts dihapus, font Inter tidak akan dimuat dan UI jatuh ke `sans-serif` fallback.

---

## Requirements yang Dipenuhi

| Requirement | Keterangan |
|-------------|------------|
| **1.8** | `@import` Google Fonts Inter dengan weights 300, 400, 500, 600, 700 |
| **1.9** | Definisi `.bni-teal`, `.bg-bni-teal`, `.bni-orange`, `.bg-bni-orange` |
| **1.10** | `.table-fixed-header th` dengan `position: sticky` dan `z-index: 10` |
| **1.11** | `.truncate-2-lines` dengan `-webkit-line-clamp: 2` |

---

## Catatan Penting

1. **Google Fonts membutuhkan koneksi internet** — jika aplikasi dijalankan di environment offline, font Inter tidak akan dimuat dan browser fallback ke `sans-serif` system font.
2. **`-webkit-line-clamp` adalah properti vendor-prefixed** — sudah luas didukung di browser modern (Chrome, Firefox 68+, Safari, Edge), tetapi secara teknis masih experimental untuk non-WebKit. Untuk produksi, ini sudah cukup.
3. **Class `.bni-teal` vs `text-[#005E6A]`** — komponen yang menggunakan Tailwind JIT lebih disarankan menggunakan `text-[#005E6A]` atau `text-bni-teal` (dari config). Class `.bni-teal` di sini adalah fallback untuk kasus yang tidak bisa menggunakan Tailwind JIT.
4. **Konten lama `index.css` dihapus sepenuhnya** — CSS reset manual (`box-sizing`, `body margin`, system font stack, `h1-h6 margin`, dll) tidak lagi diperlukan karena Tailwind Preflight sudah menyediakan reset yang lebih konsisten.
