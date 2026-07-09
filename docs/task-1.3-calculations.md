# Task 1.3 — Shared Calculations Module

## Ringkasan Singkat

Modul `backend/shared/calculations.py` adalah pustaka kalkulasi inti yang digunakan bersama oleh seluruh Lambda handler dalam sistem Campaign Insight Generator. Modul ini menyediakan fungsi-fungsi matematis standar — mulai dari menghitung persentase take-up, menghitung selisih hari, hingga menghasilkan statistik deskriptif dan distribusi persentase kelompok data. Modul ini dirancang sepenuhnya mandiri (tidak bergantung pada modul `shared` lainnya) agar mudah diuji dan dipelihara secara terpisah.

---

## Penjelasan Awam (Non-Technical)

Bayangkan sebuah tim marketing bank yang menjalankan program promosi QRIS. Di akhir program, mereka perlu menjawab pertanyaan-pertanyaan seperti:

- **"Dari 1.000 nasabah yang kami hubungi, berapa persen yang benar-benar ikut program?"**
- **"Nasabah yang ikut program, rata-rata berapa hari setelah dihubungi mereka baru mendaftar?"**
- **"Kalau kami lihat sebaran wilayah, Jakarta berapa persen, Surabaya berapa persen?"**
- **"Apakah grafik tren mingguan atau bulanan yang lebih tepat untuk periode ini?"**

Modul `calculations.py` adalah "mesin hitung" di balik layar yang menjawab semua pertanyaan tersebut secara otomatis. Seperti kalkulator khusus yang sudah tahu rumus-rumus bisnis perbankan, sehingga setiap bagian sistem tidak perlu menulis rumus yang sama berulang kali.

Manfaat bagi pengguna bisnis:
- Angka yang tampil di dashboard selalu konsisten karena dihitung oleh satu fungsi yang sama.
- Perubahan rumus (misalnya cara menghitung median) cukup dilakukan di satu tempat.
- Risiko kesalahan hitung tereduksi karena setiap fungsi sudah diuji secara terpisah.

---

## Penjelasan Teknis

### File yang Dibuat

- `backend/shared/calculations.py`

### Library/Framework yang Digunakan

- `datetime.date` (standard library) — untuk kalkulasi selisih tanggal.
- Tidak ada dependensi pihak ketiga. Modul ini sepenuhnya murni Python.

### Pola Arsitektur yang Diterapkan

- **Pure functions** — semua fungsi bersifat deterministik: input yang sama selalu menghasilkan output yang sama, tanpa efek samping.
- **Self-contained module** — tidak mengimpor dari `shared/models.py` maupun modul lain dalam proyek. Ini menjamin modul bisa diuji dan digunakan secara independen.
- **Fail-fast validation** — setiap fungsi memvalidasi parameter di awal dan langsung melempar `ValueError` jika input tidak valid, bukan mengembalikan nilai sentinel yang ambigu.

### Keputusan Desain Penting

1. **Mengapa tidak menggunakan `numpy` atau `statistics` dari standard library?**
   Fungsi `compute_statistics` diimplementasikan secara manual menggunakan Python murni. Ini menghindari dependensi tambahan pada Lambda layer dan memastikan kompatibilitas di lingkungan AWS Lambda tanpa konfigurasi tambahan.

2. **Penyesuaian grup terakhir di `compute_distribution_percentages`**
   Persentase dibulatkan ke 4 desimal, dan grup terakhir disesuaikan (`100.0 - running_sum`) agar total tepat 100.0. Ini menghindari *floating-point rounding error* yang umum terjadi saat menjumlahkan banyak angka desimal.

3. **Ambang batas `select_granularity` di 90 hari**
   Dipilih berdasarkan konvensi bisnis: rentang ≤ 90 hari cukup detail untuk ditampilkan per minggu, sementara rentang lebih panjang lebih mudah dibaca secara bulanan.

### Edge Cases yang Ditangani

| Kondisi | Penanganan |
|---------|-----------|
| `total_leads = 0` | `ValueError` — tidak bisa membagi dengan nol |
| `total_take_up = 0` | Mengembalikan `0.0` (bukan error) |
| `take_up_date` lebih awal dari `distribution_date` | `ValueError` |
| List `values` kosong di `compute_statistics` | `ValueError` |
| Total semua grup = 0 di `compute_distribution_percentages` | `ValueError` |
| `end_date` lebih awal dari `start_date` di `select_granularity` | `ValueError` |

---

## Struktur Kode

