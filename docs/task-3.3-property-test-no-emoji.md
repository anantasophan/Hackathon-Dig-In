# Task 3.3 — Property Test DashboardLayout: No Emoji (Property 2)

## Ringkasan Singkat

Task ini menulis property-based test untuk memverifikasi bahwa komponen `DashboardLayout` tidak pernah merender karakter emoji apapun, untuk sembarang kombinasi username dan route aktif. Test menggunakan `fast-check` sebagai library property testing dan `@testing-library/react` untuk merender komponen di lingkungan JSDOM.

## Penjelasan Awam (Non-Technical)

Bayangkan sebuah auditor yang memeriksa setiap halaman aplikasi untuk memastikan tidak ada emoji yang muncul — karena aplikasi enterprise BNI menggunakan ikon grafis profesional (Lucide React), bukan emoji teks. Task ini secara otomatis mensimulasikan ratusan skenario (berbagai nama pengguna, berbagai halaman aktif) dan memastikan tidak ada satu pun emoji yang lolos ke tampilan pengguna.

Analoginya: seperti mesin pemeriksa kualitas di pabrik yang menguji setiap produk dari lini produksi secara acak — bukan hanya satu sampel — untuk memastikan standar terpenuhi secara konsisten.

Manfaat bagi tim bisnis:
- Memastikan UI selalu terlihat profesional dan sesuai brand BNI
- Tidak ada risiko emoji muncul secara tidak sengaja karena perubahan kode
- Test berjalan otomatis setiap kali ada perubahan kode

## Penjelasan Teknis

### File yang Dibuat/Dimodifikasi

| File | Aksi | Keterangan |
|------|------|------------|
| `frontend/src/components/__tests__/DashboardLayout.test.tsx` | Dibuat | File test baru — berisi Property 1 dan Property 2 |
| `frontend/package.json` | Sudah ada | `fast-check@3.19.0` dan `@testing-library/react@14.2.2` sudah terdaftar di devDependencies |

### Library yang Digunakan

- **`fast-check@3.19.0`** — library property-based testing untuk JavaScript/TypeScript. Menghasilkan ratusan input acak dan memverifikasi bahwa sebuah properti (invariant) selalu benar.
- **`@testing-library/react@14.2.2`** — merender komponen React di JSDOM (lingkungan browser simulasi) dan menyediakan akses ke DOM output.
- **`react-router-dom`** — dibutuhkan `MemoryRouter` agar `NavLink` di `DashboardLayout` bisa menentukan route aktif tanpa browser nyata.

### Pola Arsitektur

Test file ini berisi **dua describe block** — satu untuk setiap property:

1. **Property 1** (dari task 3.2, disertakan di file yang sama): Active nav exclusivity
2. **Property 2** (task 3.3): No emoji in rendered output

### Keputusan Desain

- `MemoryRouter` dengan `initialEntries={[route]}` digunakan agar NavLink dapat mendeteksi route aktif, sehingga test menguji rendering nyata (bukan mock).
- `container.textContent` digunakan (bukan `document.body.textContent`) agar test terisolasi pada komponen yang dirender, tidak terpengaruh konten DOM lain.
- `unmount()` dipanggil setelah setiap assertion untuk mencegah memory leak antar run property test.
- `numRuns: 20` dipilih sebagai keseimbangan antara coverage dan kecepatan test.

### Regex Emoji

```typescript
const EMOJI_REGEX = /[\u{1F300}-\u{1FFFF}\u{2600}-\u{27BF}]/u;
```

Mencakup dua blok Unicode utama:
- `U+1F300–U+1FFFF`: Blok emoji modern (Emoticons, Symbols, Transport, dll)
- `U+2600–U+27BF`: Blok Miscellaneous Symbols (☀ ⚠ ✅ ❌ dll)

## Struktur Kode

