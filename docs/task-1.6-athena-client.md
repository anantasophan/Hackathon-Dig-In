# Task 1.6 — Athena Query Helper

## Ringkasan Singkat

File `backend/shared/athena_client.py` mengimplementasikan class `AthenaClient` — sebuah wrapper di atas layanan AWS Athena yang menangani semua kebutuhan query data untuk Campaign Insight Generator. Modul ini menyediakan mekanisme eksekusi query dengan polling otomatis, pembangunan SQL yang aman dari injection, dan lima query builder yang masing-masing melayani satu analytical view (overview, perbandingan, regional, analisis waktu, dan kriteria nasabah). Semua Lambda handler backend menggunakan modul ini sebagai satu-satunya jalur akses ke data kampanye.

---

## Penjelasan Awam (Non-Technical)

### Apa itu Amazon Athena?

Bayangkan kamu punya **gudang data raksasa** berisi jutaan baris rekaman nasabah dan kampanye bank — tersimpan di hard disk virtual di cloud (Amazon S3). Biasanya, untuk mencari data di sana, kamu butuh sebuah server database yang terus menyala 24 jam dan harus dirawat.

**Amazon Athena** menghilangkan kebutuhan itu. Kamu cukup menulis pertanyaan dalam bahasa SQL ("tampilkan semua leads kampanye QRIS bulan Januari"), Athena membacakan langsung dari gudang data tersebut, menjawab pertanyaanmu, lalu selesai — tanpa server permanen yang harus dibayar terus-menerus.

Analoginya: seperti jasa **fotokopi kilat**. Kamu datang, berikan dokumen yang ingin difotokopi (pertanyaan SQL-mu), tunggu sebentar, ambil hasilnya, lalu pulang. Tidak perlu beli mesin fotokopi sendiri.

### Bagaimana AthenaClient Bekerja?

`AthenaClient` adalah petugas yang duduk di depan mesin Athena tersebut. Tugasnya:

1. **Menerima pertanyaan** dari sistem (misalnya: "ambil data performa kampanye QRIS di Jakarta")
2. **Menerjemahkan pertanyaan** ke bahasa SQL yang Athena pahami, dengan cara yang aman
3. **Mengirim pertanyaan** ke Athena dan **menunggu jawaban** (proses ini bisa makan waktu beberapa detik)
4. **Mengambil jawaban** dan merapikannya agar mudah digunakan oleh sistem lain
5. **Memberitahu** jika terjadi masalah (timeout, query gagal, dll.)

Manfaat bagi pengguna bisnis: laporan di dashboard dijamin datanya berasal dari data yang sama persis seperti yang ada di data warehouse bank, tanpa risiko salah hitung akibat copy-paste data.

---

## Penjelasan Teknis

**File:** `backend/shared/athena_client.py`

**Library yang digunakan:**
- `boto3` — AWS SDK untuk Python; digunakan untuk memanggil API Athena (`start_query_execution`, `get_query_execution`, `get_query_results`, `stop_query_execution`)
- `time` — fungsi `time.sleep()` untuk polling interval
- `shared.models` — mengimpor `CampaignOverviewRequest` sebagai tipe parameter

**Pola arsitektur:**
- **Polling loop** — karena Athena bersifat asynchronous (query dijalankan di background), `AthenaClient` menerapkan polling aktif setiap 1 detik hingga query selesai atau timeout 30 detik tercapai
- **Query builder pattern** — setiap analytical view memiliki method builder tersendiri (`build_campaign_overview_query`, dst.) alih-alih satu method generik, sehingga struktur SQL tetap terkontrol dan mudah diuji
- **Parameterized query via manual substitution** — Athena tidak mendukung native bind parameters, sehingga `_bind_params` mengimplementasikan substitusi placeholder `:name` dengan quoting yang aman
- **Pagination** — `_fetch_results` menggunakan mekanisme `NextToken` untuk mengambil seluruh hasil bahkan jika melebihi satu halaman

