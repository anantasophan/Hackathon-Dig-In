# Requirements Document

## Introduction

Fitur ini adalah refactor menyeluruh seluruh antarmuka pengguna (frontend) aplikasi Campaign Insight Generator agar sesuai dengan BNI Design System yang telah didefinisikan di steering file `ui-design-system.md`. UI saat ini menggunakan emoji sebagai ikon, custom CSS biasa (non-Tailwind), dan palet warna yang tidak sesuai brand BNI. Refactor mencakup instalasi Tailwind CSS dan Lucide React, konversi semua styling ke Tailwind utility classes, penggantian emoji dengan Lucide icons, dan penerapan konsisten komponen (Card, Stat Card, Sidebar dark, Button variants, Badge, Toast, Top Header Bar) di seluruh 9 halaman dan 3 komponen bersama.

---

## Glossary

- **BNI Design System**: Panduan visual resmi yang didefinisikan di `.kiro/steering/ui-design-system.md`, meliputi warna, tipografi, layout, dan pola komponen.
- **BNI Teal**: Warna primer `#005E6A` — digunakan untuk button primary, sidebar item aktif, dan focus ring.
- **BNI Orange**: Warna aksen `#F15A24` — digunakan hanya untuk label aksen dan branding, bukan sebagai warna button.
- **Tailwind CSS**: Framework CSS utility-first yang menjadi satu-satunya metode styling dalam aplikasi setelah refactor.
- **Lucide React**: Library ikon berbasis SVG (`lucide-react`) yang menggantikan seluruh penggunaan emoji di UI.
- **DashboardLayout**: Komponen shell utama yang merender sidebar, header, dan area konten.
- **FilterPanel**: Komponen filter bersama yang digunakan di beberapa halaman.
- **ExportService**: Komponen tombol ekspor dengan notifikasi toast.
- **Stat_Card**: Komponen kartu KPI untuk menampilkan angka metrik besar.
- **Toast**: Komponen notifikasi sementara yang muncul di pojok bawah kanan layar.
- **Top_Header_Bar**: Header horizontal di bagian atas area konten dengan judul halaman.
- **Inline Style**: Penulisan styling langsung via atribut `style={}` pada elemen React — dilarang dalam desain baru.
- **Empty State**: Tampilan ketika tidak ada data yang tersedia untuk ditampilkan.
- **Loading State**: Tampilan saat data sedang dimuat dari API.

---

## Requirements

### Requirement 1: Instalasi dan Konfigurasi Dependensi

**User Story:** Sebagai developer, saya ingin Tailwind CSS dan Lucide React tersedia di project frontend, sehingga semua komponen dapat dibangun menggunakan design system BNI tanpa memerlukan library styling lain.

#### Acceptance Criteria

1. THE Frontend_Project SHALL menyertakan `tailwindcss` versi `3.4.1` sebagai dependency di `frontend/package.json`.
2. THE Frontend_Project SHALL menyertakan `lucide-react` versi `0.378.0` sebagai dependency di `frontend/package.json`.
3. THE Frontend_Project SHALL menyertakan `autoprefixer` versi `10.4.19` dan `postcss` versi `8.4.38` sebagai devDependency di `frontend/package.json`.
4. WHEN `frontend/tailwind.config.js` dibaca, THE Tailwind_Config SHALL mendefinisikan custom color `bni-teal` dengan nilai `#005E6A`.
5. WHEN `frontend/tailwind.config.js` dibaca, THE Tailwind_Config SHALL mendefinisikan custom color `bni-orange` dengan nilai `#F15A24`.
6. WHEN `frontend/tailwind.config.js` dibaca, THE Tailwind_Config SHALL mendefinisikan font family `sans` sebagai `['Inter', 'sans-serif']`.
7. THE `frontend/tailwind.config.js` SHALL menyertakan path `./src/**/*.{ts,tsx}` pada field `content` untuk purging CSS yang tidak terpakai.
8. THE `frontend/src/index.css` SHALL mengimpor font Inter dari Google Fonts dengan weights 300, 400, 500, 600, dan 700.
9. THE `frontend/src/index.css` SHALL mendefinisikan class utility `.bni-teal`, `.bg-bni-teal`, `.bni-orange`, dan `.bg-bni-orange`.
10. THE `frontend/src/index.css` SHALL mendefinisikan class `.table-fixed-header th` dengan `position: sticky` dan `z-index: 10` untuk sticky table headers.
11. THE `frontend/src/index.css` SHALL mendefinisikan class `.truncate-2-lines` untuk teks yang dipotong setelah 2 baris.

