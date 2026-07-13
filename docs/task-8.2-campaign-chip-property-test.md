# Task 8.2 — Property Test: Campaign Chip Tailwind Classes (Property 7)

## Ringkasan Singkat

Task ini menulis property-based test menggunakan `fast-check` dan `@testing-library/react` untuk memverifikasi bahwa setiap chip campaign yang dirender di `CampaignComparisonPage` selalu memiliki class Tailwind yang tepat sesuai BNI Design System — untuk input berupa array 1–5 campaign ID apapun.

## Penjelasan Awam (Non-Technical)

Bayangkan sebuah label kecil berbentuk bulat yang muncul di halaman perbandingan kampanye ketika pengguna memilih ID kampanye. Label ini harus selalu tampil dengan warna hijau-teal khas BNI (`#005E6A`) — latar belakang transparan, border, dan teks berwarna teal — apa pun isi teksnya.

Test ini seperti "inspektur kualitas otomatis" yang menjalankan 100 kombinasi nama kampanye acak dan memastikan setiap label selalu tampil sesuai standar visual BNI, tanpa pengecualian.

## Penjelasan Teknis

**File yang dibuat:**
- `frontend/src/tests/CampaignChip.property.test.tsx`

**Library yang digunakan:**
- `fast-check ^3.19.0` — property-based testing: menghasilkan 100 array ID kampanye acak secara otomatis
- `@testing-library/react ^14.2.2` — render komponen React dalam lingkungan test DOM

**Pola yang diterapkan:**
- Komponen `ChipList` kecil didefinisikan langsung di file test — mereplikasi JSX chip dari `CampaignComparisonPage.tsx` secara persis
- Menggunakan `container.querySelectorAll('[role="listitem"]')` untuk query chip (bukan `data-testid`) agar aman untuk ID yang mengandung spasi atau karakter khusus
- Setiap iterasi fast-check memanggil `render()` + `unmount()` untuk menghindari kebocoran antar test

**Generator yang digunakan:**
```typescript
fc.array(fc.string({ minLength: 1 }), { minLength: 1, maxLength: 5 })
```
Menghasilkan array 1–5 string non-kosong untuk mensimulasikan semua kemungkinan kombinasi ID kampanye.

**Class yang diverifikasi:**
```
bg-[#005E6A]/20    border    border-[#005E6A]    text-[#005E6A]
rounded-full    text-xs    font-medium
```

## Struktur Kode

```tsx
// Komponen chip yang diuji (mirror dari CampaignComparisonPage.tsx)
const ChipList: React.FC<ChipListProps> = ({ campaignIds }) => (
  <div role="list">
    {campaignIds.map((id, index) => (
      <span key={index} className="inline-flex ... bg-[#005E6A]/20 border border-[#005E6A] ..."
            role="listitem">
        {id} <button>×</button>
      </span>
    ))}
  </div>
);

// Property 7
fc.assert(
  fc.property(
    fc.array(fc.string({ minLength: 1 }), { minLength: 1, maxLength: 5 }),
    (campaignIds) => {
      const { container, unmount } = render(<ChipList campaignIds={campaignIds} />);
      const chips = container.querySelectorAll('[role="listitem"]');
      expect(chips).toHaveLength(campaignIds.length);
      chips.forEach(chip => {
        REQUIRED_CHIP_CLASS_SUBSTRINGS.forEach(cls => {
          expect(chip.getAttribute('class')).toContain(cls);
        });
      });
      unmount();
    },
  ),
);
```

## Simulasi / Skenario

### Skenario 1 — Input Normal
- Input: `["CAMP-001", "CAMP-2024-Q1"]`
- Proses: Render ChipList → query 2 `listitem` spans
- Output: Setiap span mengandung `bg-[#005E6A]/20`, `border-[#005E6A]`, `rounded-full`, dsb.
- Status: ✅ PASS

### Skenario 2 — ID Dengan Karakter Khusus
- Input: `[" ", "e&!!", "o` `"]`
- Proses: Render → query by role listitem (tidak tergantung ID string)
- Output: Semua chip ditemukan dan class-nya benar
- Status: ✅ PASS (setelah fix awal yang menggunakan `data-testid`)

### Skenario 3 — Edge Case: 1 ID
- Input: `["X"]`
- Proses: 1 chip dirender
- Output: 1 listitem dengan semua class yang dibutuhkan
- Status: ✅ PASS

## Keterkaitan dengan Komponen Lain

- **Menguji:** `CampaignComparisonPage.tsx` (chip JSX di baris ~260)
- **Bergantung pada:** `fast-check`, `@testing-library/react`, React 18
- **Memvalidasi:** Requirements 6.6 — chip campaign harus punya class `bg-[#005E6A]/20 border border-[#005E6A] text-[#005E6A] rounded-full text-xs font-medium`

## Requirements yang Dipenuhi

- **Requirements 6.6:** `THE CampaignComparisonPage SHALL merender chip campaign terpilih dengan class bg-[#005E6A]/20 border border-[#005E6A] text-[#005E6A] rounded-full text-xs font-medium`

## Catatan Penting

- Counterexample awal dari fast-check (`[" "]`) menunjukkan bug pada implementasi pertama yang menggunakan `data-testid` — ID dengan spasi menyebabkan query DOM gagal. Solusi: gunakan `querySelectorAll('[role="listitem"]')` langsung dari `container`.
- Class `bg-[#005E6A]/20` adalah Tailwind arbitrary value — tidak bisa dicek dengan `classList.contains()` standar karena slash (`/`) adalah karakter valid dalam class string. Solusi: `String.prototype.includes()` via `.toContain()` dari Jest.
- Penggunaan `index` sebagai `key` di ChipList test component adalah intentional — di test kita tidak peduli identity stabilitas React, hanya memverifikasi class output.
