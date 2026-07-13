# Task 3.1 — DashboardLayout Rewrite: Tailwind CSS & Lucide Icons

## Ringkasan Singkat

Task ini menulis ulang sepenuhnya komponen `DashboardLayout.tsx` — shell utama aplikasi Campaign Insight Generator. Seluruh styling CSS kustom digantikan dengan Tailwind CSS utility classes, dan semua emoji digantikan dengan ikon Lucide React. Hasilnya adalah sidebar gelap bergaya enterprise dengan header logo, informasi sesi pengguna, navigasi berbasis ikon, dan tombol logout.

---

## Penjelasan Awam (Non-Technical)

Bayangkan sebuah kantor dengan pintu masuk yang resmi. Saat Anda masuk, ada **panel navigasi di sebelah kiri** (seperti papan petunjuk di lobi gedung) yang memberi tahu Anda sedang ada di ruang mana dan bisa pergi ke ruang mana. Di bagian atas panel itu ada logo perusahaan dan nama Anda. Di bagian bawahnya ada tombol "Keluar" untuk logout.

Di sebelah kanan adalah **area kerja utama** — tempat semua informasi kampanye ditampilkan tergantung menu mana yang Anda pilih.

Sebelumnya, tampilan ini menggunakan emoji (📊⚖️⏱️) sebagai ikon dan styling CSS manual yang tidak konsisten. Sekarang semua ikon diganti dengan ikon vektor Lucide yang tajam di semua ukuran layar, dan warna mengikuti panduan resmi BNI Design System.

---

## Penjelasan Teknis

### File yang Dimodifikasi

- **`frontend/src/components/DashboardLayout.tsx`** — full rewrite

### File yang Dihapus (Dependency)

- Import `'./DashboardLayout.css'` dihapus dari file komponen ini. File CSS-nya sendiri akan dihapus di task 15.1.

### Library yang Digunakan

- **`lucide-react`** `0.378.0` — ikon SVG: `LayoutGrid`, `GitCompareArrows`, `Clock`, `MapPin`, `Users`, `Search`, `LogOut`
- **`react-router-dom`** — `NavLink` dengan render prop `({ isActive })` untuk mendeteksi halaman aktif
- **Tailwind CSS** `3.4.1` — semua utility classes

### Arsitektur Layout

```
div.h-screen.flex.bg-gray-50.overflow-hidden
├── aside.w-64.bg-slate-900          (Sidebar)
│   ├── div.bg-slate-950             (Logo header)
│   ├── div.bg-slate-800/50          (User session info — conditional)
│   ├── nav.flex-1.p-4              (Navigation links)
│   │   └── NavLink × 6             (per navItems array)
│   └── div.bg-slate-950.border-t   (Logout button — conditional)
└── main.flex-1.flex-col.bg-slate-50 (Content area)
    ├── header.h-14.bg-white         (Top Header Bar)
    └── div.flex-1.overflow-y-auto   (View container for children)
```

### Keputusan Desain Penting

1. **`NavLink` render prop pattern** — digunakan agar class aktif/non-aktif bisa diterapkan pada elemen `<span>` yang membungkus ikon dan label. Ini diperlukan karena Tailwind tidak bisa menggunakan `active:` pseudo-class pada wrapper custom.

2. **`NavItem` interface** menggunakan `Icon: React.ComponentType<{ className?: string }>` — tipe generik ini memungkinkan setiap ikon Lucide dirender sebagai `<Icon className="w-4 h-4 flex-shrink-0" />` tanpa casting.

3. **Tidak ada inline `style={}`** — seluruh styling murni via Tailwind. Tidak ada pengecualian di komponen ini.

4. **Conditional rendering** untuk `username` dan `onSignOut` — prop bersifat opsional sesuai interface yang sudah ada, sehingga komponen tetap valid di konteks tanpa auth.

5. **`flex-shrink-0`** pada sidebar — mencegah sidebar menyusut saat konten area kanan memerlukan lebih banyak ruang.

### Kelas Tailwind Kunci

| Elemen | Class |
|--------|-------|
| Root container | `h-screen flex bg-gray-50 overflow-hidden` |
| Sidebar | `w-64 flex-shrink-0 bg-slate-900 flex flex-col` |
| Logo header | `bg-slate-950 px-5 py-4 border-b border-slate-800` |
| BNI accent label | `text-[10px] text-[#F15A24] font-semibold uppercase tracking-wider` |
| User session | `bg-slate-800/50 px-4 py-2.5` |
| Nav item aktif | `bg-[#005E6A] text-white font-semibold` |
| Nav item non-aktif | `text-slate-400 hover:bg-slate-800 hover:text-white transition-colors` |
| Logout area | `bg-slate-950 p-4 border-t border-slate-800` |
| Content area | `flex-1 flex flex-col bg-slate-50 overflow-hidden` |
| Top Header Bar | `h-14 bg-white border-b border-gray-200 shadow-sm z-30` |
| View container | `flex-1 overflow-y-auto p-6` |

