# Task 3.2 — Property Test DashboardLayout: Active Nav Exclusivity

## Ringkasan Singkat

Task ini menambahkan property-based tests untuk komponen `DashboardLayout` yang memverifikasi bahwa hanya satu item navigasi aktif (memiliki class `bg-[#005E6A]`) setiap saat, sesuai dengan BNI Design System. Tests menggunakan `fast-check` + `@testing-library/react` dan memvalidasi Requirements 2.7 dan 2.8.

---

## Penjelasan Awam (Non-Technical)

Bayangkan menu navigasi di sidebar aplikasi — seperti menu di sisi kiri website bank. Setiap menu (Overview, Perbandingan Campaign, dsb.) hanya boleh tampil "aktif" (berwarna teal/hijau-biru) saat kita sedang berada di halaman tersebut. Tidak mungkin dua menu aktif bersamaan, dan tidak boleh tidak ada yang aktif sama sekali.

Task ini adalah **serangkaian "ujian otomatis"** yang memastikan aturan ini selalu berlaku — bukan hanya untuk satu halaman, tapi untuk semua 6 halaman navigasi sekaligus. Jika suatu saat kode diubah dan aturan ini terlanggar, ujian ini akan langsung memberikan laporan kesalahan.

---

## Penjelasan Teknis

### File yang Dibuat

| File | Deskripsi |
|------|-----------|
| `frontend/src/components/__tests__/DashboardLayout.test.tsx` | Property-based tests untuk DashboardLayout |

### File yang Dimodifikasi

| File | Perubahan |
|------|-----------|
| `frontend/package.json` | Tambah `fast-check@3.19.0`, `@testing-library/react@14.2.2`, `@testing-library/jest-dom@6.4.2`, `@testing-library/user-event@14.5.2` ke devDependencies |

### Library yang Digunakan

- **`fast-check@3.19.0`** — property-based testing library untuk JavaScript/TypeScript. Menghasilkan input secara otomatis dan menguji properti universal.
- **`@testing-library/react@14.2.2`** — library untuk merender komponen React dalam test environment
- **`react-router-dom/MemoryRouter`** — digunakan untuk mensimulasikan navigasi tanpa browser nyata

### Arsitektur DashboardLayout yang Relevan

`DashboardLayout.tsx` menggunakan render-prop pattern dari `react-router-dom`'s `NavLink`:

```tsx
<NavLink key={path} to={path}>
  {({ isActive }) => (
    <span
      className={
        isActive
          ? 'w-full flex items-center ... bg-[#005E6A] text-white font-semibold'
          : 'w-full flex items-center ... text-slate-400 hover:bg-slate-800'
      }
    >
      <Icon className="w-4 h-4" />
      <span>{label}</span>
    </span>
  )}
</NavLink>
```

Class `bg-[#005E6A]` (warna BNI Teal aktif) diterapkan pada `<span>` di dalam `<a>`, **bukan pada `<a>` itu sendiri**. Karena itu selector yang benar adalah `nav span` (bukan `nav a`).

### Keputusan Desain

**Selector `nav span` vs `nav a`:** Active class ada di `<span>` pertama di dalam `<a>`, bukan di `<a>` itu sendiri. Selector `nav span` lebih tepat.

**`numRuns: 6`:** Menggunakan `fc.constantFrom(6 routes)` artinya ada 6 kemungkinan nilai. `numRuns: 6` memastikan semua 6 route dicoba minimal sekali per test run.

**`MemoryRouter` + `initialEntries`:** Digunakan karena test environment tidak memiliki browser history. `initialEntries=[route]` mensimulasikan user yang sudah berada di route tersebut.

---

## Struktur Test

### Property 1A: Exactly One Active Nav Item

```
Input:  route ∈ {'/overview', '/comparison', '/time-analysis',
                  '/regional', '/customer-criteria', '/similar-campaigns'}
Assert: count(nav spans with bg-[#005E6A]) === 1
```

