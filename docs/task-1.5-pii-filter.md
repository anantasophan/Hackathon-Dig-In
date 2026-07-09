# Task 1.5 — PII Filter Module

## Ringkasan Singkat

Modul `backend/shared/pii_filter.py` adalah komponen keamanan data yang bertanggung jawab memastikan bahwa informasi pribadi nasabah (Personally Identifiable Information / PII) tidak pernah bocor keluar melalui API response. Modul ini menyediakan dua fungsi utama: `strip_pii` untuk menghapus semua field PII dari data sebelum dikirim ke frontend, dan `has_pii` untuk mendeteksi apakah suatu data masih mengandung PII. Kedua fungsi bekerja secara rekursif — artinya mampu memeriksa dan membersihkan data bertingkat (nested dict dan list) hingga level terdalam.

---

## Penjelasan Awam (Non-Technical)

Dalam operasi kampanye bank, data leads yang diproses sistem berisi informasi sensitif nasabah: nama lengkap, nomor rekening, nomor identitas (KTP/SIM), dan alamat rumah. Informasi-informasi ini **tidak boleh** tampil di layar aplikasi dashboard, apalagi masuk ke log sistem yang bisa dibaca pihak tidak berwenang.

Bayangkan seperti proses pengguntingan dokumen sebelum diserahkan ke publik. Seorang pegawai bank yang ingin berbagi laporan performa kampanye tidak perlu melihat nama nasabah satu per satu — mereka hanya butuh angka seperti "berapa persen yang take up?" atau "dari segmen mana mayoritas nasabahnya?".

Modul `pii_filter.py` berperan sebagai **gunting otomatis** yang selalu dijalankan sebelum data dikirim ke pengguna. Tidak peduli seberapa dalam data itu tersarang (misalnya data dalam data dalam data), gunting ini akan mencari dan menghapus semua informasi sensitif tanpa terlewat satu pun.

Manfaat bagi pengguna bisnis dan compliance:
- Dashboard aman digunakan oleh staf yang tidak memiliki akses ke data nasabah mentah.
- Kepatuhan terhadap regulasi OJK terkait perlindungan data nasabah terjamin secara teknis.
- Tidak ada risiko "human error" dalam menyembunyikan data sensitif — prosesnya otomatis dan konsisten.
- Modul ini berjalan untuk **semua pengguna** tanpa pengecualian — tidak ada role yang bisa bypass.

---

## Penjelasan Teknis

### File yang Dibuat

- `backend/shared/pii_filter.py`

### Library/Framework yang Digunakan

- `typing.Any` (standard library) — untuk type hint pada struktur data yang bersifat dinamis.
- Tidak ada dependensi pihak ketiga.

### Field PII yang Dilindungi

```python
PII_FIELDS: frozenset[str] = frozenset(
    {
        "nama_lengkap",
        "nomor_rekening",
        "nomor_identitas",
        "alamat_lengkap",
    }
)
```

> **Catatan Penting Rekonsiliasi:** Modul `pii_filter.py` melindungi 4 field ini sebagai layer keamanan di API response. Sementara itu, `shared/models.py` mendefinisikan `PII_FIELDS = frozenset({"cif"})` yang digunakan sebagai referensi utama di data model `LeadRecord`. Kedua set ini bekerja pada lapisan yang berbeda: `models.py` untuk kebutuhan data model dan ETL, sedangkan `pii_filter.py` untuk sanitasi API response. Pastikan kedua set ini tetap sinkron saat menambahkan field baru.

### Pola Arsitektur yang Diterapkan

- **Recursive traversal** — fungsi memanggil dirinya sendiri untuk memproses nested dict dan list, sehingga tidak ada batasan kedalaman struktur data yang bisa dibersihkan.
- **Non-mutating** — fungsi `strip_pii` selalu mengembalikan objek baru, tidak pernah memodifikasi input. Ini aman untuk dipanggil di mana saja tanpa risiko efek samping.
- **Pass-through untuk scalar** — nilai bukan-dict dan bukan-list (string, integer, float, boolean, None) dikembalikan langsung tanpa modifikasi. Ini memungkinkan rekursi berhenti dengan aman di "daun" dari struktur data.
- **Defense-in-depth** — modul ini adalah layer terakhir sebelum data keluar dari Lambda. Meskipun data sudah dibersihkan di ETL, modul ini tetap berjalan sebagai safety net.

### Keputusan Desain Penting