---

### Requirement 2: Refactor DashboardLayout — Shell Utama

**User Story:** Sebagai pengguna, saya ingin shell aplikasi memiliki tampilan enterprise yang konsisten dengan sidebar gelap dan header yang bersih, sehingga navigasi terasa profesional dan sesuai brand BNI.

#### Acceptance Criteria

1. THE DashboardLayout SHALL merender sidebar dengan background `bg-slate-900` dan lebar `w-64`.
2. THE DashboardLayout SHALL merender bagian logo/header sidebar dengan background `bg-slate-950` dan border bawah `border-b border-slate-800`.
3. THE DashboardLayout SHALL menampilkan informasi sesi pengguna di sidebar dengan background `bg-slate-800/50` dan ukuran teks `text-xs`.
4. THE DashboardLayout SHALL merender tombol Logout di bagian bawah sidebar dengan background `bg-slate-950`, border atas `border-t border-slate-800`, dan ikon `LogOut` dari Lucide React.
5. THE DashboardLayout SHALL merender area konten utama dengan background `bg-slate-50`.
6. THE DashboardLayout SHALL merender Top Header Bar dengan height `h-14`, background `bg-white`, border bawah `border-b border-gray-200`, dan `shadow-sm`.
7. WHEN sebuah item navigasi dalam keadaan aktif (halaman saat ini), THE DashboardLayout SHALL menampilkan item tersebut dengan background `bg-[#005E6A]`, teks `text-white`, dan `font-semibold`.
8. WHEN sebuah item navigasi dalam keadaan tidak aktif, THE DashboardLayout SHALL menampilkan item tersebut dengan teks `text-slate-400`, hover `hover:bg-slate-800 hover:text-white`, dan ukuran teks `text-xs`.
9. THE DashboardLayout SHALL menggunakan ikon Lucide React untuk setiap item navigasi: `LayoutGrid` untuk Campaign Overview, `GitCompareArrows` untuk Perbandingan Campaign, `Clock` untuk Time to Take Up, `MapPin` untuk Performa Regional, `Users` untuk Kriteria Nasabah, dan `Search` untuk Campaign Serupa.
10. IF file `DashboardLayout.css` ada setelah refactor selesai, THEN THE DashboardLayout SHALL tidak menggunakan class CSS dari file tersebut — seluruh styling harus via Tailwind utility classes.
11. THE DashboardLayout SHALL tidak menggunakan emoji di manapun dalam komponen ini.
12. THE DashboardLayout SHALL tidak menggunakan atribut `style={}` (inline styles) pada elemen apapun, kecuali untuk nilai animasi yang tidak bisa diekspresikan via Tailwind.

---

### Requirement 3: Refactor FilterPanel — Panel Filter Bersama

**User Story:** Sebagai pengguna, saya ingin panel filter memiliki tampilan yang konsisten dengan design system BNI, sehingga kontrol filter mudah dibaca dan digunakan.

#### Acceptance Criteria

1. THE FilterPanel SHALL merender seluruh styling menggunakan Tailwind CSS utility classes tanpa menggunakan file `FilterPanel.css`.
2. THE FilterPanel SHALL menampilkan label fieldset dengan class `text-xs font-bold uppercase tracking-wider text-gray-600`.
3. THE FilterPanel SHALL merender tombol Collapse/Expand dengan ikon Lucide React (`ChevronUp` untuk collapse, `ChevronDown` untuk expand) — bukan karakter teks `▼` atau `▲`.
4. THE FilterPanel SHALL merender tombol Apply dengan class `bg-[#005E6A] hover:bg-[#004852] text-white font-semibold rounded-lg`.
5. THE FilterPanel SHALL merender tombol Reset dengan class `bg-gray-100 hover:bg-gray-200 text-gray-700 font-semibold rounded-lg`.
6. THE FilterPanel SHALL merender input teks dan date dengan class `border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#005E6A] text-xs`.
7. THE FilterPanel SHALL merender container panel dengan class `bg-white border border-gray-200 rounded-xl shadow-sm`.
8. THE FilterPanel SHALL tidak menggunakan emoji di manapun dalam komponen ini.

---

### Requirement 4: Refactor ExportService — Tombol Ekspor dengan Toast

**User Story:** Sebagai pengguna, saya ingin komponen ekspor menampilkan notifikasi status yang profesional menggunakan Lucide icons, sehingga umpan balik status ekspor jelas dan konsisten dengan design system.

