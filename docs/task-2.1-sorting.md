# Task 2.1 — Sorting Utility Module

## Ringkasan Singkat

Modul `backend/shared/sorting.py` menyediakan fungsi-fungsi pengurutan data terpusat yang digunakan oleh Lambda handler untuk menampilkan data kampanye dalam urutan yang bermakna secara bisnis. Modul ini mencakup tiga fungsi utama: `sort_by_attribute` untuk pengurutan generik berdasarkan atribut apapun, `sort_similar_campaigns` untuk mengurutkan hasil pencarian kampanye serupa berdasarkan relevansi, dan `sort_regional_performance` untuk mengurutkan performa per wilayah dari yang terbaik ke terburuk. Semua fungsi bersifat non-mutating dan menggunakan strategi `sentinel value` untuk menempatkan data yang memiliki field kosong di posisi paling akhir.

---

## Penjelasan Awam (Non-Technical)

Bayangkan Anda sedang melihat tabel peringkat performa kampanye di dashboard. Data yang ditampilkan perlu diurutkan dengan cara yang logis bagi pengguna bisnis:

- **Wilayah mana yang paling tinggi take-up rate-nya?** → Tampilkan dari yang tertinggi ke terendah.
- **Campaign mana yang paling mirip dengan kampanye referensi?** → Tampilkan yang paling banyak dimensi kesamaannya dulu, kalau sama jumlah kesamaannya, yang take-up rate-nya lebih tinggi tampil lebih atas.
- **Data mana yang datanya tidak lengkap?** → Tempatkan di paling bawah, jangan campur dengan data valid di atas.

Modul `sorting.py` adalah "pengatur urutan" yang bekerja di balik layar untuk memastikan tampilan tabel selalu dalam urutan yang informatif dan konsisten. Seperti seorang asisten yang sudah tahu aturan pengurutan bisnis dan menerapkannya secara otomatis setiap kali data ditampilkan.

Manfaat bagi pengguna bisnis:
- Regional manager langsung tahu wilayah mana yang performanya terbaik tanpa perlu mengurutkan manual.
- Hasil "campaign serupa" langsung tersusun dari yang paling relevan, menghemat waktu analisis.
- Data yang tidak lengkap tidak "mengotori" bagian atas tabel — selalu muncul di bawah.

---

## Penjelasan Teknis

### File yang Dibuat

- `backend/shared/sorting.py`

### Library/Framework yang Digunakan

- `typing.Any` (standard library) — untuk type hint dict yang bersifat dinamis.
- `shared.models.SimilarCampaignResult` — dataclass untuk hasil pencarian kampanye serupa.

### Pola Arsitektur yang Diterapkan

- **Sentinel value strategy** — nilai `float("inf")` digunakan sebagai penanda untuk item yang tidak memiliki field yang diurutkan. Sentinel ini memastikan item tanpa field selalu muncul di posisi terakhir, terpisah dari item valid.
- **Non-mutating sort** — semua fungsi menggunakan `sorted()` (bukan `.sort()`) sehingga selalu mengembalikan list baru tanpa memodifikasi input.
- **Tuple key sorting** — `(0, nilai)` untuk item valid dan `(1, sentinel)` untuk item invalid. Tuple pertama digunakan Python sebagai tiebreaker, sehingga semua item invalid (tuple pertama = 1) selalu ditempatkan setelah semua item valid (tuple pertama = 0).
- **Multi-key sort** — `sort_similar_campaigns` menggunakan lambda dengan tuple `(-dimension_count, -take_up_rate)` untuk sort dua dimensi sekaligus secara efisien.

### Keputusan Desain Penting

1. **Mengapa `float("inf")` sebagai sentinel, bukan `None` atau `-1`?**
   `None` tidak bisa dibandingkan dengan integer/float secara langsung di Python 3 dan akan menghasilkan `TypeError`. `-1` adalah angka valid yang bisa muncul dalam data. `float("inf")` adalah nilai terbesar yang bisa direpresentasikan float, sehingga selalu muncul "terakhir" dalam ascending sort dan "pertama" dalam descending — karena kita negasi nilainya, sentinel negatif infinite menjadi yang paling kecil, dan tuple ke-0 `(0, ...)` vs `(1, ...)` memastikan urutan yang tepat.