**Keputusan desain penting:**
- Timeout 30 detik dipilih sebagai keseimbangan antara memberi waktu cukup untuk query kompleks dan tidak membiarkan request Lambda menggantung terlalu lama (Lambda timeout biasanya 60 detik)
- Saat timeout terjadi, sistem **mencoba membatalkan** query Athena yang masih berjalan (`stop_query_execution`) untuk menghindari "orphaned query" yang tetap berjalan dan menghabiskan biaya
- Column names diambil dari baris pertama result set Athena (header row), bukan dari schema metadata, untuk menyederhanakan kode
- Helper `_quote`, `_in_clause`, `_bind_params` dijadikan fungsi module-level (bukan method class) agar bisa diuji secara independen

**Edge cases yang ditangani:**
- `_in_clause` dengan list kosong menghasilkan `(1 = 0)` — kondisi yang selalu false — daripada SQL tidak valid atau query yang mengembalikan semua baris
- `_bind_params` mengurutkan key dari yang terpanjang dulu untuk menghindari collision prefix (misal `:id` tidak boleh menggantikan bagian dari `:id_list`)
- Boolean dalam params (`True`/`False`) diubah ke `true`/`false` (bukan `1`/`0`) sesuai sintaks Presto/Athena
- `_quote` menggunakan doubling single-quote (`'O''Brien'`) yang merupakan standar SQL, bukan backslash escape

---

## Struktur Kode

### Konstanta

```python
_POLL_INTERVAL_SECONDS: float = 1.0   # Jeda antar polling (detik)
_QUERY_TIMEOUT_SECONDS: int = 30      # Batas waktu maksimum tunggu query

_SUCCEEDED: str = "SUCCEEDED"
_FAILED: str = "FAILED"
_CANCELLED: str = "CANCELLED"
_TERMINAL_STATES: frozenset[str] = frozenset({_SUCCEEDED, _FAILED, _CANCELLED})
```

---

### Custom Exceptions

```python
class QueryTimeoutError(Exception):
    """Query tidak selesai dalam 30 detik."""
    def __init__(self, query_execution_id: str, timeout_seconds: int) -> None:
        self.query_execution_id = query_execution_id
        self.timeout_seconds = timeout_seconds
        # Pesan: "Athena query 'abc-123' did not complete within 30 seconds."

class QueryExecutionError(Exception):
    """Athena melaporkan status FAILED atau CANCELLED."""
    def __init__(
        self, query_execution_id: str, state: str, reason: str = ""
    ) -> None:
        self.query_execution_id = query_execution_id
        self.state = state    # "FAILED" atau "CANCELLED"
        self.reason = reason  # Pesan error dari Athena, jika ada
```

---

### `AthenaClient.__init__`

```python
def __init__(
    self,
    database: str,              # Nama database Athena, misal "campaign_db"
    s3_output_location: str,    # URI S3 untuk menyimpan hasil, misal "s3://bucket/results/"
    region_name: str | None = None,  # AWS region; None = ikuti environment
    workgroup: str = "primary", # Athena workgroup
) -> None:
```

---

### `execute_query` — Eksekusi Query dengan Polling

```python
def execute_query(
    self,
    sql: str,                          # SQL dengan placeholder :name
    params: dict[str, Any] | None = None,  # Nilai pengganti placeholder
) -> list[dict[str, Any]]:             # Baris hasil sebagai list of dict
```

**Alur kerja internal:**
1. Panggil `_bind_params(sql, params)` → hasilkan SQL final yang aman
2. Panggil `start_query_execution` → dapat `execution_id`
3. Panggil `_wait_for_completion(execution_id)` → polling hingga selesai atau timeout
4. Panggil `_fetch_results(execution_id)` → ambil dan konversi baris hasil
5. Kembalikan `list[dict]`

---

### `_wait_for_completion` — Polling Mechanism

```python
def _wait_for_completion(self, execution_id: str) -> None:
    elapsed: float = 0.0
    while elapsed < _QUERY_TIMEOUT_SECONDS:          # Maksimum 30 iterasi
        response = self._client.get_query_execution(...)
        state = response["QueryExecution"]["Status"]["State"]

        if state == _SUCCEEDED:
            return                                    # Sukses → keluar

        if state in (_FAILED, _CANCELLED):
            reason = response[...].get("StateChangeReason", "")
            raise QueryExecutionError(execution_id, state, reason)

        time.sleep(_POLL_INTERVAL_SECONDS)            # Tunggu 1 detik
        elapsed += _POLL_INTERVAL_SECONDS

    # Timeout → coba batalkan query, lalu lempar error
    try:
        self._client.stop_query_execution(QueryExecutionId=execution_id)
    except Exception:
        pass  # Best-effort — timeout error tetap dilempar

    raise QueryTimeoutError(execution_id, _QUERY_TIMEOUT_SECONDS)
```