#### Acceptance Criteria

1. THE ExportService SHALL merender tombol Export dengan ikon `Download` dari Lucide React — bukan emoji `📥`.
2. WHEN status ekspor sedang berjalan, THE ExportService SHALL menampilkan ikon `Loader2` berputar dari Lucide React — bukan emoji `⏳`.
3. WHEN toast bertipe success muncul, THE ExportService SHALL menampilkan ikon `CheckCircle` dari Lucide React dengan warna `text-white`, dan background toast `bg-emerald-600` — bukan string `✅`.
4. WHEN toast bertipe warning muncul, THE ExportService SHALL menampilkan ikon `AlertCircle` dari Lucide React dengan background toast `bg-amber-500` — bukan emoji `⚠️`.
5. WHEN toast bertipe error muncul, THE ExportService SHALL menampilkan ikon `XCircle` dari Lucide React dengan background toast `bg-rose-600` — bukan emoji `❌`.
6. THE ExportService SHALL merender toast di posisi `fixed bottom-5 right-5` dengan lebar maksimal `max-w-sm` dan ukuran teks `text-xs`.
7. THE ExportService SHALL merender tombol dismiss toast menggunakan ikon `X` dari Lucide React — bukan karakter `✕`.
8. THE ExportService SHALL tidak menggunakan emoji di manapun dalam komponen ini.
9. THE ExportService SHALL merender seluruh styling menggunakan Tailwind CSS utility classes tanpa menggunakan file `ExportService.css`.
10. THE ExportService SHALL menampilkan pesan toast yang formal tanpa tanda seru berlebih: `"File siap diunduh"` (bukan `"File siap diunduh!"`), `"Ekspor gagal"`, `"Ekspor timeout"`.

---

### Requirement 5: Refactor CampaignOverviewPage

**User Story:** Sebagai analis kampanye, saya ingin halaman Campaign Overview menggunakan Stat Cards dan tampilan yang bersih sesuai design system BNI, sehingga metrik KPI mudah dibaca secara sekilas.

#### Acceptance Criteria

1. THE CampaignOverviewPage SHALL merender tiga Stat Cards (Total Leads, Total Take Up, Take Up Rate) menggunakan class `bg-white p-4 border border-gray-200 rounded-xl shadow-sm`.
2. THE CampaignOverviewPage SHALL merender label Stat Card dengan class `text-xs font-medium text-slate-400`.
3. THE CampaignOverviewPage SHALL merender nilai angka Stat Card dengan class `text-2xl font-bold text-slate-700`.
4. THE CampaignOverviewPage SHALL menggunakan ikon Lucide React (`Users`, `TrendingUp`, `BarChart2`) untuk setiap Stat Card — bukan emoji `👥`, `✅`, `📈`.
5. WHEN data berhasil dimuat dan response time kurang dari 5000ms, THE CampaignOverviewPage SHALL menampilkan badge response time menggunakan ikon `CheckCircle` dari Lucide React dan warna `text-emerald-600` — bukan karakter `✓ <5s`.
6. WHEN data berhasil dimuat dan response time lebih dari atau sama dengan 5000ms, THE CampaignOverviewPage SHALL menampilkan badge response time menggunakan ikon `AlertCircle` dari Lucide React dan warna `text-amber-600`.
7. WHEN terjadi error saat memuat data, THE CampaignOverviewPage SHALL menampilkan ikon `AlertCircle` dari Lucide React dengan class `text-rose-600` — bukan emoji `⚠️`.
8. WHEN tidak ada data yang cocok dengan filter, THE CampaignOverviewPage SHALL menampilkan ikon `Inbox` dari Lucide React dengan class `text-gray-300` — bukan emoji `📭`.
9. THE CampaignOverviewPage SHALL merender Top Header Bar menggunakan komponen atau pola yang sesuai dengan spesifikasi `Top_Header_Bar` di design system (height `h-14`, background `bg-white`, judul dengan ikon Lucide).
10. THE CampaignOverviewPage SHALL merender seluruh styling menggunakan Tailwind CSS utility classes tanpa menggunakan file `CampaignOverviewPage.css`.
11. THE CampaignOverviewPage SHALL tidak menggunakan inline styles kecuali untuk konfigurasi Chart.js yang tidak bisa diekspresikan via Tailwind.

---

### Requirement 6: Refactor CampaignComparisonPage

