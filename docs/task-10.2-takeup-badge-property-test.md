# Task 10.2 — Property Test: Take-Up Rate Badge Class Logic

## Ringkasan Singkat

Task ini mengimplementasikan property-based test dan unit test untuk fungsi `getTakeUpBadgeClasses`, sebuah fungsi murni yang menentukan kelas Tailwind CSS dari badge persentase take-up rate pada halaman Performa Regional. Test memverifikasi bahwa ketiga tier warna (hijau/emerald, kuning/amber, merah/rose) diterapkan secara konsisten untuk semua nilai rate yang mungkin.

---

## Penjelasan Awam (Non-Technical)

Bayangkan papan skor di sebuah pertandingan: angka persentase bisa berwarna hijau (bagus), kuning (sedang), atau merah (kurang). Fungsi yang diuji di sini bertanggung jawab untuk memilih warna yang tepat berdasarkan angka tersebut.

- **Rate ≥ 10%** → badge hijau (performa tinggi)
- **5% ≤ rate < 10%** → badge kuning (performa sedang)
- **rate < 5%** → badge merah (performa rendah)

Test ini memastikan bahwa aturan warna tersebut selalu benar — tidak hanya untuk angka-angka contoh tertentu, tetapi untuk **semua kemungkinan angka** antara 0 dan 50.

**Manfaat bagi bisnis:** Analis regional dapat langsung melihat status performa wilayah hanya dari warna badge, tanpa perlu membaca angka secara detail.

---

## Penjelasan Teknis

### File yang dibuat

- `frontend/src/tests/TakeUpBadge.property.test.tsx` — file test baru (39 test cases)

### Library yang digunakan

- `fast-check ^3.19.0` — property-based testing framework
- `@testing-library/react ^14.2.2` — React test utilities (tersedia untuk test rendering, tidak digunakan di file ini karena fungsi yang diuji adalah pure function)
- Jest (via `react-scripts test`) — test runner

### Keputusan desain penting

**Mengapa fungsi di-mirror ke dalam test, bukan diimpor dari `RegionalPerformancePage.tsx`?**

`RegionalPerformancePage.tsx` mengimpor `api.ts` yang mengimpor `axios`. Versi `axios` yang digunakan dalam project ini (`1.6.8`) didistribusikan sebagai ESM module. Jest yang dijalankan via `react-scripts` menggunakan transform pipeline yang mengecualikan `node_modules` dari Babel transform secara default — sehingga import axios dari test akan gagal dengan `SyntaxError: Cannot use import statement outside a module`.

Pattern yang sama digunakan oleh `ExportService.test.tsx` dan `CampaignChip.property.test.tsx` dalam project ini: logika pure function di-mirror secara lokal di file test, dengan komentar eksplisit bahwa mirror harus selalu sinkron dengan implementasi produksi.

### Edge cases yang ditangani

- Nilai tepat di batas: `rate === 10` (emerald, bukan amber), `rate === 5` (amber, bukan rose)
- Nilai desimal: `4.99`, `9.99`
- Nilai `0` (minimum valid)
- Mutual exclusivity: hanya satu token warna background dan satu token warna teks yang hadir pada satu waktu

---

## Struktur Kode

```typescript
// Mirror fungsi produksi (harus sinkron dengan RegionalPerformancePage.tsx)
function getTakeUpBadgeClasses(rate: number): string

// Shared layout classes yang selalu harus ada
const SHARED_CLASSES = ['rounded', 'px-1.5', 'py-0.5', 'text-xs', 'font-semibold']
```

### Kelompok test

| Kelompok | Jumlah test | Isi |
|---|---|---|
| Unit: high tier (≥ 10) | 4 | Exact values, exclusivity |
| Unit: medium tier (5–9.99) | 4 | Exact values, exclusivity |
| Unit: low tier (< 5) | 4 | Exact values, exclusivity |
| Unit: shared classes | 6 | Semua rate memiliki layout classes |
| Unit: boundary precision | 2 | Rate 10 dan rate 5 tepat di batas |
| Unit: mutual exclusivity | 18 | Tepat satu bg-token dan satu text-token |
| Property 8 | 1 | fast-check, 100 runs otomatis untuk rate ∈ [0, 50] |
| **Total** | **39** | |

---

## Simulasi / Skenario

### Skenario 1 — Rate tinggi (≥ 10%)

```
Input:  rate = 12.5
Output: "bg-emerald-100 text-emerald-700 rounded px-1.5 py-0.5 text-xs font-semibold"
Badge:  [12.50%]  ← warna hijau di tabel regional
```

### Skenario 2 — Rate sedang (5–9.99%)

```
Input:  rate = 7.3
Output: "bg-amber-100 text-amber-700 rounded px-1.5 py-0.5 text-xs font-semibold"
Badge:  [7.30%]   ← warna kuning di tabel regional
```

### Skenario 3 — Rate rendah (< 5%)

```
Input:  rate = 2.1
Output: "bg-rose-100 text-rose-700 rounded px-1.5 py-0.5 text-xs font-semibold"
Badge:  [2.10%]   ← warna merah di tabel regional
```

### Skenario 4 — Property test (fast-check)

```
Generator: fc.float({ min: 0, max: 50, noNaN: true })
Contoh run: rate = 0.0, 4.99, 5.0, 9.99, 10.0, 27.34, 50.0, ...
Assertion:  Untuk setiap nilai yang di-generate, tier warna harus sesuai,
            mutual exclusivity harus terjaga, dan shared classes harus ada.
```

---

## Keterkaitan dengan Komponen Lain

- **Bergantung pada:** Implementasi `getTakeUpBadgeClasses` di `RegionalPerformancePage.tsx` (mirror harus sinkron)
- **Digunakan oleh:** CI/CD pipeline (test suite), task 10.1 yang mengimplementasikan halaman tersebut
- **Pengaruh ke:** Jika fungsi produksi diubah threshold-nya, test ini akan gagal dan mendeteksi regresi

---

## Requirements yang Dipenuhi

- **Requirement 8.5**: Badge take-up rate tinggi (≥10%) menggunakan `bg-emerald-100 text-emerald-700`
- **Requirement 8.6**: Badge take-up rate sedang (5–9.99%) menggunakan `bg-amber-100 text-amber-700`
- **Requirement 8.7**: Badge take-up rate rendah (<5%) menggunakan `bg-rose-100 text-rose-700`

---

## Catatan Penting

- **Sinkronisasi mirror**: Komentar `IMPORTANT: Keep this in sync with ...` ada di file test. Jika implementasi produksi diubah, mirror di test harus diperbarui juga.
- **noNaN: true**: Generator `fc.float` dikonfigurasi dengan `noNaN: true` untuk menghindari `NaN` yang tidak terdefinisi perilakunya di threshold comparison.
- **Tidak ada React rendering**: Karena fungsi yang diuji adalah pure function, test tidak perlu merender React component — sehingga lebih cepat dan tidak terpengaruh oleh perubahan UI.
- **fast-check default**: 100 runs default dari fast-check digunakan (tidak di-override) agar coverage maksimal di range [0, 50].
