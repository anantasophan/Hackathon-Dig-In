# UI Design System — Campaign Insight Generator

Referensi utama: `bni-campaign-engine - new/main_v4a.html`

Semua komponen frontend **harus mengikuti design system ini** untuk konsistensi visual.

---

## Color Palette

| Nama | Hex | Tailwind | Penggunaan |
|------|-----|----------|------------|
| BNI Teal (Primary) | `#005E6A` | `bg-[#005E6A]` | Sidebar aktif, button primary, focus ring, badge |
| BNI Orange (Accent) | `#F15A24` | `text-[#F15A24]` | Accent label, notifikasi badge, branding text |
| Sidebar BG | `#0F172A` (slate-900) | `bg-slate-900` | Sidebar utama |
| Sidebar header | `#020617` (slate-950) | `bg-slate-950` | Header logo sidebar |
| Content BG | `#F8FAFC` (slate-50) | `bg-slate-50` | Area konten utama |
| Card BG | `#FFFFFF` | `bg-white` | Semua card/panel |
| Border default | `#E5E7EB` (gray-200) | `border-gray-200` | Border card |

### Status Colors

| Status | Warna teks | Warna border/bg |
|--------|-----------|-----------------|
| Submitted / Default | `text-slate-700` | `border-gray-200` |
| On Progress / Warning | `text-amber-600` | `border-amber-200` |
| Wait Approval | `text-cyan-700` | `border-amber-300 bg-amber-50` |
| Error / Revision | `text-rose-600` | `border-rose-200` |
| Running / Active | `text-emerald-600` | `border-emerald-200` |
| Done / Success | `text-indigo-600` | `border-indigo-200` |

---

## Typography

- **Font**: `Inter` (Google Fonts) — import di `index.css`
- **Base size**: `text-xs` (12px) mendominasi UI — compact enterprise feel
- **Labels**: `text-xs font-bold uppercase tracking-wider text-gray-600`
- **Headings section**: `text-xs font-bold uppercase tracking-wider text-gray-400`
- **Page title**: `text-md font-bold text-gray-700`
- **Large numbers (stat cards)**: `text-2xl font-bold`

---

## Layout

### Shell Structure

```
body (bg-gray-50, h-screen, flex)
├── <aside> Sidebar (w-64, bg-slate-900, flex-col)
│   ├── Logo header (bg-slate-950, p-5, border-b border-slate-800)
│   ├── User session info (bg-slate-800/50, text-xs)
│   ├── <nav> Menu items (p-4, space-y-1)
│   └── Logout button (p-4, border-t, bg-slate-950)
└── <main> Content area (flex-1, flex-col, bg-slate-50)
    ├── <header> Top bar (h-14, bg-white, border-b, shadow-sm)
    └── <div> View container (flex-1, overflow-y-auto, p-6)
```

### Sidebar Nav Items

```html
<!-- Inactive -->
<button class="w-full flex items-center space-x-3 px-4 py-2.5 rounded-lg 
               text-xs font-medium text-slate-400 hover:bg-slate-800 hover:text-white transition">
  <i data-lucide="icon-name" class="w-4 h-4"></i>
  <span>Label</span>
</button>

<!-- Active -->
<button class="w-full flex items-center space-x-3 px-4 py-2.5 rounded-lg 
               text-xs font-semibold bg-[#005E6A] text-white">
```

---

## Components

### Card

```html
<div class="bg-white p-4 border border-gray-200 rounded-xl shadow-sm">
  <!-- content -->
</div>
```

### Stat Card (Dashboard KPI)

```html
<div class="bg-white p-4 border border-gray-200 rounded-xl shadow-sm">
  <span class="text-xs font-medium text-slate-400 block">Label</span>
  <span class="text-2xl font-bold text-slate-700">42</span>
</div>
```

### Section Heading

```html
<h3 class="text-xs font-bold uppercase tracking-wider text-gray-400 mb-2">
  Section Title
</h3>
```

### Primary Button (Teal)

```html
<button class="px-6 py-2.5 bg-[#005E6A] hover:bg-[#004852] text-white 
               font-semibold rounded-lg transition flex items-center gap-2">
  <i data-lucide="icon" class="w-4 h-4"></i>
  Label
</button>
```

### Secondary Button (Gray)

```html
<button class="px-4 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 
               font-semibold rounded-lg transition">
  Cancel
</button>
```

### Danger Button (Rose)

```html
<button class="flex items-center gap-2 px-4 py-2.5 bg-rose-50 hover:bg-rose-100 
               text-rose-600 font-bold rounded-lg border border-rose-200 text-xs">
  Label
</button>
```

### Form Input

```html
<label class="block font-bold text-gray-600 uppercase mb-1 text-xs">Field Label</label>
<input type="text" 
       class="w-full px-3 py-2 border border-gray-300 rounded-lg 
              focus:outline-none focus:ring-2 focus:ring-[#005E6A] bg-white text-xs">
```

### Badge / Role Tag

```html
<span class="bg-[#005E6A]/40 border border-[#005E6A] text-cyan-300 
             px-1.5 py-0.5 rounded text-[10px] font-medium">
  Role Label
</span>
```

### Toast Notification

Posisi: `fixed bottom-5 right-5`, `max-w-sm`, `space-y-2`