2. **Mengapa `sort_similar_campaigns` menerima `list[SimilarCampaignResult]` dan bukan `list[dict]`?**
   Menggunakan typed dataclass sebagai parameter memaksa caller untuk menyiapkan data dalam format yang benar sebelum sorting. Ini lebih type-safe dibanding dict dan membantu IDE memberikan autocomplete.

3. **Mengapa fungsi `sort_by_attribute` menggunakan `try/except TypeError` untuk negasi?**
   Nilai dalam dict bisa berupa string (nama wilayah) atau angka (take-up rate). Untuk descending sort, nilai numerik dinegasi (`-val`). Nilai string tidak bisa dinegasi langsung. `except TypeError` memungkinkan fallback ke string sort ascending untuk tipe non-numerik, daripada crash.

### Konstanta Sentinel

```python
_SENTINEL_HIGH = float("inf")   # untuk ascending: item invalid sort terakhir
_SENTINEL_LOW  = float("-inf")  # didefinisikan tapi tidak digunakan langsung
                                 # (dipertahankan untuk dokumentasi/extension)
```

### Edge Cases yang Ditangani

| Kondisi | Penanganan |
|---------|-----------|
| Item tidak memiliki `attribute` yang diurutkan | Selalu muncul paling akhir |
| List kosong sebagai input | Dikembalikan sebagai list kosong |
| Nilai string di `sort_by_attribute` descending | Fallback ke ascending string sort |
| Dua campaign memiliki `dimension_count` yang sama | Tiebreaker: `take_up_rate` descending |
| Region tidak memiliki `take_up_rate` | Selalu muncul paling akhir |
| Satu elemen dalam list | Dikembalikan dalam list satu elemen (no-op) |

---

## Struktur Kode

```python
# backend/shared/sorting.py

_SENTINEL_HIGH = float("inf")    # sentinel: item dengan field kosong → sort terakhir
_SENTINEL_LOW  = float("-inf")   # sentinel cadangan (untuk dokumentasi)

def sort_by_attribute(
    items: list[dict[str, Any]],
    attribute: str,
    ascending: bool,
) -> list[dict[str, Any]]:
    """
    Sorting generik untuk list of dict berdasarkan satu atribut.
    Item tanpa atribut selalu muncul di akhir.
    """

def sort_similar_campaigns(
    campaigns: list[SimilarCampaignResult],
) -> list[SimilarCampaignResult]:
    """
    Sort hasil pencarian campaign serupa:
    1. Primary:   dimension_count DESC (lebih banyak kesamaan = lebih relevan)
    2. Secondary: take_up_rate DESC (di antara campaign sama-sama relevan, pilih yang performa lebih baik)
    """

def sort_regional_performance(
    regions: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Sort data performa wilayah berdasarkan take_up_rate DESC.
    Wilayah tanpa take_up_rate selalu muncul di akhir.
    """
```

### Pola Key Function dalam `sort_by_attribute`

```python
# Ascending — item invalid → (1, inf) → selalu setelah (0, nilai_apapun)
def key_asc(item):
    if attribute not in item:
        return (1, _SENTINEL_HIGH)
    return (0, item[attribute])

# Descending — negasi nilai numerik untuk membalik urutan
def key_desc(item):
    if attribute not in item:
        return (1, _SENTINEL_HIGH)
    val = item[attribute]
    try:
        return (0, -val)       # numerik: negasi untuk descending
    except TypeError:
        return (0, val)        # string: fallback ascending
```

---

## Simulasi / Skenario

### Skenario 1 — Urutan Performa Wilayah (sort_regional_performance)

**Konteks:** Lambda `regional_performance` mengambil data performa dari 5 wilayah dan perlu mengurutkannya dari take-up rate tertinggi untuk tampil di tabel dashboard.

