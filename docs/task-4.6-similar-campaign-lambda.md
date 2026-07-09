# Task 4.6 — Similar Campaign Lambda

## Ringkasan Singkat

Lambda handler ini melayani endpoint `POST /api/campaigns/similar` yang mencari kampanye-kampanye historis yang **mirip** dengan kampanye referensi berdasarkan dimensi tertentu. Dimensi yang didukung adalah `flag_program` (jenis produk), `media_blasting` (channel distribusi), dan `jenis_leads` (tujuan leads). Handler ini membaca dari tabel DynamoDB `CampaignSimilarityIndex` yang sudah di-pre-compute oleh ETL, memfilter kampanye yang cocok di **semua** dimensi yang diminta, lalu mengurutkannya dari yang paling relevan ke yang paling tidak relevan. Hasilnya disertai `learning_summary` berupa ringkasan insight dari kampanye teratas.

---

## Penjelasan Awam (Non-Technical)

Bayangkan seseorang baru saja selesai menjalankan kampanye QRIS Juli 2024 dan ingin merancang kampanye QRIS Agustus 2024. Mereka ingin tahu: **"Kampanye mana saja yang pernah kita jalankan dengan cara yang mirip, dan seberapa berhasil mereka?"**

Handler ini bekerja seperti mesin rekomendasi yang:
1. Menerima nama kampanye referensi dan kriteria yang ingin disamakan (misal: pakai channel yang sama, jenis produk yang sama)
2. Mencari di arsip semua kampanye historis yang memenuhi kriteria tersebut
3. Mengurutkan hasilnya: yang paling banyak kesamaannya muncul pertama; jika sama, yang punya hasil terbaik muncul di atas
4. Menyertakan ringkasan pembelajaran: "kampanye paling mirip ini punya tingkat keberhasilan sekian persen"

**Analogi kehidupan nyata:** Seperti fitur "Film yang Mungkin Kamu Suka" di Netflix — sistem melihat genre, sutradara, dan aktor yang kamu sukai, lalu merekomendasikan film serupa yang sudah terbukti disukai penonton lain.

**Manfaat bisnis:**
- Campaign Planner bisa belajar dari kampanye historis sebelum membuat keputusan baru
- Mengurangi trial-and-error dengan memanfaatkan pengalaman masa lalu
- Memberikan benchmark realistis: "Jika kita pakai strategi serupa, ekspektasi take_up_rate sekitar sekian persen"

---

## Penjelasan Teknis

### File yang Terlibat

| File | Peran |
|------|-------|
| `backend/lambdas/similar_campaign/handler.py` | Entry point Lambda, orkestrasi utama |
| `backend/shared/models.py` | Dataclass `SimilarCampaignRequest`, `SimilarCampaignResult`, `SimilarCampaignResponse`; konstanta `SIMILAR_CAMPAIGN_DIMENSIONS` |
| `backend/shared/sorting.py` | Fungsi `sort_similar_campaigns()` |
| DynamoDB tabel `CampaignSimilarityIndex` | Sumber data yang sudah di-pre-compute oleh ETL Glue job |

### Library / Framework

- **AWS Lambda** — serverless compute
- **Amazon DynamoDB** — NoSQL database untuk similarity index yang sudah pre-computed
- `boto3` → `boto3.resource("dynamodb")` — AWS SDK untuk query DynamoDB
- `boto3.dynamodb.conditions.Key` — query KeyConditionExpression
- `dataclasses.asdict` — konversi dataclass ke dict untuk serialisasi JSON
- `shared.models.SimilarCampaignResult`, `SimilarCampaignResponse` — model data terstruktur
- `shared.sorting.sort_similar_campaigns` — sorting berdasarkan dimensi dan take_up_rate

### Pola Arsitektur

- **Lambda Proxy Integration** dengan API Gateway
- **Pre-computed index pattern**: tidak ada query Athena real-time; data sudah di-denormalize di DynamoDB oleh ETL
- **POST dengan body JSON**: berbeda dari handler lain yang pakai GET + path parameter
- **Pagination handling**: handler menangani `LastEvaluatedKey` dari DynamoDB secara otomatis

### Tiga Dimensi Kesamaan yang Didukung

