# Task 1.4 — Shared Filter Module

## Ringkasan Singkat

Modul `backend/shared/filters.py` menyediakan mekanisme filtering terpusat yang digunakan oleh seluruh Lambda handler untuk menyaring dataset campaign berdasarkan kriteria yang dipilih pengguna. Modul ini mengimplementasikan logika AND (irisan): sebuah data hanya akan lolos filter jika ia memenuhi **semua** kriteria filter yang aktif secara bersamaan. Modul ini bekerja di atas struktur data `ActiveFilter` dari `shared/models.py` dan mencakup validasi filter, pencocokan item, serta aplikasi filter ke dataset.

---

## Penjelasan Awam (Non-Technical)

Bayangkan seorang Campaign Owner di bank membuka dashboard dan ingin melihat data yang spesifik: **"Tampilkan hanya campaign QRIS, yang menggunakan channel WhatsApp, di wilayah Jakarta."**

Permintaan ini sebenarnya memiliki tiga syarat sekaligus. Modul `filters.py` bertindak seperti seorang *penjaga pintu* yang memeriksa setiap data campaign:

1. Apakah ini campaign QRIS? ✅ atau ❌
2. Apakah channel-nya WhatsApp? ✅ atau ❌  
3. Apakah wilayahnya Jakarta? ✅ atau ❌

Hanya data yang **lolos ketiga pemeriksaan sekaligus** yang akan ditampilkan. Ini berbeda dari logika OR (di mana data yang memenuhi salah satu saja sudah ditampilkan). Logika AND yang digunakan di sini membuat filter lebih presisi — cocok untuk analisis yang membutuhkan segmentasi ketat.

Manfaat bagi pengguna bisnis:
- Filter bekerja konsisten di semua halaman dashboard (Overview, Comparison, Regional, dll).
- Kombinasi filter yang kompleks tetap memberikan hasil yang tepat dan dapat diprediksi.
- Validasi otomatis mencegah filter "asal-asalan" yang bisa merusak query database.

---

## Penjelasan Teknis

### File yang Dibuat

- `backend/shared/filters.py`

### Library/Framework yang Digunakan

- `typing.Any` (standard library) — untuk type hint pada item dict yang bersifat dinamis.
- `shared.models.ActiveFilter` — dataclass yang merepresentasikan satu filter aktif.

### Pola Arsitektur yang Diterapkan

- **Filter sebagai data** — filter direpresentasikan sebagai objek `ActiveFilter`, bukan sebagai callback function. Ini memungkinkan filter diserialisasi, dilogging, dan divalidasi secara terstruktur.
- **AND semantics (Requirement 1.5)** — multiple filter selalu dikombinasikan dengan intersection (irisan), bukan union. Ini adalah keputusan domain eksplisit yang tercatat di requirement spec.
- **Safe default untuk missing key** — item yang tidak memiliki field yang difilter dianggap tidak cocok (non-matching), bukan dianggap cocok. Ini menghindari kebocoran data yang tidak diinginkan.
- **Non-mutating** — `apply_filters` mengembalikan list baru tanpa memodifikasi input.

### Field yang Didukung sebagai Filter

```python
VALID_FILTER_FIELDS: frozenset[str] = frozenset(
    {"product", "sub_product", "channel", "region", "period"}
)
```

Perhatikan bahwa ini adalah nama field abstrak yang digunakan di layer filter, **bukan** nama field di database (yang menggunakan nama seperti `flag_program`, `media_blasting`, `wilayah`). Pemetaan dilakukan di handler sebelum filter diaplikasikan.

### Penanganan Khusus Field `period`

Field `period` mendapat perlakuan khusus karena data yang sudah di-aggregate mungkin menyimpan informasi periode dalam format berbeda:

- Jika item memiliki key `"period"` → gunakan langsung.
- Jika tidak ada `"period"` tapi ada `"start_date"` → gunakan `"start_date"` sebagai proxy.
- Jika keduanya tidak ada → item dianggap tidak cocok.