---

## Struktur Kode

```tsx
interface NavItem {
  path: string;
  label: string;
  Icon: React.ComponentType<{ className?: string }>;  // Lucide component ref
}

export interface DashboardLayoutProps {
  children: React.ReactNode;
  username?: string;    // opsional — ditampilkan di user session info
  onSignOut?: () => void; // opsional — jika ada, tampilkan tombol Logout
}

const navItems: NavItem[] = [
  { path: '/overview',          label: 'Campaign Overview',     Icon: LayoutGrid },
  { path: '/comparison',        label: 'Perbandingan Campaign', Icon: GitCompareArrows },
  { path: '/time-analysis',     label: 'Time to Take Up',       Icon: Clock },
  { path: '/regional',          label: 'Performa Regional',     Icon: MapPin },
  { path: '/customer-criteria', label: 'Kriteria Nasabah',      Icon: Users },
  { path: '/similar-campaigns', label: 'Campaign Serupa',       Icon: Search },
];
```

---

## Simulasi / Skenario

### Skenario 1: Pengguna Login, Navigasi ke Overview

**Input**: `username="Budi Santoso"`, `onSignOut={handleLogout}`, halaman saat ini `/overview`

**Output (sidebar)**:
- Logo header: "Campaign Insight Generator" + label aksen "BNI" warna oranye
- User section: "Pengguna" (label abu) + "Budi Santoso" (teks putih)
- Nav item "Campaign Overview": background teal `#005E6A`, teks putih, ikon `LayoutGrid`
- Nav item lain: teks abu `text-slate-400`, background transparan
- Logout button di bawah: teks abu, ikon `LogOut`

### Skenario 2: Pengguna Tanpa Auth (username dan onSignOut tidak disediakan)

**Input**: hanya `children` yang diberikan

**Output**: sidebar tanpa user section dan tanpa tombol Logout. Logo header dan navigasi tetap tampil normal.

### Skenario 3: Hover Nav Item Non-Aktif

**Input**: cursor hover di atas "Performa Regional" (non-aktif)

**Output**: background berubah ke `bg-slate-800`, teks berubah ke `text-white`, transisi smooth via `transition-colors`.

---

## Keterkaitan dengan Komponen Lain

- **Bergantung pada**: `react-router-dom` (NavLink), `lucide-react` (7 ikon)
- **Digunakan oleh**: `App.tsx` atau root router — semua 6 halaman dibungkus oleh komponen ini
- **Pengaruh ke**: Jika `navItems` ditambah/dikurangi, cukup update array di file ini
- **DashboardLayout.css**: sudah tidak diimpor; akan dihapus di task 15.1

---

## Requirements yang Dipenuhi

| Requirement | Deskripsi |
|-------------|-----------|
| 2.1 | Sidebar `bg-slate-900`, `w-64` |
| 2.2 | Logo header `bg-slate-950`, `border-b border-slate-800` |
| 2.3 | User session `bg-slate-800/50`, `text-xs` |
| 2.4 | Logout button `bg-slate-950`, `border-t border-slate-800`, ikon `LogOut` |
| 2.5 | Content area `bg-slate-50` |
| 2.6 | Top Header Bar `h-14 bg-white border-b border-gray-200 shadow-sm` |
| 2.7 | Nav item aktif: `bg-[#005E6A] text-white font-semibold` |
| 2.8 | Nav item non-aktif: `text-slate-400 hover:bg-slate-800 hover:text-white text-xs` |
| 2.9 | Ikon Lucide untuk setiap nav item |
| 2.10 | Tidak menggunakan class dari `DashboardLayout.css` |
| 2.11 | Tidak ada emoji di komponen ini |
| 2.12 | Tidak ada inline `style={}` |

---

## Catatan Penting

- **`flex-shrink-0` pada `<Icon>`**: class `flex-shrink-0` ditambahkan pada setiap ikon nav agar ikon tidak terkompresi saat label teks panjang.
- **`z-30` pada Top Header Bar**: diperlukan agar header tidak tertutup oleh elemen yang di-scroll di bawahnya (misalnya sticky table headers di halaman konten).
- **`overflow-hidden` pada root dan sidebar**: mencegah scroll yang tidak diinginkan pada level shell; scrolling hanya terjadi di dalam `.overflow-y-auto` pada view container.
- **`transition-colors`** (bukan `transition`): lebih efisien — hanya menganimasikan properti warna, bukan semua properti CSS.
- **Todo (task berikutnya)**: Task 3.2 dan 3.3 akan menulis property-based tests untuk memverifikasi eksklusivitas nav item aktif dan ketiadaan emoji.