---

### `build_campaign_overview_query`

```python
def build_campaign_overview_query(
    self, request: CampaignOverviewRequest
) -> str:
```

Membangun query ke tabel `campaign_overview_agg`. Selalu menerapkan filter tanggal (`period_start >= ...` dan `period_end <= ...`), lalu secara kondisional menambahkan klausa `IN` untuk setiap filter opsional yang hadir di request.

**Tabel target:** `campaign_overview_agg`

---

### `build_comparison_query`

```python
def build_comparison_query(self, campaign_ids: list[str]) -> str:
```

Membangun query ke tabel `campaign` untuk mengambil 5 metrik perbandingan per kampanye: `total_leads`, `total_take_up`, `take_up_rate`, `total_transaction_value`, dan `duration_days` (dihitung dengan `date_diff`).

**Tabel target:** `campaign`

---

### `build_regional_query`

```python
def build_regional_query(self, campaign_id: str) -> str:
```

Membangun query ke tabel `regional_performance_agg` dengan `GROUP BY region` untuk menghitung metrik per wilayah. Menggunakan `CASE WHEN SUM(leads_count) = 0 THEN 0.0` untuk menghindari division by zero saat menghitung `take_up_rate`.

**Tabel target:** `regional_performance_agg`

---

### `build_time_analysis_query`

```python
def build_time_analysis_query(self, campaign_id: str) -> str:
```

Membangun query ke tabel `leads` yang hanya mengambil baris dengan `take_up_flag = true` dan `take_up_date IS NOT NULL` — yaitu hanya nasabah yang benar-benar melakukan take-up — untuk keperluan histogram waktu konversi.

**Tabel target:** `leads`

---

### `build_customer_criteria_query`

```python
def build_customer_criteria_query(self, campaign_id: str) -> str:
```

Membangun query ke tabel `leads` untuk analisis demografi nasabah: `customer_segment`, `age_group`, `domicile_region`, `product_holding`, `balance_category`, `take_up_flag`, `transaction_value`.

**Tabel target:** `leads`

---

### Helper Functions (Module-Level Private)

#### `_quote(value: str) -> str`

```python
def _quote(value: str) -> str:
    """Mengamankan string untuk literal SQL dengan single-quote doubling."""
    escaped = str(value).replace("'", "''")  # O'Brien → O''Brien
    return f"'{escaped}'"
    # _quote("Jakarta") → "'Jakarta'"
    # _quote("O'Brien") → "'O''Brien'"
```

#### `_in_clause(column: str, values: list[str]) -> str`

```python
def _in_clause(column: str, values: list[str]) -> str:
    """Membangun klausa SQL IN dengan quoting aman per nilai."""
    if not values:
        return "(1 = 0)"  # List kosong → kondisi selalu false
    quoted_values = ", ".join(_quote(v) for v in values)
    return f"{column} IN ({quoted_values})"
    # _in_clause("channel", ["wa", "sms"]) → "channel IN ('wa', 'sms')"
    # _in_clause("channel", [])            → "(1 = 0)"
```

#### `_bind_params(sql: str, params: dict[str, Any]) -> str`

```python
def _bind_params(sql: str, params: dict[str, Any]) -> str:
    """Mengganti placeholder :name dengan nilai yang sudah di-quote."""
    # Proses key dari terpanjang → menghindari ":id" cocok ke ":id_list"
    for key in sorted(params.keys(), key=len, reverse=True):
        value = params[key]
        if isinstance(value, bool):
            replacement = "true" if value else "false"
        elif isinstance(value, (int, float)):
            replacement = str(value)
        else:
            replacement = _quote(str(value))
        result = result.replace(f":{key}", replacement)
    return result
```

---

## Simulasi / Skenario

### Skenario 1 — Query Overview: PROGRAM QRIS + Channel WA + Wilayah Jakarta

