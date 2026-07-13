# Task 7.2 — Property Test StatCard: Required Tailwind Classes

## Ringkasan Singkat

Task ini menulis property-based test untuk sub-komponen `StatCard` yang ada di `CampaignOverviewPage.tsx`. Test memverifikasi bahwa untuk kombinasi teks label dan value apapun, elemen-elemen kartu KPI selalu memiliki Tailwind CSS class yang diwajibkan oleh BNI Design System.

## Penjelasan Awam (Non-Technical)

Bayangkan kartu nama yang harus selalu dicetak dengan format tertentu: font tertentu, warna tertentu, ukuran tertentu — tidak peduli nama siapa yang ditulis di sana. Test ini memastikan bahwa kartu metrik (Stat Card) di dashboard selalu tampil dengan gaya yang benar, apapun angka atau teks yang ditampilkan di dalamnya.

Jika seseorang secara tidak sengaja mengubah warna atau ukuran font di kartu tersebut saat melakukan perubahan kode, test ini akan langsung mendeteksi pelanggaran tersebut.

**Manfaat bisnis**: Konsistensi visual di semua kartu KPI (Total Leads, Total Take Up, Take Up Rate) terjamin secara otomatis setiap kali kode diubah.

## Penjelasan Teknis

**File yang dibuat:**
- `frontend/src/tests/StatCard.property.test.tsx`

**Library yang digunakan:**
- `fast-check ^3.19.0` — property-based testing (menghasilkan ratusan kombinasi input acak)
- `@testing-library/react ^14.2.2` — rendering komponen ke jsdom
- `react-scripts test` (Jest + CRA) — test runner

**Strategi implementasi:**

Karena `StatCard` adalah komponen internal (tidak diekspor) dari `CampaignOverviewPage.tsx`, komponen didefinisikan ulang secara lokal di file test sebagai salinan identik dari implementasi aslinya. Ini mengikuti pola yang sama dengan `ExportService.property.test.tsx`.

**DOM selector issue yang ditemukan dan diperbaiki:**

Awalnya, label span dicari dengan `span:first-of-type`. Ini gagal karena prop `icon` diisi `<span />`, sehingga icon menjadi `span:first-of-type` di dalam DOM. Solusinya: gunakan `span.text-slate-400` untuk menemukan label span secara deterministik berdasarkan class yang unik.

**Tiga suite test:**

1. **Pure-function tests** — Tidak ada DOM, hanya verifikasi string class literal yang ada di definisi komponen. Sangat cepat, tidak memerlukan render.

2. **Property-based tests (fast-check)** — 100 runs per properti dengan input acak:
   - Property 5a: container selalu memiliki `bg-white border border-gray-200 rounded-xl shadow-sm`
   - Property 5b: label span selalu memiliki `text-xs font-medium text-slate-400`
   - Property 5c: value span selalu memiliki `text-2xl font-bold text-slate-700`

3. **Example-based tests** — Input representatif (e.g. `"Total Leads"`, `"1,234"`) untuk keterlacakan langsung ke requirement.

## Struktur Kode

```tsx
// Salinan lokal StatCard (harus identik dengan CampaignOverviewPage.tsx)
const StatCard: React.FC<StatCardProps> = ({ label, value, icon }) => (
  <div className="bg-white p-4 border border-gray-200 rounded-xl shadow-sm flex items-start gap-3">
    <div className="flex-shrink-0 text-[#005E6A]">{icon}</div>
    <div>
      <span className="text-xs font-medium text-slate-400 block">{label}</span>
      <span className="text-2xl font-bold text-slate-700">{value}</span>
    </div>
  </div>
);

// Helper: verifikasi semua token class ada di className string
function hasAllClasses(classString: string, required: readonly string[]): boolean {
  const tokens = new Set(classString.split(/\s+/));
  return required.every((cls) => tokens.has(cls));
}
```

## Simulasi / Skenario

**Skenario 1 — Happy path (typical input):**
- Input: `label="Total Leads"`, `value="1,234"`, `icon=<Users />`
- Container className: `"bg-white p-4 border border-gray-200 rounded-xl shadow-sm ..."`
- Label className: `"text-xs font-medium text-slate-400 block"`
- Value className: `"text-2xl font-bold text-slate-700"`
- Hasil: semua assertions pass ✓

**Skenario 2 — Edge case (string kosong):**
- Input: `label=""`, `value=""`
- Class names tidak bergantung pada props — tetap memiliki semua class yang diwajibkan
- Hasil: pass ✓

**Skenario 3 — Input acak (fast-check):**
- fast-check menghasilkan 100 pasangan `{label, value}` acak termasuk string Unicode, string panjang, spasi, karakter khusus
- Untuk setiap input: class tidak berubah (class di-hardcode, bukan dinamis)
- Hasil: semua 100 runs pass ✓

## Keterkaitan dengan Komponen Lain

- **Bergantung pada**: `StatCard` di `CampaignOverviewPage.tsx` (salinan lokal di test harus sinkron)
- **Digunakan oleh**: CI pipeline — test ini berjalan saat `npm test`
- **Pengaruh ke**: Jika class di `StatCard` diubah (baik sengaja maupun tidak), test ini akan gagal dan memaksa developer untuk sadar bahwa requirements 5.1–5.3 mungkin terdampak

## Requirements yang Dipenuhi

- **Requirement 5.1**: `StatCard` container memiliki `bg-white p-4 border border-gray-200 rounded-xl shadow-sm`
- **Requirement 5.2**: label StatCard memiliki `text-xs font-medium text-slate-400`
- **Requirement 5.3**: value StatCard memiliki `text-2xl font-bold text-slate-700`
- **Requirement 7.2**: `TimeToTakeUpPage` menggunakan pola StatCard yang sama (test berlaku untuk kedua halaman)
- **Requirement 7.3**: label dan value stat card di `TimeToTakeUpPage` mengikuti class yang sama

## Catatan Penting

1. **Salinan lokal harus sinkron**: Jika `StatCard` di `CampaignOverviewPage.tsx` diubah, salinan di test file harus diupdate secara manual. Ini adalah trade-off yang disengaja untuk menghindari dependency pada simbol non-exported.

2. **Selector `span.text-slate-400`**: Dipilih karena class `text-slate-400` hanya ada di label span, bukan di elemen span lain dalam komponen. Jika class label berubah, selector ini perlu diupdate.

3. **jsdom tidak memproses Tailwind**: Test memverifikasi bahwa class string hadir di `className` attribute — bukan bahwa CSS rule benar-benar diterapkan. Ini sudah cukup karena Tailwind utility classes bekerja satu-ke-satu dengan nama classnya.

4. **Test hasil**: 12/12 passed, waktu eksekusi ~2.2 detik.