1. **Mengapa `frozenset` dan bukan `list` atau `set`?**
   `frozenset` bersifat immutable (tidak bisa diubah setelah dibuat) dan memiliki operasi membership check O(1) yang sangat efisien. Ini mencegah seseorang secara tidak sengaja menambahkan atau menghapus field dari set PII di runtime.

2. **Mengapa rekursif dan bukan flat iteration?**
   Data campaign bisa memiliki struktur nested — misalnya response yang berisi list of leads, di mana setiap lead adalah dict yang mungkin berisi nested dict lain. Rekursi memastikan tidak ada field PII yang terlewat di level manapun.

3. **Mengapa `has_pii` terpisah dari `strip_pii`?**
   `has_pii` berguna untuk testing, logging, dan assertion — memverifikasi bahwa `strip_pii` benar-benar sudah dijalankan dan hasilnya bersih. Memisahkan keduanya mengikuti prinsip *single responsibility*.

### Edge Cases yang Ditangani

| Kondisi | Penanganan |
|---------|-----------|
| PII di level root dict | Langsung dihapus |
| PII di nested dict | Rekursi memastikan field dihapus di level manapun |
| PII di dalam list | Rekursi ke setiap elemen list |
| PII di list dalam dict dalam list | Rekursi penuh hingga level terdalam |
| Dict kosong `{}` | Dikembalikan sebagai `{}` (tidak error) |
| List kosong `[]` | Dikembalikan sebagai `[]` (tidak error) |
| Scalar value (string, int, None) | Pass-through tanpa modifikasi |

---

## Struktur Kode

```python
# backend/shared/pii_filter.py

PII_FIELDS: frozenset[str] = frozenset({
    "nama_lengkap",
    "nomor_rekening",
    "nomor_identitas",
    "alamat_lengkap",
})
# Konstanta immutable yang mendefinisikan semua field PII yang harus dihapus

def strip_pii(data: dict[str, Any] | list[Any]) -> dict[str, Any] | list[Any]:
    """
    Menghapus semua field PII dari data secara rekursif.
    Mengembalikan salinan baru tanpa memodifikasi input.
    
    - list → rekursi ke setiap elemen
    - dict → buang key yang ada di PII_FIELDS, rekursi ke value
    - scalar → pass-through (basis rekursi)
    """

def has_pii(data: dict[str, Any] | list[Any]) -> bool:
    """
    Memeriksa apakah data mengandung field PII di level manapun.
    Berguna untuk testing dan assertion post-strip.
    
    - list → cek setiap elemen (short-circuit jika ditemukan)
    - dict → cek setiap key, rekursi ke value jika perlu
    - scalar → selalu False (basis rekursi)
    """
```

### Alur Eksekusi `strip_pii`

```
strip_pii(data)
│
├── isinstance(data, list)?
│   └── return [strip_pii(item) for item in data]
│
├── isinstance(data, dict)?
│   └── return {
│           key: strip_pii(value)
│           for key, value in data.items()
│           if key not in PII_FIELDS   ← filter di sini
│       }
│
└── else (scalar)
    └── return data  ← basis rekursi
```

---

## Simulasi / Skenario

### Skenario 1 — Strip PII dari Response Sederhana

**Konteks:** Lambda `customer_criteria` menghasilkan summary data leads. Sebelum dikembalikan ke API Gateway, `strip_pii` dijalankan.

```python
from shared.pii_filter import strip_pii

# Data sebelum strip (dari query hasil join dengan monitoring report)
raw_response = {
    "campaign_id": "QRIS-2024-08",
    "nama_program": "PROGRAM QRIS Agustus 2024",
    "nama_lengkap": "Budi Santoso",           # ← PII
    "nomor_rekening": "1234567890",            # ← PII
    "segment_by_aum": "AFFLUENT",
    "wilayah": 1,
    "take_up_flag": "YES",
}

# Proses
cleaned = strip_pii(raw_response)

# Output
print(cleaned)
# {
#   "campaign_id": "QRIS-2024-08",
#   "nama_program": "PROGRAM QRIS Agustus 2024",
#   "segment_by_aum": "AFFLUENT",
#   "wilayah": 1,
#   "take_up_flag": "YES"
# }
```

`nama_lengkap` dan `nomor_rekening` hilang. Field lain tetap utuh.

---

### Skenario 2 — Strip PII dari List of Leads