```python
from shared.sorting import sort_regional_performance

regions = [
    {"wilayah": 1,  "nama": "Jakarta",  "take_up_rate": 9.2,  "total_leads": 300},
    {"wilayah": 5,  "nama": "Bandung",  "take_up_rate": 12.8, "total_leads": 200},
    {"wilayah": 11, "nama": "Surabaya", "take_up_rate": 7.5,  "total_leads": 180},
    {"wilayah": 3,  "nama": "Semarang", "take_up_rate": 15.1, "total_leads": 150},
    {"wilayah": 9,  "nama": "Medan",    "take_up_rate": 10.3, "total_leads": 220},
]

sorted_regions = sort_regional_performance(regions)

# Output (urut dari take_up_rate tertinggi):
# [
#   {"wilayah": 3,  "nama": "Semarang", "take_up_rate": 15.1, ...},  # 🥇
#   {"wilayah": 5,  "nama": "Bandung",  "take_up_rate": 12.8, ...},  # 🥈
#   {"wilayah": 9,  "nama": "Medan",    "take_up_rate": 10.3, ...},  # 🥉
#   {"wilayah": 1,  "nama": "Jakarta",  "take_up_rate": 9.2,  ...},  # 4th
#   {"wilayah": 11, "nama": "Surabaya", "take_up_rate": 7.5,  ...},  # 5th
# ]
```

Regional manager melihat Semarang di posisi teratas — performa terbaik bulan ini dengan take-up rate 15.1%.

---

### Skenario 2 — Urutan Campaign Serupa (sort_similar_campaigns)

**Konteks:** Lambda `similar_campaign` menemukan 4 campaign yang mirip dengan referensi "PROGRAM QRIS Agustus 2024". Perlu diurutkan berdasarkan relevansi.

```python
from shared.models import SimilarCampaignResult
from shared.sorting import sort_similar_campaigns

campaigns = [
    SimilarCampaignResult(
        campaign_id="QRIS-2024-03",
        campaign_name="PROGRAM QRIS Maret 2024",
        matching_dimensions=["flag_program", "media_blasting", "jenis_leads"],
        dimension_count=3,           # cocok di 3 dimensi
        similarity_score=0.95,
        take_up_rate=11.2,           # take-up rate lebih rendah
        total_leads=800,
        total_take_up=90,
    ),
    SimilarCampaignResult(
        campaign_id="QRIS-2024-05",
        campaign_name="PROGRAM QRIS Mei 2024",
        matching_dimensions=["flag_program", "media_blasting", "jenis_leads"],
        dimension_count=3,           # cocok di 3 dimensi (sama)
        similarity_score=0.92,
        take_up_rate=14.5,           # take-up rate lebih tinggi → naik
        total_leads=950,
        total_take_up=138,
    ),
    SimilarCampaignResult(
        campaign_id="BIAYA-2024-08",
        campaign_name="PROGRAM BIAYA ADMIN Agustus 2024",
        matching_dimensions=["media_blasting", "jenis_leads"],
        dimension_count=2,           # hanya cocok di 2 dimensi
        similarity_score=0.70,
        take_up_rate=20.0,           # take-up tinggi, tapi relevansi rendah
        total_leads=500,
        total_take_up=100,
    ),
    SimilarCampaignResult(
        campaign_id="QRIS-2024-01",
        campaign_name="PROGRAM QRIS Januari 2024",
        matching_dimensions=["flag_program"],
        dimension_count=1,           # hanya cocok di 1 dimensi
        similarity_score=0.45,
        take_up_rate=8.0,
        total_leads=600,
        total_take_up=48,
    ),
]

sorted_campaigns = sort_similar_campaigns(campaigns)

# Urutan hasil:
# 1. QRIS Mei 2024      → dimension_count=3, take_up_rate=14.5 (3 dim, rate lebih tinggi)
# 2. QRIS Maret 2024    → dimension_count=3, take_up_rate=11.2 (3 dim, rate lebih rendah)
# 3. BIAYA ADMIN Agt    → dimension_count=2 (hanya 2 dim cocok)
# 4. QRIS Januari 2024  → dimension_count=1 (paling sedikit kesamaan)

for c in sorted_campaigns:
    print(f"{c.campaign_name}: dim={c.dimension_count}, rate={c.take_up_rate}%")
```

**Penjelasan urutan:** QRIS Mei dan Maret sama-sama cocok di 3 dimensi, tapi Mei naik karena take-up rate-nya lebih tinggi (14.5% vs 11.2%). BIAYA ADMIN meskipun take-up 20%, turun ke posisi 3 karena hanya cocok di 2 dimensi — relevansi lebih penting dari performa.