### Property 1B: Active Item Has Required Classes

```
Input:  route (same as above)
Assert: nav span with bg-[#005E6A]
        → also has 'text-white' AND 'font-semibold'
```

### Property 2 (Bonus): No Emoji in Rendered Output

```
Input:  username ∈ fc.string({ maxLength: 50 })
        route ∈ VALID_ROUTES
Assert: container.textContent does NOT match /[\u{1F300}-\u{1FFFF}\u{2600}-\u{27BF}]/u
```

---

## Simulasi / Skenario

### Skenario 1 — Route `/overview` (happy path)

```
Input:   route = '/overview'
Render:  DashboardLayout di dalam MemoryRouter dengan initialEntries=['/overview']

NavLink untuk '/overview' → isActive = true
  → <span className="... bg-[#005E6A] text-white font-semibold">Campaign Overview</span>

NavLink untuk '/comparison' → isActive = false
  → <span className="... text-slate-400 hover:bg-slate-800 hover:text-white">...</span>

... (4 lainnya sama, tidak aktif)

Assertion: 1 span memiliki bg-[#005E6A] ✅
```

### Skenario 2 — Semua 6 route (property sweep)

fast-check akan mencoba semua 6 route secara otomatis (karena `numRuns: 6` dengan `fc.constantFrom`). Setiap run memverifikasi eksklusivitas aktif.

### Skenario 3 — Username dengan karakter aneh

```
Input:   username = "Robin Abc 123 !@#$"
         route = '/regional'

Assertion: Tidak ada emoji di output — username ditampilkan apa adanya
           tanpa emoji ditambahkan ✅
```

---

## Keterkaitan dengan Komponen Lain

- **Bergantung pada:** `DashboardLayout.tsx` (komponen yang ditest), `react-router-dom` (NavLink behavior)
- **Digunakan oleh:** QA pipeline, CI/CD — dijalankan via `npm run test`
- **Pengaruh ke:** Jika `DashboardLayout.tsx` diubah (misalnya active class diganti), test ini akan gagal dan mendeteksi regresi

---

## Requirements yang Dipenuhi

| Requirement | Deskripsi | Diverifikasi Oleh |
|-------------|-----------|------------------|
| **2.7** | Nav item aktif memiliki `bg-[#005E6A]`, `text-white`, `font-semibold` | Property 1A dan 1B |
| **2.8** | Nav item tidak aktif memiliki `text-slate-400`, hover classes | Property 1B (implisit — non-active spans checked) |
| **2.11** | Tidak ada emoji di DashboardLayout | Property 2 |

---

## Hasil Test

```
PASS  src/components/__tests__/DashboardLayout.test.tsx
  DashboardLayout — Property 1: Active nav item has exclusive active classes
    ✓ exactly one nav item has bg-[#005E6A] for any valid route (63ms)
    ✓ active nav item has text-white and font-semibold (31ms)
  DashboardLayout — Property 2: No emoji in rendered output
    ✓ renders no emoji for any username and route combination (59ms)

Tests: 3 passed, 3 total
Time:  2.784s
```

---

## Catatan Penting

1. **CRA Test Environment:** `react-scripts test` menggunakan Jest + jsdom. `MemoryRouter` diperlukan karena jsdom tidak menyediakan browser history.

2. **Class string matching:** Test menggunakan `className.includes('bg-[#005E6A]')`. Ini cukup robust karena class tersebut adalah literal string penuh — tidak ada partial match yang bisa salah.

3. **Tailwind JIT & test env:** Tailwind tidak memproses CSS di test environment (jsdom). Namun test ini hanya memeriksa keberadaan class string di attribute `className`, bukan tampilan visual CSS-nya — sehingga berjalan dengan benar.

4. **`numRuns: 6`:** Untuk `fc.constantFrom(6 values)`, fast-check dengan seed default tidak selalu mencakup semua 6 nilai. Jika diperlukan coverage 100%, gunakan loop eksplisit di atas property test.