**Input request:**
```python
from shared.models import CampaignOverviewRequest

req = CampaignOverviewRequest(
    start_date="2024-01-01",
    end_date="2024-03-31",
    flag_program=["PROGRAM QRIS"],
    media_blasting=["wa"],
    wilayah=[1],  # 1 = Jakarta
)
```

**Proses di `build_campaign_overview_query`:**
```python
conditions = [
    "period_start >= '2024-01-01'",      # _quote(request.start_date)
    "period_end <= '2024-03-31'",        # _quote(request.end_date)
    "product IN ('PROGRAM QRIS')",       # _in_clause("product", ["PROGRAM QRIS"])
    "channel IN ('wa')",                 # _in_clause("channel", ["wa"])
    "region IN ('1')",                   # _in_clause("region", ["1"]) — int dikonversi ke str
]
```

**SQL yang dihasilkan:**
```sql
SELECT
    period_start,
    period_end,
    granularity,
    product,
    channel,
    region,
    total_leads,
    total_take_up,
    take_up_rate,
    total_transaction_value,
    campaign_count
FROM campaign_overview_agg
WHERE period_start >= '2024-01-01'
  AND period_end <= '2024-03-31'
  AND product IN ('PROGRAM QRIS')
  AND channel IN ('wa')
  AND region IN ('1')
ORDER BY period_start ASC
```

**Output (setelah `execute_query` selesai):**
```python
[
    {
        "period_start": "2024-01-01",
        "period_end": "2024-01-31",
        "granularity": "monthly",
        "product": "PROGRAM QRIS",
        "channel": "wa",
        "region": "1",
        "total_leads": "14800",
        "total_take_up": "1658",
        "take_up_rate": "11.2",
        "total_transaction_value": "18250000000",
        "campaign_count": "1",
    },
    # ... baris bulan Februari dan Maret
]
```

---

### Skenario 2 — Query Perbandingan 3 Kampanye

**Input:**
```python
sql = client.build_comparison_query(["CAMP-001", "CAMP-002", "CAMP-003"])
```

**SQL yang dihasilkan:**
```sql
SELECT
    campaign_id,
    campaign_name,
    total_leads,
    total_take_up,
    take_up_rate,
    total_transaction_value,
    date_diff('day', start_date, end_date) AS duration_days
FROM campaign
WHERE campaign_id IN ('CAMP-001', 'CAMP-002', 'CAMP-003')
ORDER BY campaign_id ASC
```

---

### Skenario 3 — Timeout dan Error Handling

**Skenario:** Query berjalan lebih dari 30 detik (misalnya karena beban Athena tinggi).

**Alur:**
```
t=0s   → start_query_execution dipanggil → execution_id = "xyz-789"
t=1s   → get_query_execution → state = "RUNNING"
t=2s   → get_query_execution → state = "RUNNING"
...
t=30s  → elapsed >= 30 → loop berhenti
        → stop_query_execution("xyz-789") dipanggil (best-effort)
        → raise QueryTimeoutError("xyz-789", 30)
```

**Di Lambda handler:**
```python
try:
    rows = client.execute_query(sql)
except QueryTimeoutError as e:
    # Log ke CloudWatch, kembalikan HTTP 504 ke frontend
    return {"statusCode": 504, "body": f"Query timeout setelah {e.timeout_seconds}s"}
except QueryExecutionError as e:
    # Query gagal di sisi Athena
    return {"statusCode": 500, "body": f"Query gagal: {e.reason}"}
```

---

### Skenario 4 — Pencegahan SQL Injection

**Input berbahaya (misalnya dari parameter yang dimanipulasi):**
```python
# Bayangkan campaign_id diterima dari request dan berisi karakter berbahaya
campaign_id = "'; DROP TABLE leads; --"
```

**Proses di `_quote`:**
```python
_quote("'; DROP TABLE leads; --")
# → escaped = "''; DROP TABLE leads; --"  (single-quote di-double)
# → return "'''; DROP TABLE leads; --'"
```

**SQL yang dihasilkan (tidak berbahaya):**
```sql
WHERE campaign_id = '''; DROP TABLE leads; --'
-- Athena memperlakukan ini sebagai string literal, bukan perintah SQL
```

Serangan SQL injection gagal karena `'` menjadi `''` — tidak ada perintah yang bisa dieksekusi.

---