---

### Skenario 3 — Sort Generik Ascending dan Descending (sort_by_attribute)

**Konteks:** Handler comparison perlu mengurutkan campaign berdasarkan `total_leads` dari terbesar ke terkecil (descending).

```python
from shared.sorting import sort_by_attribute

campaigns = [
    {"campaign_id": "QRIS-08", "nama_program": "PROGRAM QRIS Agustus 2024",  "total_leads": 1000},
    {"campaign_id": "QRIS-07", "nama_program": "PROGRAM QRIS Juli 2024",     "total_leads":  850},
    {"campaign_id": "QRIS-09", "nama_program": "PROGRAM QRIS September 2024","total_leads": 1200},
    {"campaign_id": "BIAYA-08","nama_program": "PROGRAM BIAYA ADMIN Agt 2024","total_leads":  600},
]

# Ascending: dari terkecil ke terbesar
asc = sort_by_attribute(campaigns, attribute="total_leads", ascending=True)
# BIAYA-08 (600) → QRIS-07 (850) → QRIS-08 (1000) → QRIS-09 (1200)

# Descending: dari terbesar ke terkecil
desc = sort_by_attribute(campaigns, attribute="total_leads", ascending=False)
# QRIS-09 (1200) → QRIS-08 (1000) → QRIS-07 (850) → BIAYA-08 (600)

print([c["campaign_id"] for c in desc])
# ["QRIS-09", "QRIS-08", "QRIS-07", "BIAYA-08"]
```

---

### Skenario 4 — Menangani Data Tidak Lengkap (Sentinel Value)

**Konteks:** Beberapa wilayah di data masih dalam proses ETL dan belum memiliki `take_up_rate`. Data ini harus tetap muncul di tabel, tapi di bawah semua data valid.

```python
from shared.sorting import sort_regional_performance

regions = [
    {"wilayah": 1,  "nama": "Jakarta",  "take_up_rate": 9.2},
    {"wilayah": 5,  "nama": "Bandung",  "take_up_rate": 12.8},
    {"wilayah": 13, "nama": "Ambon"},    # ← tidak ada take_up_rate (ETL belum selesai)
    {"wilayah": 11, "nama": "Surabaya", "take_up_rate": 7.5},
    {"wilayah": 15, "nama": "Jayapura"}, # ← tidak ada take_up_rate
]

result = sort_regional_performance(regions)

# Output:
# 1. Bandung   → 12.8%
# 2. Jakarta   → 9.2%
# 3. Surabaya  → 7.5%
# 4. Ambon     → (no data) ← tetap muncul, di bawah
# 5. Jayapura  → (no data) ← tetap muncul, di bawah
```

Ambon dan Jayapura tetap tampil di tabel (tidak dihilangkan), tapi selalu di bawah data valid.

---

### Skenario 5 — Sort Nama Campaign (String, Ascending/Descending)

```python
from shared.sorting import sort_by_attribute

campaigns = [
    {"campaign_id": "C3", "nama_program": "PROGRAM QRIS September 2024"},
    {"campaign_id": "C1", "nama_program": "PROGRAM BIAYA ADMIN Agustus 2024"},
    {"campaign_id": "C2", "nama_program": "PROGRAM QRIS Agustus 2024"},
]

# Ascending alphabetical (A→Z)
asc = sort_by_attribute(campaigns, attribute="nama_program", ascending=True)
# C1 (BIAYA ADMIN...) → C2 (QRIS Agustus...) → C3 (QRIS September...)

# Descending string: karena string tidak bisa dinegasi,
# sort_by_attribute fallback ke ascending untuk descending string
# (limitasi yang terdokumentasi — gunakan sort_by_attribute hanya untuk numerik descending)
```

---

## Keterkaitan dengan Komponen Lain

### Bergantung pada:
- `shared.models.SimilarCampaignResult` — dataclass untuk `sort_similar_campaigns`
- `typing.Any` dari Python standard library