```python
SIMILAR_CAMPAIGN_DIMENSIONS: frozenset[str] = frozenset({
    "media_blasting",  # Channel distribusi (WA, email, telesales, dll)
    "jenis_leads",     # Tujuan leads (Migrasi, Akuisisi, dll)
    "flag_program",    # Jenis produk (PROGRAM QRIS, PROGRAM BIAYA ADMIN)
})
```

### Alur Eksekusi (10 Langkah)

```
1. Parse JSON body → ekstrak reference_campaign_id, dimensions, limit
2. Validasi: reference_campaign_id tidak boleh kosong
3. Validasi: dimensions tidak boleh kosong
4. Validasi: setiap nilai di dimensions harus ada di SIMILAR_CAMPAIGN_DIMENSIONS
5. Buat SimilarCampaignRequest dari payload (validasi limit di __post_init__)
6. Query DynamoDB: KeyConditionExpression(campaign_id == reference_id), handle pagination
7. Filter: hanya item yang matching_dimensions ⊇ requested_dims (ALL dims harus cocok)
8. Konversi DynamoDB items → list[SimilarCampaignResult] via _to_int/_to_float
9. Sort via sort_similar_campaigns(): dimension_count DESC, take_up_rate DESC
10. Apply limit (min(request.limit, 20)) → build learning_summary → return 200
```

### Logika Filter Dimensi (Langkah 7)

```python
# "Subset check" — semua dimensi yang diminta harus ada di matching_dimensions item
requested_dims_set: set[str] = set(request.dimensions)

filtered_items = [
    item
    for item in items
    if requested_dims_set.issubset(set(item.get("matching_dimensions", [])))
]
```

**Contoh:** Jika request dimensions = `["flag_program", "media_blasting"]`, maka:
- Item dengan `matching_dimensions: ["flag_program", "media_blasting", "jenis_leads"]` → ✅ lolos
- Item dengan `matching_dimensions: ["flag_program"]` → ❌ tidak lolos (tidak punya `media_blasting`)
- Item dengan `matching_dimensions: ["media_blasting"]` → ❌ tidak lolos (tidak punya `flag_program`)

### Fungsi `_build_learning_summary()`

```python
def _build_learning_summary(top: SimilarCampaignResult) -> dict[str, Any]:
    """
    Membuat ringkasan pembelajaran dari kampanye teratas.
    
    Untuk MVP, hanya take_up_rate yang tersedia dari DynamoDB similarity index.
    top_segment dan top_region dikembalikan "N/A" karena data tersebut
    tidak ada di index — perlu Athena join untuk mendapatkannya.
    """
    return {
        "take_up_rate_formatted": f"{top.take_up_rate:.2f}%",
        "top_segment": "N/A",    # MVP limitation
        "top_region": "N/A",     # MVP limitation
    }
```

### Keputusan Desain Penting

| Keputusan | Alasan |
|-----------|--------|
| Menggunakan DynamoDB bukan Athena | Pencarian similarity adalah query yang sering dipanggil; DynamoDB pre-computed lebih cepat (<50ms vs minutes Athena) |
| Filter ALL dimensions (bukan ANY) | Kebutuhan bisnis: kampanye serupa harus cocok di **semua** dimensi yang diminta, bukan salah satu |
| Pagination DynamoDB di-handle otomatis | DynamoDB membatasi response per halaman; harus loop `LastEvaluatedKey` untuk data lengkap |
| Limit maksimum = 20 (`_MAX_RESULTS`) | Mencegah response terlalu besar; 20 kampanye sudah cukup untuk reference |
| `top_segment` dan `top_region` = "N/A" (MVP) | DynamoDB index tidak menyimpan breakdown segment/region; memerlukan Athena join terpisah yang mahal |
| Empty result → HTTP 200 (bukan 404) | Tidak ada yang salah jika tidak ada kampanye serupa; frontend perlu tahu agar tampilkan state kosong |

### Edge Cases yang Ditangani

- Body request null / tidak ada → HTTP 400
- Body bukan valid JSON → HTTP 400
- `reference_campaign_id` kosong → HTTP 400
- `dimensions` kosong (array kosong atau tidak ada) → HTTP 400
- Dimensi tidak dikenali (misal `"tipe_nasabah"`) → HTTP 400 dengan daftar yang valid
- `limit` invalid (ValueError/TypeError dari `SimilarCampaignRequest.__post_init__`) → HTTP 400
- Tidak ada kampanye serupa ditemukan → HTTP 200 dengan array kosong dan pesan Bahasa Indonesia
- DynamoDB pagination → di-handle otomatis dengan loop `LastEvaluatedKey`
- Nilai DynamoDB non-numerik → `_to_int()`/`_to_float()` mengembalikan 0/0.0 (tidak crash)