```html
<div class="px-4 py-3 rounded-lg shadow-lg text-white text-xs font-medium 
            flex items-center gap-2 bg-emerald-600">
  ✓ Success message
</div>
```

Toast colors: `bg-emerald-600` (success), `bg-rose-600` (error), `bg-amber-500` (warning), `bg-slate-700` (info)

### Top Header Bar

```html
<header class="h-14 bg-white border-b border-gray-200 flex items-center 
               justify-between px-6 z-30 shadow-sm">
  <h1 class="text-md font-bold text-gray-700 flex items-center space-x-2">
    <i data-lucide="layers" class="w-4 h-4 text-[#005E6A]"></i>
    <span>Page Title</span>
  </h1>
  <!-- right side: notifications, clock, user info -->
</header>
```

---

## Icons

Gunakan **Lucide React** (`lucide-react` package):

```tsx
import { LayoutDashboard, GitCompareArrows, Clock, MapPin, Users, Star } from 'lucide-react';
```

Icon size default: `w-4 h-4` (16px)

Navigation icons yang digunakan di referensi:
- Dashboard: `grid` / `activity`
- Campaign Comparison: `git-compare-arrows`
- Time Analysis: `clock`
- Regional: `map-pin`
- Customer Criteria: `users`
- Similar Campaign: `star` / `search`
- Export: `download`
- Logout: `log-out`

---

## Tailwind Configuration

Install Tailwind CSS dan pastikan `tailwind.config.js` include:

```js
module.exports = {
  theme: {
    extend: {
      colors: {
        'bni-teal': '#005E6A',
        'bni-orange': '#F15A24',
      },
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
      }
    }
  }
}
```

---

## CSS Custom Classes (global `index.css`)

```css
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

body { font-family: 'Inter', sans-serif; }

.bni-orange { color: #F15A24; }
.bg-bni-orange { background-color: #F15A24; }
.bni-teal { color: #005E6A; }
.bg-bni-teal { background-color: #005E6A; }

/* Sticky table headers */
.table-fixed-header th { 
  position: sticky; top: 0; 
  background: #F9FAFB; z-index: 10; 
}

/* Truncate 2 lines */
.truncate-2-lines { 
  display: -webkit-box; 
  -webkit-line-clamp: 2; 
  -webkit-box-orient: vertical; 
  overflow: hidden; 
}
```

---

## Aturan Implementasi

1. **Selalu gunakan Tailwind CSS** untuk semua styling — tidak ada inline style kecuali animasi
2. **Warna BNI Teal** (`#005E6A`) adalah primary action color — gunakan untuk button, sidebar active, focus ring
3. **Warna BNI Orange** (`#F15A24`) hanya untuk accent/branding — jangan digunakan sebagai button
4. **Sidebar selalu dark** (`bg-slate-900`) — tidak boleh terang
5. **Content area** selalu `bg-slate-50` bukan `bg-white`
6. **Cards** selalu `rounded-xl` dengan `shadow-sm border border-gray-200`
7. **Text size** mengutamakan `text-xs` dan `text-sm` — hindari `text-base` atau lebih besar kecuali angka KPI
8. **Label form** selalu `uppercase font-bold text-gray-600`
9. **Semua komponen baru** harus mengikuti pattern yang ada di referensi ini sebelum menambahkan gaya baru

---

## Tone Visual — Enterprise & Profesional

### DILARANG (tidak boleh digunakan):
- **Emoji** — tidak ada 🎉 💡 ✅ ❌ ⚠️ 🔍 📊 atau emoji apapun dalam UI
- **Animated GIF** atau loading spinner yang terlalu mencolok
- **Teks dengan tanda seru berlebihan** — hindari "Success!" "Error!" — cukup "Saved" / "Failed"
- **Warna gradient cerah** (pink, purple, rainbow) — tidak sesuai brand bank
- **Font playful** — hanya Inter
- **Icon kartun** atau ilustrasi bergaya infantil

### HARUS DIGUNAKAN sebagai pengganti:
- **Lucide React icons** untuk semua indikator visual — `CheckCircle`, `AlertCircle`, `XCircle`, `Info`
- **Status text** yang singkat dan formal: `"Berhasil disimpan"`, `"Terjadi kesalahan"`, `"Tidak ada data"`
- **Warna status** yang konsisten (lihat tabel Status Colors di atas) — bukan emoji
- **Divider line** (`border-t border-gray-100`) untuk memisahkan section, bukan dekorasi

### Contoh SALAH vs BENAR:

```
// SALAH — jangan gunakan emoji
<span>✅ Data berhasil disimpan!</span>
<span>⚠️ Ada yang salah nih</span>

// BENAR — gunakan icon Lucide + teks formal
<span class="flex items-center gap-1.5 text-emerald-600">
  <CheckCircle class="w-4 h-4" />
  Data berhasil disimpan
</span>

<span class="flex items-center gap-1.5 text-amber-600">
  <AlertCircle class="w-4 h-4" />
  Perhatian: Beberapa field belum diisi
</span>
```

### Empty State

```tsx
// BENAR — profesional, tanpa ilustrasi atau emoji
<div class="text-center py-12 text-gray-400">
  <InboxIcon class="w-8 h-8 mx-auto mb-2 text-gray-300" />
  <p class="text-sm font-medium">Tidak ada data tersedia</p>
  <p class="text-xs mt-1">Silakan sesuaikan filter untuk menampilkan data</p>
</div>
```