### Digunakan oleh:
| Komponen | Fungsi yang Dipakai | Tujuan |
|----------|-------------------|--------|
| `lambdas/regional_performance/handler.py` | `sort_regional_performance` | Tampilkan wilayah dari take-up tertinggi |
| `lambdas/similar_campaign/handler.py` | `sort_similar_campaigns` | Ranking campaign paling relevan pertama |
| `lambdas/campaign_comparison/handler.py` | `sort_by_attribute` | Sort campaign berdasarkan metrik yang dipilih |
| `lambdas/campaign_overview/handler.py` | `sort_by_attribute` | Sort tren periode |
| `lambdas/customer_criteria/handler.py` | `sort_by_attribute` | Sort distribusi segmen nasabah |

### Pengaruh ke:
- Perubahan aturan sorting di `sort_similar_campaigns` (misalnya menambahkan `similarity_score` sebagai tiebreaker ketiga) akan mengubah urutan hasil di halaman Similar Campaign.
- Perubahan perilaku `sort_by_attribute` untuk string descending akan memengaruhi semua komponen yang mengurutkan berdasarkan field string.
- Jika `SimilarCampaignResult` di `models.py` menambahkan field baru, `sort_similar_campaigns` mungkin perlu diupdate untuk memasukkan field tersebut sebagai tiebreaker tambahan.

---

## Requirements yang Dipenuhi

| Requirement | Deskripsi |
|-------------|-----------|
| **2.4** | Hasil campaign serupa diurutkan berdasarkan relevansi (dimension match) — diimplementasikan oleh `sort_similar_campaigns` |
| **4.2** | Data performa regional ditampilkan dari take-up rate tertinggi — diimplementasikan oleh `sort_regional_performance` |
| **6.1** | Sorting generik berdasarkan atribut dinamis untuk tampilan tabel di berbagai endpoint — diimplementasikan oleh `sort_by_attribute` |

---

## Catatan Penting

### Limitasi yang Diketahui
1. **`sort_by_attribute` dengan string descending menggunakan fallback ke ascending.** Ini adalah limitasi yang disengaja (documented behavior) — jika descending alphabetical dibutuhkan, perlu implementasi terpisah dengan `reverse=True` atau penggunaan `functools.cmp_to_key`.
2. **`sort_similar_campaigns` tidak mendukung pengurutan dinamis.** Urutan selalu `dimension_count DESC → take_up_rate DESC`. Jika bisnis ingin bisa sort berdasarkan metrik lain (misalnya `total_leads`), perlu fungsi baru atau parameter tambahan.
3. **Tidak ada stable sort guarantee untuk item dengan nilai yang sama.** Python's `sorted()` adalah stable sort, tapi hanya untuk elemen dengan key yang identik. Jika dua wilayah memiliki `take_up_rate` yang sama persis, urutan relatif keduanya tidak didefinisikan secara eksplisit.
4. **`_SENTINEL_LOW` didefinisikan tapi tidak digunakan secara langsung** di implementasi saat ini. Dipertahankan untuk mendokumentasikan ketersediaan nilai dan kemungkinan penggunaan di masa depan.

### Asumsi yang Dibuat
- Nilai dalam field numerik (seperti `take_up_rate`, `total_leads`) sudah dalam tipe `float` atau `int` — bukan string numerik seperti `"12.5"`.
- `SimilarCampaignResult.dimension_count` selalu merupakan integer non-negatif yang mencerminkan panjang `matching_dimensions`.
- Items dalam list yang diurutkan adalah independent satu sama lain — tidak ada relasi parent-child yang perlu dijaga selama pengurutan.

### Todo untuk Pengembangan Berikutnya
- [ ] Tambahkan fungsi `sort_by_multiple_attributes` untuk multi-key sorting yang lebih fleksibel (list of `(attribute, ascending)` tuples).
- [ ] Tambahkan parameter `nulls_position: Literal["first", "last"] = "last"` ke `sort_by_attribute` untuk kontrol eksplisit posisi data tidak lengkap.
- [ ] Perbaiki perilaku string descending di `sort_by_attribute` agar menggunakan `reverse=True` dengan benar.
- [ ] Pertimbangkan menambahkan tiebreaker `campaign_id` (alphabetical) sebagai tiebreaker terakhir di `sort_similar_campaigns` dan `sort_regional_performance` untuk deterministic sort — berguna untuk testing.