---

## Struktur Kode

### Fungsi Publik

```python
def lambda_handler(event: dict, context: object) -> dict[str, Any]:
    """Entry point. POST body → validasi → DynamoDB query → filter → sort → response."""
```

### Fungsi Helper Privat

```python
def _response(status_code: int, body: dict[str, Any]) -> dict[str, Any]:
    """Membuat Lambda Proxy Integration response dict."""

def _to_float(value: Any) -> float:
    """Konversi aman DynamoDB Decimal/string ke float. Mengembalikan 0.0 jika gagal.
    DynamoDB Decimal tidak langsung kompatibel dengan float Python."""

def _to_int(value: Any) -> int:
    """Konversi aman DynamoDB Decimal/string ke int. Mengembalikan 0 jika gagal."""

def _build_learning_summary(top: SimilarCampaignResult) -> dict[str, Any]:
    """Membuat ringkasan pembelajaran dari kampanye teratas untuk ditampilkan di UI."""
```

### Konstanta

```python
_CONTENT_TYPE_JSON: str = "application/json"  # Header Content-Type
_MAX_RESULTS: int = 20                         # Batas maksimum hasil yang dikembalikan
```

### Model Data yang Digunakan

```python
# Dari shared/models.py
SimilarCampaignRequest:
    reference_campaign_id: str
    dimensions: list[Literal["media_blasting", "jenis_leads", "flag_program"]]
    limit: Optional[int] = 20  # default 20, maksimum 20

SimilarCampaignResult:
    campaign_id: str
    campaign_name: str
    matching_dimensions: list[str]
    dimension_count: int           # jumlah dimensi yang cocok
    similarity_score: float        # skor [0.0, 1.0] dari ETL
    take_up_rate: float            # take_up_rate kampanye ini (%)
    total_leads: int
    total_take_up: int

SimilarCampaignResponse:
    similar_campaigns: list[SimilarCampaignResult]
```

### Dependency Eksternal

```python
import boto3
from boto3.dynamodb.conditions import Key
from shared.models import SIMILAR_CAMPAIGN_DIMENSIONS, SimilarCampaignRequest, ...
from shared.sorting import sort_similar_campaigns
```

---

## Simulasi / Skenario

### Skenario 1 — Happy Path: 5 Kampanye Serupa Ditemukan

**Input (API Gateway Event):**
```json
{
  "body": "{\"reference_campaign_id\": \"QRIS-AUG-2024\", \"dimensions\": [\"flag_program\", \"media_blasting\"], \"limit\": 5}"
}
```

**Request yang diparsed:**
```python
SimilarCampaignRequest(
    reference_campaign_id="QRIS-AUG-2024",
    dimensions=["flag_program", "media_blasting"],
    limit=5
)
```

**DynamoDB Query** — `campaign_id == "QRIS-AUG-2024"`:
```
Returned 12 items total (dengan pagination DynamoDB)
```

**Setelah Filter** (harus punya KEDUA dimensi):
```
5 item lolos dari 12 item total
```

**Setelah Sort** (`dimension_count` DESC, `take_up_rate` DESC):
```
1. QRIS-JUL-2024     → dimension_count: 2, take_up_rate: 9.2%
2. QRIS-JUN-2024     → dimension_count: 2, take_up_rate: 8.7%
3. QRIS-MEI-2024     → dimension_count: 2, take_up_rate: 7.9%
4. QRIS-APR-2024     → dimension_count: 2, take_up_rate: 7.1%
5. QRIS-MAR-2024     → dimension_count: 2, take_up_rate: 6.5%
```

**Output (HTTP 200):**
```json
{
  "similar_campaigns": [
    {
      "campaign_id": "QRIS-JUL-2024",
      "campaign_name": "QRIS Juli 2024",
      "matching_dimensions": ["flag_program", "media_blasting"],
      "dimension_count": 2,
      "similarity_score": 0.91,
      "take_up_rate": 9.2,
      "total_leads": 8500,
      "total_take_up": 782
    },
    {
      "campaign_id": "QRIS-JUN-2024",
      "campaign_name": "QRIS Juni 2024",
      "matching_dimensions": ["flag_program", "media_blasting"],
      "dimension_count": 2,
      "similarity_score": 0.87,
      "take_up_rate": 8.7,
      "total_leads": 7900,
      "total_take_up": 688
    }
  ],
  "learning_summary": {
    "take_up_rate_formatted": "9.20%",
    "top_segment": "N/A",
    "top_region": "N/A"
  }
}
```