**Konteks:** Response customer criteria berisi list banyak nasabah. `strip_pii` bekerja pada seluruh list sekaligus.

```python
from shared.pii_filter import strip_pii

leads = [
    {
        "cif": "C001",
        "nama_lengkap": "Siti Rahayu",        # ← PII
        "nomor_identitas": "3271234567890001", # ← PII
        "segment_by_aum": "MASS",
        "wilayah": 5,   # Bandung
        "take_up_flag": "YES",
    },
    {
        "cif": "C002",
        "nama_lengkap": "Ahmad Fauzi",         # ← PII
        "alamat_lengkap": "Jl. Merdeka No. 1", # ← PII
        "segment_by_aum": "EMERALD",
        "wilayah": 11,  # Surabaya
        "take_up_flag": "NO",
    },
]

cleaned = strip_pii(leads)

# Output:
# [
#   {"cif": "C001", "segment_by_aum": "MASS",    "wilayah": 5,  "take_up_flag": "YES"},
#   {"cif": "C002", "segment_by_aum": "EMERALD", "wilayah": 11, "take_up_flag": "NO"},
# ]
```

Semua field `nama_lengkap`, `nomor_identitas`, dan `alamat_lengkap` hilang dari kedua elemen list.

---

### Skenario 3 — Strip PII dari Struktur Nested (Deep Recursion)

**Konteks:** Response yang kompleks memiliki nested structure. `strip_pii` tetap menemukan dan menghapus PII di semua level.

```python
from shared.pii_filter import strip_pii

nested_response = {
    "campaign_id": "QRIS-2024-08",
    "summary": {
        "total_leads": 1000,
        "total_take_up": 87,
    },
    "top_lead": {
        "cif": "C001",
        "nama_lengkap": "Dewi Lestari",        # ← PII di level 2
        "segment_by_aum": "AFFLUENT",
        "detail": {
            "nomor_rekening": "9876543210",    # ← PII di level 3
            "avg_aum_3_bln": 150000000.0,
        }
    }
}

cleaned = strip_pii(nested_response)

# Output:
# {
#   "campaign_id": "QRIS-2024-08",
#   "summary": {"total_leads": 1000, "total_take_up": 87},
#   "top_lead": {
#     "cif": "C001",
#     "segment_by_aum": "AFFLUENT",
#     "detail": {
#       "avg_aum_3_bln": 150000000.0
#       # "nomor_rekening" sudah terhapus dari level 3
#     }
#   }
# }
```

---

### Skenario 4 — Verifikasi dengan `has_pii`

**Konteks:** Unit test memverifikasi bahwa `strip_pii` benar-benar membersihkan data.

```python
from shared.pii_filter import strip_pii, has_pii

raw = {
    "nama_lengkap": "Rizky Pratama",
    "nomor_identitas": "3175012345678901",
    "segment_by_aum": "MASS",
}

# Sebelum strip — ada PII
assert has_pii(raw) == True

# Setelah strip — PII sudah bersih
cleaned = strip_pii(raw)
assert has_pii(cleaned) == False

# Verifikasi field yang tersisa
assert "segment_by_aum" in cleaned
assert "nama_lengkap" not in cleaned
assert "nomor_identitas" not in cleaned

print("✅ PII berhasil dibersihkan")
```

---

### Skenario 5 — Data yang Sudah Bersih (Idempotent)

**Konteks:** `strip_pii` dipanggil dua kali pada data yang sama (defensive coding). Hasilnya tetap konsisten.

```python
from shared.pii_filter import strip_pii

data = {"campaign_id": "QRIS-2024-08", "total_leads": 1000}

# Panggil dua kali — hasilnya tetap sama
result1 = strip_pii(data)
result2 = strip_pii(result1)

assert result1 == result2  # ← idempotent
print(result2)  # {"campaign_id": "QRIS-2024-08", "total_leads": 1000}
```

`strip_pii` adalah operasi idempotent: memanggilnya berkali-kali pada data yang sudah bersih tidak merusak apapun.

---

## Keterkaitan dengan Komponen Lain

### Bergantung pada:
- Tidak ada dependensi internal proyek
- `typing.Any` dari Python standard library