```python
# backend/shared/calculations.py

def calculate_take_up_rate(total_leads: int, total_take_up: int) -> float:
    """Menghitung persentase take-up dari total leads dan total konversi."""

def compute_time_to_take_up(distribution_date: date, take_up_date: date) -> int:
    """Menghitung jumlah hari kalender antara tanggal distribusi dan take-up."""

def compute_statistics(values: list[int]) -> dict[str, float]:
    """Menghitung statistik deskriptif: min, max, mean, median."""

def compute_distribution_percentages(groups: dict[str, int]) -> dict[str, float]:
    """Menghitung persentase setiap kelompok terhadap total, dengan koreksi pembulatan."""

def select_granularity(start_date: date, end_date: date) -> str:
    """Memilih granularitas waktu: 'weekly' (≤90 hari) atau 'monthly' (>90 hari)."""
```

### Detail Tiap Fungsi

| Fungsi | Input | Output | Raises |
|--------|-------|--------|--------|
| `calculate_take_up_rate` | `total_leads: int`, `total_take_up: int` | `float` (0.0–100.0) | `ValueError` jika `total_leads ≤ 0` |
| `compute_time_to_take_up` | `distribution_date: date`, `take_up_date: date` | `int` (≥ 0) | `ValueError` jika urutan tanggal salah |
| `compute_statistics` | `values: list[int]` | `dict` dengan key `min`, `max`, `mean`, `median` | `ValueError` jika list kosong |
| `compute_distribution_percentages` | `groups: dict[str, int]` | `dict[str, float]` sum = 100.0 | `ValueError` jika total = 0 |
| `select_granularity` | `start_date: date`, `end_date: date` | `"weekly"` atau `"monthly"` | `ValueError` jika urutan tanggal salah |

---

## Simulasi / Skenario

### Skenario 1 — Menghitung Take-Up Rate Campaign QRIS Agustus 2024

**Konteks:** Campaign "PROGRAM QRIS Agustus 2024" mendistribusikan leads ke 1.000 nasabah. Sebanyak 87 nasabah akhirnya melakukan transaksi QRIS pertama mereka (take up).

```python
from shared.calculations import calculate_take_up_rate

# Input
total_leads = 1000
total_take_up = 87

# Proses
rate = calculate_take_up_rate(total_leads, total_take_up)

# Output
print(rate)  # → 8.7
```

**Interpretasi:** Dari 1.000 nasabah yang dihubungi, 8,7% berhasil dikonversi. Angka ini yang muncul sebagai KPI utama di halaman Campaign Overview.

---

### Skenario 2 — Menghitung Waktu Rata-rata Take-Up

**Konteks:** Tim analis ingin tahu berapa hari rata-rata nasabah membutuhkan waktu untuk take up setelah menerima pesan WA blast.

```python
from datetime import date
from shared.calculations import compute_time_to_take_up, compute_statistics

# Data 5 nasabah yang take up (dari ETL join)
distribusi = date(2024, 8, 1)
tanggal_take_up = [
    date(2024, 8,  3),   # 2 hari
    date(2024, 8,  8),   # 7 hari
    date(2024, 8,  5),   # 4 hari
    date(2024, 8, 15),   # 14 hari
    date(2024, 8,  4),   # 3 hari
]

# Hitung selisih hari untuk tiap nasabah
hari_list = [
    compute_time_to_take_up(distribusi, tgl) for tgl in tanggal_take_up
]
# hari_list = [2, 7, 4, 14, 3]

# Hitung statistik
stats = compute_statistics(hari_list)
# Output:
# {
#   "min": 2.0,
#   "max": 14.0,
#   "mean": 6.0,
#   "median": 4.0
# }
```

**Interpretasi:** Median 4 hari berarti separuh nasabah take up dalam 4 hari pertama. Mean 6 hari lebih tinggi karena ada nasabah yang butuh 14 hari (outlier menarik rata-rata ke atas).

---

### Skenario 3 — Distribusi Leads per Segmen Nasabah

**Konteks:** Campaign QRIS Agustus 2024 mendistribusikan leads ke 3 segmen. Tim ingin tahu komposisi persentasenya untuk laporan.

```python
from shared.calculations import compute_distribution_percentages

groups = {
    "MASS":     650,
    "AFFLUENT": 280,
    "EMERALD":   70,
}

result = compute_distribution_percentages(groups)
# Output:
# {
#   "MASS":     65.0,
#   "AFFLUENT": 28.0,
#   "EMERALD":   7.0    ← disesuaikan agar total tepat 100.0
# }
```

**Catatan:** Jika dibulatkan biasa, `EMERALD` mungkin menghasilkan `6.9999...` atau `7.0001`. Fungsi ini memastikan grup terakhir selalu disesuaikan agar total tepat 100.0.

---

### Skenario 4 — Pemilihan Granularitas Otomatis