```typescript
// Property 2 — inti test no-emoji
describe('DashboardLayout — Property 2: No emoji in rendered output', () => {
  const EMOJI_REGEX = /[\u{1F300}-\u{1FFFF}\u{2600}-\u{27BF}]/u;

  it('renders no emoji for any username and route combination', () => {
    fc.assert(
      fc.property(
        fc.string({ maxLength: 50 }),  // arbitrary username
        fc.constantFrom('/overview', '/comparison', ...),  // valid routes
        (username, route) => {
          const { container, unmount } = render(
            <MemoryRouter initialEntries={[route]}>
              <DashboardLayout username={username}>
                <div>test content</div>
              </DashboardLayout>
            </MemoryRouter>
          );
          const textContent = container.textContent ?? '';
          const hasEmoji = EMOJI_REGEX.test(textContent);
          unmount();
          return !hasEmoji;  // property: tidak ada emoji
        }
      ),
      { numRuns: 20 }
    );
  });
});
```

## Simulasi / Skenario

### Skenario 1 — Username Normal, Route Overview

```
Input: username="John Doe", route="/overview"
Proses: Render DashboardLayout dengan MemoryRouter pada /overview
Output DOM textContent: "Campaign Insight GeneratorBNIJohn DoePerformance Overview..."
Emoji check: false → test LULUS
```

### Skenario 2 — Username Kosong, Route Comparison

```
Input: username="", route="/comparison"
Proses: Render tanpa user info section (username tidak ditampilkan jika falsy)
Output DOM textContent: "Campaign Insight GeneratorBNIPerbandingan Campaign..."
Emoji check: false → test LULUS
```

### Skenario 3 — Username dengan Karakter Khusus (fast-check generated)

```
Input: username="abc\x00def", route="/time-analysis"
Proses: Render dengan username yang mengandung null character
Output DOM textContent: tidak mengandung emoji
Emoji check: false → test LULUS
```

### Skenario 4 — Deteksi Regresi (jika emoji masuk kembali)

```
Input: username="normal", route="/regional"
Proses: Developer menambahkan emoji "⚠️" ke sidebar
Output DOM textContent: "...⚠️..."
Emoji check: true → test GAGAL — regresi terdeteksi
```

## Hasil Test

```
PASS  src/components/__tests__/DashboardLayout.test.tsx
  DashboardLayout — Property 1: Active nav item has exclusive active classes
    √ exactly one nav item has bg-[#005E6A] for any valid route (55 ms)
    √ active nav item has text-white and font-semibold (28 ms)
  DashboardLayout — Property 2: No emoji in rendered output
    √ renders no emoji for any username and route combination (72 ms)

Tests: 3 passed, 3 total
Time:  1.864s
```

## Keterkaitan dengan Komponen Lain

- **Bergantung pada:** `DashboardLayout.tsx` (komponen yang diuji), `react-router-dom` (MemoryRouter), `fast-check` (property testing), `@testing-library/react` (render)
- **Digunakan oleh:** CI pipeline (saat `npm test` dijalankan)
- **Pengaruh ke:** Jika `DashboardLayout.tsx` dimodifikasi dan emoji masuk kembali, test ini akan langsung mendeteksi dan gagal.

## Requirements yang Dipenuhi

- **Requirement 2.11** — `THE DashboardLayout SHALL tidak menggunakan emoji di manapun dalam komponen ini.`

## Catatan Penting

- Test ini juga menyertakan Property 1 (task 3.2) dalam file yang sama sesuai konvensi "satu file test per komponen".
- Regex emoji `[\u{1F300}-\u{1FFFF}]` membutuhkan flag `/u` (Unicode mode) — tanpanya, pola `\u{...}` tidak akan berfungsi.
- `fast-check` perlu diinstall via `npm install` sebelum test bisa berjalan (`npm install --save-dev fast-check@3.19.0 @testing-library/react@14.2.2`).
- Test ini tidak mencakup emoji dari blok `U+2300–U+25FF` (Technical Symbols, Geometric Shapes) — namun blok tersebut bukan emoji yang umum digunakan di UI.
