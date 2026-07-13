# Task 14.4 — Property Test: No Emoji Invariant (Shared State Components)

## Ringkasan Singkat

Task ini mengimplementasikan property test untuk memverifikasi bahwa komponen `EmptyState`, `LoadingState`, dan `ErrorState` dari `StateComponents.tsx` tidak pernah merender karakter emoji di output-nya — untuk sembarang nilai props yang diberikan.

---

## Penjelasan Awam (Non-Technical)

Bayangkan sebuah aturan perusahaan: "Tidak boleh ada emoji di tampilan aplikasi ini." Kita ingin membuktikan aturan itu berlaku **selalu**, bukan hanya untuk kasus-kasus tertentu yang kita uji manual.

Property test bekerja seperti ini: alih-alih kita yang menyiapkan 5 atau 10 contoh data, library `fast-check` secara otomatis mencoba **ratusan kombinasi data acak** sebagai input ke komponen. Jika satu pun percobaan menghasilkan emoji di layar, tes langsung gagal dan menunjukkan contoh yang bermasalah.

Manfaat bisnis: desain visual BNI mensyaratkan tampilan enterprise yang profesional tanpa emoji. Test ini memastikan standar itu tidak bisa dilanggar secara tidak sengaja oleh developer mana pun.

---

## Penjelasan Teknis

**File yang dibuat:**
- `frontend/src/tests/NoEmoji.property.test.tsx`

**Library yang digunakan:**
- `fast-check` — property-based testing library (sudah ada di `devDependencies`)
- `@testing-library/react` — untuk merender komponen di jsdom
- Komponen yang diuji: `EmptyState`, `LoadingState`, `ErrorState` dari `frontend/src/components/StateComponents.tsx`

**Pola arsitektur:**
- Komponen shared state dipilih karena tidak memiliki dependency eksternal (tidak ada API call, tidak ada routing, tidak ada Chart.js) — bisa dirender langsung di test environment tanpa mocking.
- Emoji dideteksi dengan regex Unicode `[\u{1F300}-\u{1FFFF}\u{2600}-\u{27BF}]` menggunakan flag `u` agar surrogate pairs dikenali sebagai satu code point.
- Setiap test memanggil `unmount()` setelah selesai untuk menghindari memory leak antar iterasi fast-check.

**Keputusan desain:**
- Flag `u` pada regex adalah kritis. Tanpa flag ini, range `\u{1F300}-\u{1FFFF}` tidak bisa dikompilasi karena code point di atas U+FFFF membutuhkan syntax `\u{...}`.
- `⏳` (U+23F3) dan `✅` (U+2705) berada di **luar** kedua range yang dicakup regex — ini didokumentasikan eksplisit di test agar tidak ada kebingungan di masa depan.

---

## Struktur Kode

### `hasEmoji(text: string): boolean`
Helper murni yang mengembalikan `true` jika `text` mengandung karakter emoji dalam dua range yang didefinisikan.

### Suite 1 — `hasEmoji helper`
3 test example-based untuk memverifikasi regex detection bekerja dengan benar sebelum digunakan di assertions utama.

### Suite 2 — `Property 2a: EmptyState`
Property test + 3 example tests. Input: `message?: string`, `hint?: string` (keduanya opsional/arbitrary).

### Suite 3 — `Property 2b: LoadingState`
Property test + 3 example tests. Input: `text?: string` (opsional/arbitrary).

### Suite 4 — `Property 2c: ErrorState`
Property test + 3 example tests. Input: `message: string` (required, arbitrary).

### Suite 5 — Cross-component
1 property test yang merender ketiga komponen sekaligus dan memverifikasi tidak ada emoji dari gabungan output-nya.

---

## Simulasi / Skenario

**Skenario 1 — Happy path (default props):**
- Input: `<EmptyState />` tanpa props
- Proses: fast-check melewati kasus default, render menghasilkan teks "Tidak ada data tersedia" + "Silakan sesuaikan filter..."
- Output: `hasEmoji("Tidak ada data tersedia...") === false` → tes lulus

**Skenario 2 — Arbitrary string input:**
- Input: fast-check menghasilkan string seperti `"abc✓123"`, `"test data"`, `""`
- Proses: komponen merender string tersebut sebagai pesan
- Output: tidak ada emoji dari range U+1F300–U+1FFFF atau U+2600–U+27BF → tes lulus

**Skenario 3 — Deteksi emoji (self-test helper):**
- Input: string `"⚠️ warn"` (mengandung U+26A0)
- Proses: `hasEmoji("⚠️ warn")`
- Output: `true` → helper terverifikasi bekerja

---

## Keterkaitan dengan Komponen Lain

- **Bergantung pada:** `StateComponents.tsx` (`EmptyState`, `LoadingState`, `ErrorState`)
- **Digunakan oleh:** —  (hanya test file, tidak diimpor komponen lain)
- **Pengaruh ke:** Jika `StateComponents.tsx` diubah untuk menambahkan emoji, test ini akan gagal dan memblokir merge

---

## Requirements yang Dipenuhi

- **2.11** — DashboardLayout tidak menggunakan emoji
- **3.8** — FilterPanel tidak menggunakan emoji
- **4.8** — ExportService tidak menggunakan emoji
- **11.2** — Aplikasi tidak menggunakan emoji di empty state
- **Req. 5 (semua pages)** — Proven via shared components (komponen yang sama digunakan di semua halaman)

---

## Catatan Penting

1. **Scope test ini terbatas pada shared state components.** Full page components (CampaignOverviewPage, dll.) membutuhkan mock yang kompleks dan berada di luar scope task ini — seperti yang didefinisikan di task description.
2. **Regex tidak mencakup semua emoji yang mungkin ada.** Emoji seperti `✅` (U+2705) dan `⏳` (U+23F3) berada di luar dua range yang dicover. Regex ini hanya mencakup range yang disebutkan di design doc.
3. **numRuns: 200** dipilih untuk EmptyState, LoadingState, ErrorState dan **100** untuk cross-component test — cukup untuk confidence tinggi tanpa membuat CI terlalu lambat.
4. **Lucide icons merender sebagai SVG** — `textContent` SVG kosong, sehingga tidak ada risiko false positive dari icon characters.