**Interpretasi:** Kampanye QRIS Juli 2024 adalah yang paling mirip dan paling berhasil (9.2%). Ini bisa menjadi benchmark: jika strategi yang sama diulang di Agustus, target realistis adalah sekitar 9.2% take_up_rate.

---

### Skenario 2 — Tidak Ada Kampanye Serupa

Tidak ada kampanye di DynamoDB yang memiliki kedua dimensi `["flag_program", "jenis_leads"]` sekaligus.

**Output (HTTP 200):**
```json
{
  "similar_campaigns": [],
  "message": "Tidak ada campaign serupa ditemukan. Coba perluas dimensi pencarian."
}
```

**Tindak lanjut yang disarankan:** Pengguna dapat mencoba dengan hanya satu dimensi saja (misal hanya `["flag_program"]`).

---

### Skenario 3 — Dimensi Tidak Valid

**Input body:**
```json
{
  "reference_campaign_id": "QRIS-AUG-2024",
  "dimensions": ["flag_program", "tipe_nasabah"]
}
```

**Output (HTTP 400):**
```json
{
  "error": "Invalid dimension(s): ['tipe_nasabah']. Allowed values: ['flag_program', 'jenis_leads', 'media_blasting']."
}
```

---

### Skenario 4 — Body Tidak Ada

**Input:** Event tanpa field `body` (misalnya di-test langsung tanpa API Gateway).

**Output (HTTP 400):**
```json
{
  "error": "Request body is required."
}
```

---

### Skenario 5 — Limit Lebih dari 20

**Input:**
```json
{
  "reference_campaign_id": "QRIS-AUG-2024",
  "dimensions": ["flag_program"],
  "limit": 50
}
```

**Proses:** `effective_limit = min(50, 20) = 20` — maksimum tetap 20 meskipun request meminta 50.

**Output:** Maksimum 20 kampanye dikembalikan.

---

### Skenario 6 — Tiga Dimensi Sekaligus

**Input:**
```json
{
  "reference_campaign_id": "QRIS-AUG-2024",
  "dimensions": ["flag_program", "media_blasting", "jenis_leads"]
}
```

**Proses:** Hanya kampanye yang cocok di **ketiga** dimensi sekaligus yang lolos filter.

**Output:** Kemungkinan hasil lebih sedikit karena kriteria lebih ketat. Jika hasilnya 0, muncul pesan untuk perluas dimensi.

---

## Keterkaitan dengan Komponen Lain

### Bergantung Pada

| Komponen | Ketergantungan |
|----------|----------------|
| DynamoDB tabel `CampaignSimilarityIndex` | Sumber data utama; harus sudah di-populate oleh ETL sebelum endpoint ini bisa digunakan |
| `shared/models.py` → `SimilarCampaignRequest`, `SimilarCampaignResult`, `SimilarCampaignResponse` | Validasi dan struktur data |
| `shared/models.py` → `SIMILAR_CAMPAIGN_DIMENSIONS` | Konstanta untuk validasi dimensi yang valid |
| `shared/sorting.py` → `sort_similar_campaigns()` | Pengurutan berdasarkan `dimension_count` DESC + `take_up_rate` DESC |
| `boto3.resource("dynamodb")` | AWS SDK untuk query DynamoDB |
| Environment variable `SIMILARITY_TABLE` | Nama tabel DynamoDB (default: `"CampaignSimilarityIndex"`) |
| Environment variable `AWS_REGION` | Region AWS |

### Digunakan Oleh

| Komponen | Penggunaan |
|----------|------------|
| API Gateway | Route `POST /api/campaigns/similar` diarahkan ke Lambda ini |
| CDK ApiStack | Mendefinisikan Lambda function dan POST route |
| Frontend halaman Similar Campaign | Konsumsi data untuk menampilkan daftar kampanye rekomendasi + learning summary |
| Glue ETL job `similarity_index` (task 7.3) | Mengisi tabel `CampaignSimilarityIndex` yang diquery oleh handler ini — dependency tidak langsung tapi kritis |