**User Story:** Sebagai analis kampanye, saya ingin halaman Perbandingan Campaign menggunakan Tailwind CSS dan Lucide icons, menggantikan inline styles yang saat ini mendominasi komponen ini.

#### Acceptance Criteria

1. THE CampaignComparisonPage SHALL merender seluruh layout dan styling menggunakan Tailwind CSS utility classes — menghapus objek `styles` berupa inline `React.CSSProperties` yang saat ini digunakan.
2. THE CampaignComparisonPage SHALL merender card input campaign dengan class `bg-white p-4 border border-gray-200 rounded-xl shadow-sm`.
3. THE CampaignComparisonPage SHALL merender tombol Tambah (add campaign) dengan class `bg-[#005E6A] hover:bg-[#004852] text-white font-semibold rounded-lg text-xs`.
4. THE CampaignComparisonPage SHALL merender tombol Bandingkan dengan class `bg-[#005E6A] hover:bg-[#004852] text-white font-semibold rounded-lg`.
5. WHEN tombol Tambah atau Bandingkan dalam keadaan disabled, THE CampaignComparisonPage SHALL merender tombol tersebut dengan class `bg-gray-300 cursor-not-allowed text-gray-500`.
6. THE CampaignComparisonPage SHALL merender chip campaign terpilih dengan class `bg-[#005E6A]/20 border border-[#005E6A] text-[#005E6A] rounded-full text-xs font-medium`.
7. THE CampaignComparisonPage SHALL merender header tabel dengan class `bg-slate-900 text-white text-xs font-semibold`.
8. WHEN loading data, THE CampaignComparisonPage SHALL menampilkan spinner menggunakan ikon `Loader2` dari Lucide React dengan animasi `animate-spin` dari Tailwind — bukan menggunakan `@keyframes spin` inline.
9. WHEN terjadi error, THE CampaignComparisonPage SHALL menampilkan ikon `AlertCircle` dari Lucide React dengan class `text-rose-600`.
10. THE CampaignComparisonPage SHALL tidak menggunakan atribut `style={}` (inline styles) pada elemen apapun, kecuali untuk konfigurasi Chart.js.
11. THE CampaignComparisonPage SHALL tidak menggunakan emoji di manapun dalam komponen ini.

---

### Requirement 7: Refactor TimeToTakeUpPage

**User Story:** Sebagai analis kampanye, saya ingin halaman Time to Take Up menggunakan design system BNI secara konsisten, sehingga visualisasi distribusi waktu konversi terlihat profesional.

#### Acceptance Criteria

1. THE TimeToTakeUpPage SHALL merender seluruh styling menggunakan Tailwind CSS utility classes tanpa menggunakan file `TimeToTakeUpPage.css`.
2. THE TimeToTakeUpPage SHALL merender card statistik (rata-rata hari, median hari) menggunakan pola Stat Card dengan class `bg-white p-4 border border-gray-200 rounded-xl shadow-sm`.
3. THE TimeToTakeUpPage SHALL merender label statistik dengan class `text-xs font-medium text-slate-400` dan nilai dengan class `text-2xl font-bold text-slate-700`.
4. THE TimeToTakeUpPage SHALL menggunakan ikon Lucide React (`Clock`, `Timer`) untuk stat cards — bukan emoji.
5. WHEN terjadi error, THE TimeToTakeUpPage SHALL menampilkan ikon `AlertCircle` dari Lucide React dengan class `text-rose-600` — bukan emoji.
6. WHEN tidak ada data, THE TimeToTakeUpPage SHALL menampilkan ikon `Inbox` dari Lucide React dengan class `text-gray-300` — bukan emoji.
7. THE TimeToTakeUpPage SHALL tidak menggunakan inline styles kecuali untuk konfigurasi Chart.js.
8. THE TimeToTakeUpPage SHALL tidak menggunakan emoji di manapun dalam komponen ini.

---

### Requirement 8: Refactor RegionalPerformancePage

**User Story:** Sebagai analis regional, saya ingin halaman Performa Regional menggunakan Tailwind CSS dan Lucide icons, menggantikan seluruh inline styles yang saat ini mendominasi halaman ini.

#### Acceptance Criteria