Ini mengakomodasi dua jenis data: data mentah (dengan `start_date`) dan data pre-aggregate (dengan `period` label).

### Edge Cases yang Ditangani

| Kondisi | Penanganan |
|---------|-----------|
| `filters` kosong | Seluruh dataset dikembalikan tanpa perubahan |
| `dataset` kosong | List kosong dikembalikan |
| Item tidak memiliki field yang difilter | Item dianggap tidak cocok (excluded) |
| Filter `period` tanpa key `period` atau `start_date` | Item dianggap tidak cocok |
| Field tidak dikenal di `validate_filters` | Mengembalikan `False` |
| `values` kosong di filter | `validate_filters` mengembalikan `False` |

---

## Struktur Kode

```python
# backend/shared/filters.py

VALID_FILTER_FIELDS: frozenset[str]
# Konstanta set field yang valid untuk filtering

def validate_filters(filters: list[ActiveFilter]) -> bool:
    """
    Validasi semua filter dalam list.
    Mengembalikan True jika semua filter valid, False jika ada yang tidak valid.
    """

def _item_matches_filter(item: dict[str, Any], f: ActiveFilter) -> bool:
    """
    Fungsi privat: memeriksa apakah satu item memenuhi satu filter.
    Menangani kasus khusus untuk field 'period'.
    """

def apply_filters(
    dataset: list[dict[str, Any]],
    filters: list[ActiveFilter],
) -> list[dict[str, Any]]:
    """
    Mengaplikasikan semua filter ke dataset dengan logika AND.
    Mengembalikan subset dataset yang memenuhi semua filter.
    """
```

### Hubungan Antar Fungsi

```
apply_filters(dataset, filters)
    ├── Jika filters kosong → return list(dataset)
    └── Untuk tiap item dalam dataset:
            └── _item_matches_filter(item, f) untuk SEMUA f dalam filters
                    ├── f.field == "period" → cek "period" atau "start_date"
                    └── field lain → cek f.field ada di item, lalu cek nilai
```

---

## Simulasi / Skenario

### Skenario 1 — Filter Tunggal: Hanya Campaign QRIS

**Konteks:** Campaign Owner ingin melihat semua data khusus "PROGRAM QRIS".

```python
from shared.models import ActiveFilter
from shared.filters import apply_filters

dataset = [
    {"product": "PROGRAM QRIS",       "channel": "wa",        "region": "1"},
    {"product": "PROGRAM BIAYA ADMIN", "channel": "sms",       "region": "1"},
    {"product": "PROGRAM QRIS",       "channel": "telesales",  "region": "5"},
    {"product": "PROGRAM BIAYA ADMIN", "channel": "email",     "region": "11"},
]

filters = [ActiveFilter(field="product", values=["PROGRAM QRIS"])]

result = apply_filters(dataset, filters)
# Output:
# [
#   {"product": "PROGRAM QRIS", "channel": "wa",       "region": "1"},
#   {"product": "PROGRAM QRIS", "channel": "telesales", "region": "5"},
# ]
```

**2 dari 4 data lolos** karena hanya yang `product = "PROGRAM QRIS"` yang memenuhi kriteria.

---

### Skenario 2 — Filter Kombinasi AND: QRIS + WhatsApp + Jakarta

**Konteks:** Analisis mendalam: "Campaign QRIS yang dikirim via WA ke wilayah Jakarta (kode 1) saja."

```python
from shared.models import ActiveFilter
from shared.filters import apply_filters

dataset = [
    {"product": "PROGRAM QRIS", "channel": "wa",       "region": "1"},   # ✅ semua cocok
    {"product": "PROGRAM QRIS", "channel": "sms",       "region": "1"},   # ❌ channel bukan wa
    {"product": "PROGRAM QRIS", "channel": "wa",       "region": "5"},   # ❌ region bukan 1
    {"product": "PROGRAM BIAYA ADMIN", "channel": "wa", "region": "1"},  # ❌ product bukan QRIS
]

filters = [
    ActiveFilter(field="product", values=["PROGRAM QRIS"]),
    ActiveFilter(field="channel", values=["wa"]),
    ActiveFilter(field="region",  values=["1"]),
]

result = apply_filters(dataset, filters)
# Output: [{"product": "PROGRAM QRIS", "channel": "wa", "region": "1"}]
```