### Pengaruh Jika Berubah

- Penambahan dimensi baru ke `SIMILAR_CAMPAIGN_DIMENSIONS` → validasi langsung berubah; ETL juga perlu diupdate untuk mengisi dimensi baru
- Perubahan `sort_similar_campaigns()` → urutan ranking kampanye serupa berubah
- Perubahan skema DynamoDB (nama attribute) → konversi di step 8 perlu diupdate
- Perubahan konstanta `_MAX_RESULTS` → batas jumlah hasil berubah
- Pengembangan `_build_learning_summary()` untuk join Athena → response kaya informasi tapi latency meningkat
- Perubahan nama tabel DynamoDB (environment variable `SIMILARITY_TABLE`) → pastikan CDK stack dan Lambda env var konsisten

---

## Requirements yang Dipenuhi

| Requirement | Deskripsi |
|-------------|-----------|
| **6.1** | Pencarian kampanye serupa berdasarkan dimensi yang dipilih pengguna |
| **6.2** | Validasi dimensi — hanya `media_blasting`, `jenis_leads`, `flag_program` yang valid |
| **6.3** | Filter subset: semua dimensi yang diminta harus cocok (bukan hanya salah satu) |
| **6.4** | `learning_summary` untuk kampanye teratas: take_up_rate_formatted, top_segment, top_region |
| **6.5** | Graceful handling ketika tidak ada kampanye serupa — pesan Bahasa Indonesia + saran perluas dimensi |

---

## Catatan Penting

### Limitasi yang Diketahui

1. **`top_segment` dan `top_region` selalu "N/A" di MVP** — DynamoDB similarity index tidak menyimpan breakdown segment dan region dari kampanye historis. Untuk mendapatkan data ini, diperlukan query tambahan ke Athena (`leads` table) per kampanye yang ditemukan, yang akan meningkatkan latency secara signifikan. Ini adalah trade-off yang disengaja untuk MVP.

2. **Data bergantung pada ETL Glue job `similarity_index`** — jika ETL belum jalan atau gagal, tabel DynamoDB kosong dan endpoint ini selalu mengembalikan array kosong. Tidak ada indikator "data stale" di response.

3. **Filter dilakukan di Python (in-memory)** — seluruh data `campaign_id == reference_id` diambil dari DynamoDB, baru difilter. Jika satu kampanye referensi punya ribuan entry, ini bisa boros memori. Untuk skala besar, pertimbangkan GSI DynamoDB dengan composite key yang menyertakan dimensi.

4. **`dimensions` adalah AND** — tidak ada opsi OR (cocok minimal 1 dari N). Jika pengguna ingin OR, perlu endpoint berbeda atau parameter tambahan.

5. **`similarity_score` dari ETL** — cara ETL menghitung skor ini tidak didokumentasikan di handler; handler hanya menyimpan dan mengembalikan nilainya tanpa rekalkulasi.

### Asumsi yang Dibuat

- DynamoDB `CampaignSimilarityIndex` menggunakan `campaign_id` sebagai partition key
- Setiap item di DynamoDB memiliki field: `similar_campaign_id`, `campaign_name`, `matching_dimensions` (list), `dimension_count`, `similarity_score`, `take_up_rate`, `total_leads`, `total_take_up`
- ETL Glue job `similarity_index` (task 7.3) sudah berjalan dan mengisi tabel sebelum endpoint ini digunakan
- `SimilarCampaignRequest.__post_init__` di `models.py` melakukan validasi tambahan pada `limit` jika perlu

### Todo untuk Pengembangan Berikutnya

- [ ] Implementasi `top_segment` dan `top_region` via Athena join (post-MVP)
- [ ] Tambahkan parameter `match_type: "ALL" | "ANY"` untuk mendukung OR logic antar dimensi
- [ ] Tambahkan field `data_freshness` / `last_updated` di response agar pengguna tahu kapan index terakhir di-refresh
- [ ] Pertimbangkan DynamoDB GSI dengan composite key untuk filtering lebih efisien di level database
- [ ] Tambahkan unit test untuk skenario DynamoDB pagination (mock `LastEvaluatedKey`)
- [ ] Pertimbangkan caching (ElastiCache atau DynamoDB DAX) untuk request yang sama dari pengguna berbeda
- [ ] Audit apakah `similarity_score` dari ETL perlu dijelaskan cara kalkulasinya di dokumentasi ETL