1. THE RegionalPerformancePage SHALL merender seluruh layout dan styling menggunakan Tailwind CSS utility classes — menghapus objek `styles` berupa `React.CSSProperties` yang saat ini digunakan.
2. THE RegionalPerformancePage SHALL merender card filter dengan class `bg-white p-4 border border-gray-200 rounded-xl shadow-sm`.
3. THE RegionalPerformancePage SHALL merender tombol Cari dengan class `bg-[#005E6A] hover:bg-[#004852] text-white font-semibold rounded-lg`.
4. THE RegionalPerformancePage SHALL merender label form dengan class `text-xs font-bold uppercase tracking-wider text-gray-600`.
5. THE RegionalPerformancePage SHALL merender badge take-up rate tinggi (≥10%) dengan class `bg-emerald-100 text-emerald-700 rounded px-1.5 py-0.5 text-xs font-semibold`.
6. THE RegionalPerformancePage SHALL merender badge take-up rate sedang (5–9.99%) dengan class `bg-amber-100 text-amber-700 rounded px-1.5 py-0.5 text-xs font-semibold`.
7. THE RegionalPerformancePage SHALL merender badge take-up rate rendah (<5%) dengan class `bg-rose-100 text-rose-700 rounded px-1.5 py-0.5 text-xs font-semibold`.
8. WHEN loading, THE RegionalPerformancePage SHALL menggunakan ikon `Loader2` dari Lucide React dengan `animate-spin` — bukan spinner CSS inline.
9. WHEN idle (belum ada pencarian), THE RegionalPerformancePage SHALL menggunakan ikon `MapPin` dari Lucide React — bukan emoji `🗺️`.
10. WHEN tidak ada data regional, THE RegionalPerformancePage SHALL menggunakan ikon `Inbox` dari Lucide React — bukan emoji `📭`.
11. WHEN terjadi error, THE RegionalPerformancePage SHALL menggunakan ikon `AlertCircle` dari Lucide React — bukan emoji `⚠️`.
12. THE RegionalPerformancePage SHALL tidak menggunakan atribut `style={}` (inline styles) pada elemen apapun, kecuali untuk konfigurasi Chart.js.
13. THE RegionalPerformancePage SHALL tidak menggunakan emoji di manapun dalam komponen ini.

---

### Requirement 9: Refactor CustomerCriteriaPage

**User Story:** Sebagai analis data nasabah, saya ingin halaman Kriteria Nasabah menggunakan design system BNI secara konsisten, sehingga tabel dan visualisasi distribusi segmen terlihat profesional.

#### Acceptance Criteria

1. THE CustomerCriteriaPage SHALL merender seluruh styling menggunakan Tailwind CSS utility classes tanpa menggunakan file `CustomerCriteriaPage.css`.
2. THE CustomerCriteriaPage SHALL merender card wrapper tabel dengan class `bg-white border border-gray-200 rounded-xl shadow-sm`.
3. THE CustomerCriteriaPage SHALL merender section heading dengan class `text-xs font-bold uppercase tracking-wider text-gray-400`.
4. THE CustomerCriteriaPage SHALL menggunakan ikon Lucide React (`Users`, `Filter`) untuk elemen visual — bukan emoji.
5. WHEN terjadi error, THE CustomerCriteriaPage SHALL menggunakan ikon `AlertCircle` dari Lucide React dengan class `text-rose-600` — bukan emoji.
6. WHEN tidak ada data, THE CustomerCriteriaPage SHALL menggunakan ikon `Inbox` dari Lucide React — bukan emoji.
7. THE CustomerCriteriaPage SHALL tidak menggunakan inline styles kecuali untuk konfigurasi Chart.js.
8. THE CustomerCriteriaPage SHALL tidak menggunakan emoji di manapun dalam komponen ini.

---

### Requirement 10: Refactor SimilarCampaignPage

**User Story:** Sebagai manajer kampanye, saya ingin halaman Campaign Serupa menggunakan design system BNI secara konsisten, sehingga daftar rekomendasi campaign serupa terlihat bersih dan profesional.

#### Acceptance Criteria