**Hanya 1 dari 4 data** yang lolos karena AND logic mengharuskan ketiga kondisi terpenuhi.

---

### Skenario 3 — Filter Period dengan Fallback ke `start_date`

**Konteks:** Data overview pre-aggregate menggunakan `start_date`, bukan `period`. Filter tetap harus bekerja.

```python
from shared.models import ActiveFilter
from shared.filters import apply_filters, _item_matches_filter

# Data pre-aggregate (tidak ada key "period", hanya "start_date")
data_agg = [
    {"start_date": "2024-08-01", "total_leads": 500},
    {"start_date": "2024-09-01", "total_leads": 600},
    {"start_date": "2024-10-01", "total_leads": 400},
]

# Data mentah (memiliki key "period")
data_raw = [
    {"period": "2024-08-01", "cif": "C001"},
    {"period": "2024-09-01", "cif": "C002"},
]

f = ActiveFilter(field="period", values=["2024-08-01"])

# Test pada data pre-aggregate (fallback ke start_date)
print(_item_matches_filter({"start_date": "2024-08-01"}, f))  # → True
print(_item_matches_filter({"start_date": "2024-09-01"}, f))  # → False

# Test pada data mentah (langsung pakai "period")
print(_item_matches_filter({"period": "2024-08-01"}, f))      # → True
```

---

### Skenario 4 — Validasi Filter Sebelum Dieksekusi

**Konteks:** API menerima filter dari request body. Sebelum query ke Athena, filter divalidasi dulu.

```python
from shared.models import ActiveFilter
from shared.filters import validate_filters

# Filter valid
valid = validate_filters([
    ActiveFilter(field="product", values=["PROGRAM QRIS"]),
    ActiveFilter(field="region",  values=["1", "5", "11"]),
])
print(valid)  # → True

# Filter tidak valid: field tidak dikenal
invalid_field = validate_filters([
    ActiveFilter(field="nama_program", values=["QRIS Agustus"]),  # field tidak valid
])
print(invalid_field)  # → False

# Filter tidak valid: values kosong
invalid_values = validate_filters([
    ActiveFilter(field="region", values=[]),  # values wajib tidak kosong
])
print(invalid_values)  # → False

# Filter kosong (tidak ada filter aktif) → valid
empty = validate_filters([])
print(empty)  # → True
```

---

### Skenario 5 — Multi-Value dalam Satu Filter (OR di dalam field)

**Konteks:** "Tampilkan data wilayah Jakarta (1), Bandung (5), ATAU Surabaya (11)."

```python
from shared.models import ActiveFilter
from shared.filters import apply_filters

dataset = [
    {"product": "PROGRAM QRIS", "region": "1"},   # Jakarta
    {"product": "PROGRAM QRIS", "region": "5"},   # Bandung
    {"product": "PROGRAM QRIS", "region": "11"},  # Surabaya
    {"product": "PROGRAM QRIS", "region": "7"},   # Makassar — tidak termasuk
]

# Dalam SATU filter, multiple values menggunakan OR (membership test)
filters = [ActiveFilter(field="region", values=["1", "5", "11"])]

result = apply_filters(dataset, filters)
# Output: 3 item pertama (Jakarta, Bandung, Surabaya)
# Jakarta, Bandung, Surabaya masuk; Makassar tidak
```

**Pola ini penting:** OR terjadi *di dalam* satu filter (antar nilai), sedangkan AND terjadi *antar* filter yang berbeda.

---

## Keterkaitan dengan Komponen Lain