### Digunakan oleh:
| Komponen | Cara Penggunaan |
|----------|----------------|
| `lambdas/campaign_overview/handler.py` | `strip_pii(response_dict)` sebelum return |
| `lambdas/campaign_comparison/handler.py` | `strip_pii(response_dict)` sebelum return |
| `lambdas/time_analysis/handler.py` | `strip_pii(response_dict)` sebelum return |
| `lambdas/regional_performance/handler.py` | `strip_pii(response_dict)` sebelum return |
| `lambdas/customer_criteria/handler.py` | `strip_pii(leads_list)` — response ini paling rentan PII |
| `lambdas/similar_campaign/handler.py` | `strip_pii(response_dict)` sebelum return |
| `lambdas/export_service/handler.py` | `strip_pii(export_data)` sebelum generate file |
| `tests/unit/test_pii_filter.py` | Test `strip_pii` dan `has_pii` |

### Pengaruh ke:
- Menambahkan field baru ke `PII_FIELDS` akan langsung memengaruhi semua Lambda — field tersebut akan hilang dari semua API response tanpa perubahan kode lain.
- Menghapus field dari `PII_FIELDS` adalah operasi **berisiko tinggi** — field yang sebelumnya tersembunyi akan tiba-tiba muncul di semua response. Harus dikonfirmasi dengan tim compliance dan data protection officer.
- `has_pii` bergantung pada nilai `PII_FIELDS` yang sama — perubahan ke `PII_FIELDS` otomatis berlaku di keduanya.

---

## Requirements yang Dipenuhi

| Requirement | Deskripsi |
|-------------|-----------|
| **7.5** | Semua API response harus bebas dari data PII nasabah |
| **7.6** | PII stripping berlaku untuk semua role pengguna tanpa pengecualian |

---

## Catatan Penting

### Limitasi yang Diketahui
1. **`PII_FIELDS` di `pii_filter.py` ≠ `PII_FIELDS` di `models.py`** — Ada dua definisi yang saling melengkapi. `models.py` mendefinisikan `{"cif"}` (field PII di data model LeadRecord), sementara `pii_filter.py` mendefinisikan 4 field tambahan. Ini perlu dikelola dengan hati-hati agar tidak ada inkonsistensi.
2. **Tidak ada handling untuk tuple** — Jika ada struktur data yang menggunakan `tuple` (bukan `list`), `strip_pii` akan memperlakukannya sebagai scalar dan tidak merekursi ke dalamnya. Konversi ke `list` perlu dilakukan sebelumnya jika diperlukan.
3. **Key-matching bersifat exact dan case-sensitive** — `"Nama_Lengkap"` atau `"NAMA_LENGKAP"` tidak akan terdeteksi sebagai PII. Normalisasi case di ETL layer sangat direkomendasikan.
4. **Performa pada dataset besar** — Rekursi Python memiliki stack limit (~1000 level). Untuk data dengan kedalaman nesting yang sangat dalam (>100 level), bisa terjadi `RecursionError`. Dalam praktik, data campaign tidak pernah sedalam itu.

### Asumsi yang Dibuat
- Semua data yang masuk ke Lambda handler sudah dalam bentuk Python dict/list standar (sudah di-deserialize dari JSON).
- `strip_pii` selalu dipanggil sebagai operasi terakhir sebelum data di-serialize kembali ke JSON untuk response.
- Data yang berupa scalar (string yang panjang seperti JSON string) tidak diproses lebih lanjut — tidak ada parsing string JSON di dalam rekursi.

### Kebijakan Keamanan Tambahan
- `strip_pii` **wajib** dipanggil di setiap Lambda handler sebelum `return`. Ini bukan opsional.
- Unit test di `tests/unit/test_pii_filter.py` harus selalu dijalankan dalam CI/CD pipeline.
- Saat menambahkan field baru ke `LeadRecord` di `models.py`, **periksa dulu** apakah field tersebut termasuk PII dan perlu ditambahkan ke `PII_FIELDS` di `pii_filter.py`.

### Todo untuk Pengembangan Berikutnya
- [ ] Sinkronisasi `PII_FIELDS` antara `pii_filter.py` dan `models.py` — pertimbangkan mengimpor dari satu sumber kebenaran tunggal.
- [ ] Tambahkan support untuk `tuple` dalam rekursi.
- [ ] Tambahkan fungsi `mask_pii` sebagai alternatif `strip_pii` yang mengganti nilai PII dengan placeholder (`"***"`) alih-alih menghapus key-nya — berguna untuk logging dan audit trail.
- [ ] Pertimbangkan penggunaan `itertools.chain` atau iterasi iteratif untuk menghindari `RecursionError` pada edge case data yang sangat dalam.