1. THE SimilarCampaignPage SHALL merender seluruh styling menggunakan Tailwind CSS utility classes tanpa menggunakan file `SimilarCampaignPage.css`.
2. THE SimilarCampaignPage SHALL merender card setiap campaign serupa dengan class `bg-white p-4 border border-gray-200 rounded-xl shadow-sm hover:shadow-md transition`.
3. THE SimilarCampaignPage SHALL merender similarity score badge dengan class `bg-[#005E6A]/20 border border-[#005E6A] text-[#005E6A] text-xs font-semibold rounded px-1.5 py-0.5`.
4. THE SimilarCampaignPage SHALL menggunakan ikon Lucide React (`Search`, `Star`, `TrendingUp`) untuk elemen visual — bukan emoji.
5. WHEN terjadi error, THE SimilarCampaignPage SHALL menggunakan ikon `AlertCircle` dari Lucide React dengan class `text-rose-600` — bukan emoji.
6. WHEN tidak ada campaign serupa yang ditemukan, THE SimilarCampaignPage SHALL menggunakan ikon `SearchX` dari Lucide React — bukan emoji.
7. THE SimilarCampaignPage SHALL tidak menggunakan inline styles pada elemen apapun.
8. THE SimilarCampaignPage SHALL tidak menggunakan emoji di manapun dalam komponen ini.

---

### Requirement 11: Konsistensi Pola Empty State dan Loading State

**User Story:** Sebagai pengguna, saya ingin semua halaman menampilkan tampilan kosong dan loading yang seragam, sehingga pengalaman pengguna konsisten di seluruh aplikasi.

#### Acceptance Criteria

1. THE Application SHALL menampilkan empty state di semua halaman dengan pola `text-center py-12 text-gray-400` yang berisi ikon Lucide berukuran `w-8 h-8 text-gray-300`, diikuti teks `text-sm font-medium` dan sub-teks `text-xs`.
2. THE Application SHALL tidak menggunakan emoji manapun sebagai pengganti ikon pada empty state di seluruh halaman.
3. THE Application SHALL menampilkan loading state di semua halaman menggunakan ikon `Loader2` dari Lucide React dengan class `animate-spin text-[#005E6A]` — bukan div spinner CSS custom.
4. WHEN error terjadi di halaman manapun, THE Application SHALL menampilkan ikon `AlertCircle` dari Lucide React dengan class `text-rose-600`.
5. THE Application SHALL menggunakan teks status yang singkat dan formal di semua halaman: `"Tidak ada data tersedia"`, `"Terjadi kesalahan"`, `"Memuat data"` — tanpa tanda seru dan tanpa emoji.

---

### Requirement 12: Konsistensi Tipografi dan Ukuran Teks

**User Story:** Sebagai pengguna, saya ingin semua teks dalam aplikasi menggunakan font Inter dengan ukuran yang konsisten, sehingga UI terasa compact dan profesional sesuai standar enterprise.

#### Acceptance Criteria

1. THE Application SHALL menggunakan font Inter sebagai font utama di seluruh aplikasi melalui import Google Fonts di `index.css`.
2. THE Application SHALL menggunakan `text-xs` (12px) sebagai ukuran teks dominan untuk label, badge, tabel, dan form input — bukan `text-base` (16px) atau lebih besar.
3. THE Application SHALL menggunakan `text-sm` (14px) untuk teks konten sekunder seperti pesan status dan deskripsi.
4. THE Application SHALL menggunakan `text-2xl font-bold` hanya untuk angka KPI di Stat Cards.
5. THE Application SHALL menggunakan class `text-xs font-bold uppercase tracking-wider text-gray-600` untuk semua label form.
6. THE Application SHALL menggunakan class `text-xs font-bold uppercase tracking-wider text-gray-400` untuk semua section heading.
7. THE Application SHALL tidak menggunakan font selain Inter di manapun dalam aplikasi.

---

### Requirement 13: Penghapusan File CSS Lama

**User Story:** Sebagai developer, saya ingin semua file CSS komponen lama dihapus setelah refactor selesai, sehingga tidak ada styling duplikat atau konflik antara CSS lama dan Tailwind.

#### Acceptance Criteria

1. WHEN refactor selesai, THE Application SHALL tidak mengimpor `DashboardLayout.css` di manapun dalam codebase.
2. WHEN refactor selesai, THE Application SHALL tidak mengimpor `FilterPanel.css` di manapun dalam codebase.
3. WHEN refactor selesai, THE Application SHALL tidak mengimpor `ExportService.css` di manapun dalam codebase.
4. WHEN refactor selesai, THE Application SHALL tidak mengimpor file CSS halaman (`CampaignOverviewPage.css`, `CampaignComparisonPage.css`, `TimeToTakeUpPage.css`, `RegionalPerformancePage.css`, `CustomerCriteriaPage.css`, `SimilarCampaignPage.css`) di manapun dalam codebase.
5. IF sebuah file CSS lama masih ada di filesystem setelah refactor, THEN THE Application SHALL tidak mereferensikan file tersebut dari komponen manapun.