### Bergantung pada:
- `shared.models.ActiveFilter` — struktur data filter yang divalidasi

### Digunakan oleh:
| Komponen | Cara Penggunaan |
|----------|----------------|
| `lambdas/campaign_overview/handler.py` | Filter data overview sebelum agregasi |
| `lambdas/campaign_comparison/handler.py` | Filter dataset campaign yang dibandingkan |
| `lambdas/regional_performance/handler.py` | Filter data regional berdasarkan request |
| `lambdas/time_analysis/handler.py` | Filter leads sebelum analisis waktu |
| `lambdas/customer_criteria/handler.py` | Filter leads berdasarkan kriteria nasabah |
| `lambdas/similar_campaign/handler.py` | Filter pool campaign sebelum similarity match |

### Pengaruh ke:
- Perubahan `VALID_FILTER_FIELDS` (menambah atau menghapus field yang bisa difilter) akan memengaruhi validasi di semua handler.
- Mengubah dari AND ke OR semantics di `apply_filters` akan secara dramatis mengubah hasil query di semua endpoint.
- Penambahan penanganan field baru (seperti `segment_by_aum`) memerlukan perubahan di `_item_matches_filter` dan `VALID_FILTER_FIELDS`.

---

## Requirements yang Dipenuhi

| Requirement | Deskripsi |
|-------------|-----------|
| **1.3** | Filter berdasarkan `product` (flag_program) di Campaign Overview |
| **1.4** | Filter berdasarkan `channel` (media_blasting) di Campaign Overview |
| **1.5** | Kombinasi filter menggunakan logika AND (intersection) |
| **3.3** | Filter time analysis berdasarkan produk dan channel |
| **3.4** | Filter time analysis berdasarkan wilayah |
| **4.4** | Filter data regional berdasarkan produk dan periode |
| **6.2** | Validasi filter sebelum eksekusi query |

---

## Catatan Penting

### Limitasi yang Diketahui
1. **Pencocokan selalu menggunakan string** — nilai integer seperti `region: 1` di database perlu dikonversi ke string (`"1"`) sebelum masuk ke `apply_filters`, atau ada ketidakcocokan tipe. Handler bertanggung jawab untuk normalisasi ini.
2. **Case-sensitive matching** — `"PROGRAM QRIS"` tidak akan cocok dengan `"program qris"`. Normalisasi case harus dilakukan di ETL layer atau sebelum memanggil `apply_filters`.
3. **Hanya mendukung equality check** — tidak ada support untuk range filter (misalnya `region between 1 and 5`) atau partial match. Filter jenis ini harus diimplementasikan secara terpisah di handler.
4. **`VALID_FILTER_FIELDS` menggunakan nama abstrak** — berbeda dengan nama field aktual di database (`flag_program`, `media_blasting`, dll). Mapping dilakukan di masing-masing handler, bukan di modul ini.

### Asumsi yang Dibuat
- Setiap item dalam dataset adalah `dict` Python standar (tidak ada nested object yang perlu di-flatten).
- Nilai dalam `ActiveFilter.values` selalu berupa string, meskipun field yang difilter mungkin bertipe integer di database.
- Filter yang valid secara struktur (lolos `validate_filters`) dianggap aman untuk dieksekusi tanpa validasi lanjutan di `apply_filters`.

### Todo untuk Pengembangan Berikutnya
- [ ] Tambahkan support untuk filter `segment_by_aum` dan `jenis_leads` ke `VALID_FILTER_FIELDS`.
- [ ] Pertimbangkan menambahkan opsi `case_sensitive: bool = False` di `ActiveFilter` untuk matching yang lebih fleksibel.
- [ ] Tambahkan fungsi `merge_filters` yang menggabungkan dua list filter dengan deduplikasi field yang sama.
- [ ] Tambahkan logging level DEBUG untuk mencatat jumlah item sebelum dan sesudah filtering (berguna untuk monitoring Lambda performance).
