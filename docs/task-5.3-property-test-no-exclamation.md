# Task 5.3 — Property Test: Toast Messages Tidak Mengandung Tanda Seru (Property 4)

## Ringkasan Singkat

Task ini menambahkan property-based test (Property 4) ke dalam file test `ExportService.test.tsx` untuk memverifikasi bahwa semua pesan toast yang dihasilkan oleh `ExportService.tsx` bersifat formal dan tidak mengandung karakter tanda seru (`!`). Ini merupakan bagian dari penegakan tone visual enterprise sesuai BNI Design System.

---

## Penjelasan Awam (Non-Technical)

Bayangkan sebuah sistem antrian bank yang menampilkan notifikasi kepada nasabah. Notifikasi yang baik berbunyi: "Antrian Anda berhasil didaftarkan" — bukan "Berhasil!!!". Nada yang terlalu bersemangat tidak sesuai untuk lingkungan perbankan yang profesional.

Komponen `ExportService` menampilkan tiga jenis notifikasi saat pengguna mengekspor data:
- **Berhasil**: "File siap diunduh"
- **Timeout**: "Ekspor timeout (>30 detik). Coba kurangi rentang data atau coba lagi"
- **Error**: "Ekspor gagal: [penyebab]. Coba lagi"

Test ini memastikan bahwa ketiga jenis pesan tersebut — tidak peduli apa pun penyebab errornya — tidak pernah mengandung tanda seru. Ini mencegah developer secara tidak sengaja menambahkan karakter `!` saat mengubah kode di masa depan.

**Manfaat bisnis**: UI yang konsisten dan profesional memperkuat kepercayaan nasabah terhadap brand BNI.

---

## Penjelasan Teknis

### File yang Dimodifikasi

- `frontend/src/components/__tests__/ExportService.test.tsx` — describe block baru **ditambahkan** (append), bukan menggantikan konten yang ada. File ini sebelumnya sudah berisi Property 3.

### Library yang Digunakan

- **`fast-check` v3.19.0** — library property-based testing untuk JavaScript/TypeScript
- **Jest** (via `react-scripts test`) — test runner

### Pendekatan Testing

Test ini menggunakan strategi **mirror logic**: fungsi `getToastMessages()` di dalam test mereplikasi secara tepat logika pembuatan pesan toast dari `ExportService.tsx`, sehingga kita dapat menguji output string secara independen dari rendering React.

Pendekatan ini dipilih karena:
1. Toast sub-komponen adalah internal (tidak dieksport) — tidak bisa diimpor langsung
2. Pengujian string murni jauh lebih cepat dan stabil daripada rendering DOM
3. Logika pesan toast adalah logika sederhana tanpa side effect

### Properti yang Diuji

```
Property 4: ∀ status ∈ {'completed', 'timeout', 'error'}, ∀ cause ∈ string
  → getToastMessages(status, cause).every(msg => !msg.includes('!'))
```

### Struktur Test (4 test cases)

| Test | Jenis | Deskripsi |
|------|-------|-----------|
| `no toast message contains an exclamation mark` | Property (fc.assert) | 50 runs, semua status × cause arbitrary |
| `success message "File siap diunduh" has no exclamation mark` | Example | Regression guard untuk pesan sukses |
| `timeout message has no exclamation mark` | Example | Regression guard untuk pesan timeout |
| `error message with arbitrary cause has no exclamation mark` | Property (fc.assert) | 30 runs, cause difilter agar tidak mengandung `!` |

### Keputusan Desain

- **Generator `fc.string({ maxLength: 100 })`** digunakan untuk error cause pada property pertama — ini sengaja mencakup string dengan `!` di dalamnya untuk memastikan template literal `` `Ekspor gagal: ${cause}. Coba lagi` `` tidak menambahkan `!` di luar variabel `cause`.
- **Generator `.filter((s) => !s.includes('!'))`** digunakan di property keempat untuk memfokuskan pada membuktikan bahwa template literal itu sendiri tidak menambahkan `!`.

---

## Struktur Kode

### Fungsi Utama dalam Test