```python
from datetime import date
from shared.calculations import select_granularity

# Rentang pendek (30 hari) → weekly
g1 = select_granularity(date(2024, 8, 1), date(2024, 8, 31))
# g1 = "weekly"

# Rentang panjang (6 bulan) → monthly
g2 = select_granularity(date(2024, 1, 1), date(2024, 6, 30))
# g2 = "monthly"

# Tepat di batas (90 hari) → weekly
g3 = select_granularity(date(2024, 8, 1), date(2024, 10, 30))
# g3 = "weekly"  (90 hari → masih weekly)

# Melebihi batas (91 hari) → monthly
g4 = select_granularity(date(2024, 8, 1), date(2024, 10, 31))
# g4 = "monthly"
```

---

### Skenario 5 — Input Tidak Valid (Error Handling)

```python
# Error: leads = 0
calculate_take_up_rate(0, 87)
# → ValueError: total_leads must be greater than 0, got 0

# Error: take_up_date lebih awal dari distribution_date
compute_time_to_take_up(date(2024, 8, 10), date(2024, 8, 1))
# → ValueError: take_up_date (2024-08-01) must not be before distribution_date (2024-08-10)

# Error: list kosong
compute_statistics([])
# → ValueError: values must not be empty
```

---

## Keterkaitan dengan Komponen Lain

### Bergantung pada:
- `datetime.date` dari Python standard library
- Tidak ada dependensi internal proyek

### Digunakan oleh:
| Komponen | Fungsi yang Dipakai |
|----------|-------------------|
| `lambdas/campaign_overview/handler.py` | `calculate_take_up_rate`, `select_granularity` |
| `lambdas/time_analysis/handler.py` | `compute_time_to_take_up`, `compute_statistics` |
| `lambdas/campaign_comparison/handler.py` | `calculate_take_up_rate`, `compute_distribution_percentages` |
| `lambdas/regional_performance/handler.py` | `calculate_take_up_rate`, `compute_distribution_percentages` |
| `lambdas/customer_criteria/handler.py` | `compute_statistics`, `compute_distribution_percentages` |
| `glue_jobs/aggregate_metrics.py` | `calculate_take_up_rate` (saat ETL pre-compute) |

### Pengaruh ke:
- Jika rumus `calculate_take_up_rate` diubah (misalnya menggunakan formula yang berbeda), seluruh angka KPI di semua halaman dashboard akan berubah.
- Perubahan ambang batas granularitas (90 hari) akan mengubah tampilan grafik tren di Campaign Overview.
- Perubahan cara pembulatan di `compute_distribution_percentages` akan memengaruhi semua chart distribusi (segmen, wilayah, channel).

---

## Requirements yang Dipenuhi

| Requirement | Deskripsi |
|-------------|-----------|
| **1.1** | Sistem menampilkan total leads, total take-up, dan take-up rate — dihitung oleh `calculate_take_up_rate` |
| **1.2** | Trend take-up rate per periode — granularitas ditentukan oleh `select_granularity` |
| **3.1** | Analisis time-to-take-up — dihitung oleh `compute_time_to_take_up` dan `compute_statistics` |
| **3.2** | Statistik min/max/mean/median waktu take-up — disediakan oleh `compute_statistics` |
| **5.2** | Distribusi leads per segmen/wilayah — dihitung oleh `compute_distribution_percentages` |

---

## Catatan Penting

### Limitasi yang Diketahui
1. **`compute_statistics` hanya menerima `list[int]`** — jika data memiliki nilai desimal (misalnya `time_to_take_up_days` dalam jam), perlu konversi ke integer terlebih dahulu atau fungsi ini perlu diubah menjadi `list[float]`.
2. **Tidak ada proteksi terhadap nilai negatif** di `compute_statistics` dan `compute_distribution_percentages` — nilai negatif di input tidak akan divalidasi dan tetap akan diproses.
3. **`total_take_up` tidak divalidasi terhadap `total_leads`** di `calculate_take_up_rate` — bisa menghasilkan rate > 100% jika data input salah (data cleaning harus dilakukan di ETL layer).

### Asumsi yang Dibuat
- Semua tanggal menggunakan timezone lokal (tidak ada penanganan UTC/timezone offset).
- "Calendar days" dalam `compute_time_to_take_up` berarti hari kalender penuh, bukan jam bisnis.
- Granularitas "weekly" dan "monthly" adalah string literal yang dikonsumsi oleh Athena query builder untuk menentukan ekspresi SQL `date_trunc`.

### Todo untuk Pengembangan Berikutnya
- [ ] Tambahkan fungsi `compute_weighted_average` untuk menghitung rata-rata tertimbang berdasarkan jumlah leads per periode.
- [ ] Pertimbangkan menambahkan `compute_percentile` (P25, P75, P90) untuk analisis distribusi waktu take-up yang lebih kaya.
- [ ] Tambahkan validasi bahwa `total_take_up <= total_leads` dengan opsi `strict=False` untuk backward compatibility.