## Keterkaitan dengan Komponen Lain

**Bergantung pada:**
- `shared/models.py` — mengimpor `CampaignOverviewRequest` sebagai tipe parameter `build_campaign_overview_query`
- `boto3` — library AWS SDK (tercantum di `backend/requirements.txt`)
- **Amazon Athena** (infrastruktur) — layanan AWS yang harus sudah dikonfigurasi dengan database dan tabel yang sesuai
- **Amazon S3** — bucket untuk menyimpan output query Athena (dikonfigurasi via `s3_output_location`)

**Digunakan oleh:**
- `backend/lambdas/campaign_overview/handler.py` — memanggil `build_campaign_overview_query` + `execute_query`
- `backend/lambdas/campaign_comparison/handler.py` — memanggil `build_comparison_query` + `execute_query`
- `backend/lambdas/regional_performance/handler.py` — memanggil `build_regional_query` + `execute_query`
- `backend/lambdas/time_analysis/handler.py` — memanggil `build_time_analysis_query` + `execute_query`
- `backend/lambdas/customer_criteria/handler.py` — memanggil `build_customer_criteria_query` + `execute_query`

**Pengaruh ke komponen lain jika diubah:**
- Mengubah nama tabel di query builder akan menyebabkan semua handler yang bergantung gagal saat runtime
- Mengubah `_QUERY_TIMEOUT_SECONDS` mempengaruhi semua endpoint sekaligus — perlu diuji dampaknya terhadap Lambda timeout
- Mengubah format output `_fetch_results` (dari `list[dict]` ke format lain) memerlukan update di semua handler
- Mengubah logika `_quote` atau `_in_clause` berpotensi membuka celah SQL injection jika tidak hati-hati

---

## Requirements yang Dipenuhi

| Requirement | Deskripsi |
|-------------|-----------|
| **1.2** | Implementasi Athena query helper sebagai komponen shared backend |
| **2.1** | `build_comparison_query` menyediakan 5 metrik perbandingan kampanye |
| **3.1** | `build_time_analysis_query` menyediakan data analisis waktu take-up |
| **4.1** | `build_regional_query` menyediakan metrik per wilayah (`leads_count`, `take_up_count`, `take_up_rate`) |
| **5.1** | `build_customer_criteria_query` menyediakan atribut demografis nasabah |

---

## Catatan Penting

1. **Athena adalah layanan berbayar per query** — setiap panggilan `execute_query` menghabiskan biaya berdasarkan jumlah data yang di-scan. Query ke tabel `leads` (raw data) jauh lebih mahal daripada query ke tabel pre-aggregate (`campaign_overview_agg`). Gunakan tabel aggregate kapanpun memungkinkan.

2. **`_fetch_results` mengembalikan semua nilai sebagai string** — Athena mengembalikan semua nilai dalam format `VarCharValue`. Handler yang memanggil `execute_query` bertanggung jawab untuk konversi tipe (misal `int(row["total_leads"])`, `float(row["take_up_rate"])`).

3. **Timeout 30 detik bersifat wall-clock** — timer dihitung dari saat `execute_query` dipanggil, bukan dari saat Athena mulai memproses query. Jika ada delay jaringan, waktu efektif yang tersisa untuk query lebih pendek.

4. **`stop_query_execution` bersifat best-effort** — saat timeout terjadi, sistem mencoba membatalkan query Athena untuk mencegah orphaned run yang memakan biaya, tetapi jika pembatalan gagal (misal karena query sudah selesai di sisi Athena tepat di saat yang sama), error tetap diabaikan dan `QueryTimeoutError` tetap dilempar.

5. **Column name diambil dari baris header, bukan schema metadata** — jika Athena mengembalikan result set kosong, `_fetch_results` mengembalikan `[]` bukan error. Handler harus siap menangani list kosong.

6. **`build_*_query` tidak memanggil `execute_query`** — setiap method builder hanya mengembalikan string SQL. Ini memudahkan unit testing query SQL secara terpisah tanpa perlu mock boto3.

7. **`AthenaClient` tidak thread-safe** — boto3 client yang dibuat di `__init__` tidak dirancang untuk shared access antar thread. Setiap Lambda invocation membuat instance baru, sehingga ini bukan masalah dalam konteks Lambda.