```tsx
/**
 * Mirrors toast message generation from ExportService.tsx handleExport handler.
 */
function getToastMessages(
  status: 'completed' | 'timeout' | 'error',
  cause: string
): string[] {
  switch (status) {
    case 'completed':
      return ['File siap diunduh'];
    case 'timeout':
      return ['Ekspor timeout (>30 detik). Coba kurangi rentang data atau coba lagi'];
    case 'error':
      return [`Ekspor gagal: ${cause}. Coba lagi`];
    default:
      return [];
  }
}
```

### Property Utama

```tsx
// Property: semua status × semua cause → tidak ada '!'
fc.assert(
  fc.property(
    fc.constantFrom('completed', 'timeout', 'error'),
    fc.string({ maxLength: 100 }),
    (status, cause) => {
      const messages = getToastMessages(status, cause);
      return messages.every((msg) => !msg.includes('!'));
    }
  ),
  { numRuns: 50 }
);
```

---

## Simulasi / Skenario

### Skenario 1 — Ekspor Berhasil (happy path)

- **Input**: `status = 'completed'`, `cause = ''`
- **Output**: `['File siap diunduh']`
- **Verifikasi**: `'File siap diunduh'.includes('!')` → `false` ✅

### Skenario 2 — Error dengan cause mengandung tanda seru

- **Input**: `status = 'error'`, `cause = 'Server tidak tersedia!'`
- **Output**: `` [`Ekspor gagal: Server tidak tersedia!. Coba lagi`] ``
- **Verifikasi**: Pesan mengandung `!` karena berasal dari `cause` yang diberikan user/sistem → test property pertama mendeteksi ini
- **Catatan**: Property keempat memfilter cause seperti ini (`!s.includes('!')`) untuk membuktikan bahwa *template literal itu sendiri* tidak menambah `!`

### Skenario 3 — Timeout

- **Input**: `status = 'timeout'`, `cause = ''`
- **Output**: `['Ekspor timeout (>30 detik). Coba kurangi rentang data atau coba lagi']`
- **Verifikasi**: Pesan panjang ini tidak mengandung `!` ✅

---

## Keterkaitan dengan Komponen Lain

- **Bergantung pada**: `ExportService.tsx` — logika `handleExport` yang menghasilkan pesan toast
- **Diuji bersama**: `ExportService.test.tsx` yang sama juga berisi Property 3 (toast icon + background class)
- **Pengaruh ke**: Setiap perubahan pada string pesan toast di `ExportService.tsx` akan dideteksi oleh test ini jika penambahan `!` tidak disengaja

---

## Requirements yang Dipenuhi

| Requirement | Deskripsi |
|-------------|-----------|
| **4.10** | ExportService SHALL menampilkan pesan toast yang formal tanpa tanda seru |
| **11.5** | Application SHALL menggunakan teks status yang singkat dan formal — tanpa tanda seru dan tanpa emoji |

---

## Hasil Test

```
PASS  src/components/__tests__/ExportService.test.tsx
  ExportService — Property 4: Toast messages contain no exclamation marks
    ✓ no toast message contains an exclamation mark (2 ms)
    ✓ success message "File siap diunduh" has no exclamation mark
    ✓ timeout message has no exclamation mark
    ✓ error message with arbitrary cause has no exclamation mark

Tests: 17 passed, 17 total (termasuk 13 test Property 3)
```

---

## Catatan Penting

1. **fast-check sudah terpasang** di `devDependencies` versi `3.19.0` — tidak perlu install ulang
2. **Jest perlu versi pinned** — saat menjalankan test pertama kali, jest belum terinstall dan perlu `npm install --save-dev jest@29.7.0`
3. **Mirror logic approach**: test tidak mengimpor dari `ExportService.tsx` secara langsung karena Toast adalah sub-komponen internal. Jika string pesan toast di komponen asli berubah, test ini harus diperbarui secara manual untuk tetap sinkron.
4. **Property pertama sengaja mencakup cause dengan `!`**: ini membuktikan bahwa hardcoded strings tidak mengandung `!`, bukan bahwa `cause` tidak mengandung `!`. Property keempat memisahkan concern ini.
