# Task 4.9 — Audit Logging

## Ringkasan Singkat

Audit Logging adalah modul bersama (`backend/shared/audit.py`) yang mencatat setiap aktivitas akses pengguna ke dalam tabel DynamoDB bernama `AuditLog`. Setiap kali seorang pengguna membuka halaman dashboard atau memanggil endpoint API, sebuah entri log ditulis secara otomatis dengan informasi: siapa pengguna tersebut, halaman apa yang diakses, jam berapa, parameter apa yang dikirimkan, dan dari IP mana. Log ini disimpan selama 90 hari lalu dihapus otomatis menggunakan fitur TTL DynamoDB. Modul ini digunakan sebagai *decorator* di Lambda handler sehingga logging berjalan transparan tanpa mengubah logika bisnis handler.

---

## Penjelasan Awam (Non-Technical)

Bayangkan sebuah kantor yang memiliki **buku tamu digital** di setiap pintu ruangan. Setiap orang yang masuk ke ruangan tersebut — baik untuk rapat, mengambil dokumen, atau sekadar lewat — dicatat secara otomatis:

- **Nama**: siapa yang masuk
- **Waktu**: pukul berapa masuk
- **Ruangan**: ruangan mana yang dikunjungi
- **Tujuan**: apa yang dilakukan (hanya melihat? mengekspor data?)
- **Dari mana**: dari gedung mana (alamat IP)

Setelah 90 hari, catatan lama dihapus otomatis untuk menghemat ruang — sama seperti buku tamu fisik yang halamannya diganti setiap kuartal.

Yang membuat sistem ini istimewa adalah ia **bekerja di latar belakang tanpa mengganggu aktivitas utama**. Jika sistem pencatatan sedang bermasalah (misalnya listrik mati), pintu ruangan tetap bisa dibuka — sistem tidak memblokir akses hanya karena pencatatan gagal.

Manfaat bagi pengguna bisnis dan tim keamanan:
- **Audit trail**: jika ada insiden keamanan atau kebocoran data, bisa ditelusuri siapa yang mengakses apa dan kapan.
- **Kepatuhan regulasi**: banyak regulasi perbankan mensyaratkan pencatatan akses ke data sensitif.
- **Monitoring penggunaan**: tim dapat melihat fitur mana yang paling sering digunakan untuk prioritas pengembangan.
- **Deteksi anomali**: akses di luar jam kerja atau dari IP tidak dikenal bisa dideteksi dari log ini.

---

## Penjelasan Teknis

### File yang Diimplementasi

- **`backend/shared/audit.py`** — modul audit logging

### Library/Framework yang Digunakan

| Library | Sumber | Kegunaan |
|---------|--------|----------|
| `boto3` | AWS SDK | Write item ke DynamoDB |
| `functools` (stdlib) | Python | `functools.wraps` untuk decorator yang bersih |
| `json` (stdlib) | Python | Parse body request JSON |
| `logging` (stdlib) | Python | Warning log jika DynamoDB gagal |
| `time` (stdlib) | Python | Kalkulasi TTL expiry timestamp |
| `datetime` (stdlib) | Python | Generate timestamp ISO 8601 |

### Schema DynamoDB Tabel `AuditLog`

| Atribut | Tipe DynamoDB | Keterangan |
|---------|--------------|------------|
| `user_id` | String (PK) | Cognito `sub` atau `"anonymous"` |
| `timestamp` | String (SK) | ISO 8601, e.g. `"2024-08-09T02:15:23Z"` |
| `page_accessed` | String | Nama halaman atau endpoint |
| `action` | String | `"view"`, `"export"`, `"compare"`, dll. |
| `request_params` | Map | Query params + body (dipotong 1000 char) |
| `ip_address` | String | Source IP dari API Gateway (opsional) |
| `expiry_timestamp` | Number | Unix epoch TTL — DynamoDB auto-delete |

Composite key: **PK = `user_id`**, **SK = `timestamp`**.

### TTL (Time-To-Live) DynamoDB

```python
_TTL_DAYS = 90
expiry_timestamp = int(time.time()) + 90 * 24 * 3600
```

DynamoDB membaca atribut `expiry_timestamp` sebagai Unix epoch. Setelah waktu tersebut lewat, item dihapus otomatis dalam beberapa jam (DynamoDB tidak menjamin penghapusan tepat waktu, biasanya dalam 48 jam setelah TTL).

### Pola Arsitektur: Decorator Factory

```python
@audit_log(page="campaign_overview", action="view")
def lambda_handler(event, context):
    # logika bisnis di sini
    ...
```

Decorator `audit_log` adalah **factory** yang menerima parameter `page` dan `action`, lalu mengembalikan decorator yang membungkus handler. Ini menggunakan pola closure dua tingkat:

```
audit_log(page, action)      ← factory, dipanggil saat definisi fungsi
  └── decorator(handler_func)  ← dipanggil oleh Python saat @audit_log
        └── wrapper(event, context)  ← dipanggil saat Lambda diinvoke
```

`functools.wraps(handler_func)` memastikan wrapper mempertahankan metadata fungsi asli (nama, docstring) sehingga debugging dan logging lebih mudah.

### Resolusi User Identity (Prioritas)

Kode mencoba tiga sumber secara berurutan:

1. **`event["requestContext"]["authorizer"]["claims"]["sub"]`** — klaim JWT dari Cognito User Pools authorizer (paling umum dan paling terpercaya)
2. **`event["requestContext"]["authorizer"]["principalId"]`** — dari custom Lambda authorizer (fallback)
3. **`"anonymous"`** — jika tidak ada authorizer sama sekali (request publik atau pengujian lokal)

### Proteksi Ukuran Item DynamoDB

DynamoDB memiliki batas **400 KB per item**. Untuk mencegah error:

```python
_REQUEST_PARAMS_MAX_LEN = 1000  # karakter
```

Setiap nilai string dalam `request_params` dipotong di 1000 karakter. Body request juga dipotong sebelum di-parse. Fungsi `_sanitise_params()` memastikan semua nilai aman sebelum dikirim ke DynamoDB.

### Best-Effort Logging (Tidak Pernah Crash Handler)

```python
try:
    # ... write to DynamoDB
except Exception:  # noqa: BLE001
    logger.warning("audit: failed to write log entry for user=%s page=%s", ...)
```

Setiap exception ditangkap dan hanya di-log sebagai WARNING. Handler asli **selalu dipanggil** bahkan jika DynamoDB tidak tersedia.

### Edge Cases yang Ditangani

- DynamoDB tidak tersedia → log WARNING, handler tetap jalan
- `request_params` mengandung nilai sangat panjang → dipotong ke 1000 char
- Body bukan JSON valid → disimpan sebagai string mentah di key `"body"`
- Body adalah JSON tapi bukan object (misal array) → disimpan sebagai string `"body"`
- IP address tidak tersedia → field `ip_address` tidak dimasukkan ke item
- `user_id` tidak bisa diextract → fallback ke `"anonymous"`

---

## Struktur Kode

```
backend/shared/audit.py
│
├── Konstanta
│   ├── _AUDIT_LOG_TABLE = "AuditLog"     # dari env var AUDIT_LOG_TABLE
│   ├── _TTL_DAYS = 90
│   └── _REQUEST_PARAMS_MAX_LEN = 1000
│
├── Core Write Function
│   └── log_access(user_id, page_accessed, action, request_params, ip_address) → None
│       ├── Generate timestamp ISO 8601
│       ├── Kalkulasi expiry_timestamp (TTL)
│       ├── Build item dict
│       ├── Sanitise request_params
│       └── table.put_item(Item=item)   ← best-effort, semua exception ditangkap
│
├── Request Parameter Helpers
│   ├── extract_request_params(event) → dict
│   │   ├── Baca queryStringParameters
│   │   ├── Baca body → coba parse JSON → merge ke params
│   │   └── Return {} jika ada error
│   │
│   └── _sanitise_params(params) → dict
│       └── Potong semua string value > 1000 char
│
└── Decorator Factory
    └── audit_log(page, action="view") → Callable
        └── decorator(handler_func) → Callable
            └── wrapper(event, context) → Any
                ├── 1. Extract user_id dari requestContext.authorizer
                ├── 2. Extract ip_address dari requestContext.identity
                ├── 3. Extract request_params dari event
                ├── 4. Panggil log_access(...)  ← best-effort
                └── 5. Return handler_func(event, context)
```

### Signature Fungsi Utama

```python
def audit_log(page: str, action: str = "view") -> Callable:
    """
    Decorator factory untuk Lambda handler.
    Contoh: @audit_log(page="campaign_overview", action="view")
    """

def log_access(
    user_id: str,
    page_accessed: str,
    action: str,
    request_params: dict[str, Any] | None = None,
    ip_address: str | None = None,
) -> None:
    """
    Tulis satu entri ke DynamoDB AuditLog. Best-effort, tidak pernah raise.
    """

def extract_request_params(event: dict[str, Any]) -> dict[str, Any]:
    """
    Ekstrak query params dan body dari API Gateway event.
    Return: dict, atau {} jika ada error.
    """

def _sanitise_params(params: dict[str, Any]) -> dict[str, Any]:
    """
    Potong semua nilai string > 1000 char untuk keamanan ukuran DynamoDB.
    """
```

---

## Simulasi / Skenario

### Skenario 1 — User Buka Halaman Campaign Overview (Happy Path)

**Konteks**: User `robin_123` (Cognito sub: `"user-abc-001"`) membuka halaman Campaign Overview pada pukul **09:15 WIB** (UTC: 02:15 pada tanggal 2024-08-09).

**Event API Gateway yang diterima Lambda**:
```json
{
  "requestContext": {
    "authorizer": {
      "claims": {
        "sub": "user-abc-001",
        "custom:role": "divisi_bisnis",
        "auth_time": 1723167600
      }
    },
    "identity": {
      "sourceIp": "182.1.2.3"
    }
  },
  "queryStringParameters": {
    "start_date": "2024-01-01",
    "end_date": "2024-06-30"
  },
  "body": null
}
```

**Penggunaan Decorator di Handler**:
```python
@audit_log(page="campaign_overview", action="view")
def lambda_handler(event, context):
    # logika bisnis campaign overview
    ...
```

**Proses di `wrapper`**:
1. `user_id` = `"user-abc-001"` (dari `claims["sub"]`)
2. `ip_address` = `"182.1.2.3"`
3. `request_params` = `{"start_date": "2024-01-01", "end_date": "2024-06-30"}`
4. `log_access()` dipanggil:
   - `timestamp` = `"2024-08-09T02:15:23Z"`
   - `expiry_timestamp` = `1723167723 + (90 × 86400)` = `1730943723` (9 Nov 2024)

**Item yang Ditulis ke DynamoDB**:
```json
{
  "user_id": "user-abc-001",
  "timestamp": "2024-08-09T02:15:23Z",
  "page_accessed": "campaign_overview",
  "action": "view",
  "request_params": {
    "start_date": "2024-01-01",
    "end_date": "2024-06-30"
  },
  "ip_address": "182.1.2.3",
  "expiry_timestamp": 1730943723
}
```

---

### Skenario 2 — User Melakukan Export Data

**Konteks**: User yang sama melakukan export CSV dari halaman Regional Performance.

**Penggunaan Decorator**:
```python
@audit_log(page="regional_performance", action="export")
def lambda_handler(event, context):
    ...
```

**Event body**:
```json
{
  "page": "regional_performance",
  "format": "csv",
  "filters": [{"field": "flag_program", "values": ["PROGRAM QRIS"]}],
  "time_range_start": "2024-01-01",
  "time_range_end": "2024-03-31"
}
```

**Item yang Ditulis ke DynamoDB**:
```json
{
  "user_id": "user-abc-001",
  "timestamp": "2024-08-09T03:42:11Z",
  "page_accessed": "regional_performance",
  "action": "export",
  "request_params": {
    "page": "regional_performance",
    "format": "csv",
    "filters": "[{\"field\": \"flag_program\", \"values\": [\"PROGRAM QRIS\"]}]",
    "time_range_start": "2024-01-01",
    "time_range_end": "2024-03-31"
  },
  "ip_address": "182.1.2.3",
  "expiry_timestamp": 1730947331
}
```

---

### Skenario 3 — Request Tanpa Autentikasi (Fallback Anonymous)

**Konteks**: Request langsung ke endpoint tanpa token (misalnya dari pengujian internal atau health check).

**Event** tanpa `requestContext.authorizer`:
```json
{
  "requestContext": {},
  "queryStringParameters": null,
  "body": null
}
```

**Proses**: Semua path extraction gagal → `user_id = "anonymous"`

**Item yang Ditulis ke DynamoDB**:
```json
{
  "user_id": "anonymous",
  "timestamp": "2024-08-09T04:00:00Z",
  "page_accessed": "campaign_overview",
  "action": "view",
  "expiry_timestamp": 1730948400
}
```

*Catatan*: `request_params` dan `ip_address` tidak dimasukkan karena kosong/None.

---

### Skenario 4 — TTL: Entri Dihapus Otomatis Setelah 90 Hari

Entri yang dibuat pada **9 Agustus 2024** dengan `expiry_timestamp = 1730943723`:

```
Tanggal expiry: 9 Agustus 2024 + 90 hari = 7 November 2024
```

Setelah 7 November 2024, DynamoDB akan menghapus entri ini secara otomatis dalam beberapa jam. Tidak perlu cron job atau Lambda cleaner terpisah.

---

### Skenario 5 — DynamoDB Tidak Tersedia (Graceful Degradation)

**Situasi**: DynamoDB endpoint tidak bisa dijangkau karena network issue.

**Proses di `log_access()`**:
```python
try:
    table.put_item(Item=item)   # ← DynamoDB timeout/error
except Exception:               # ← Exception ditangkap di sini
    logger.warning(
        "audit: failed to write log entry for user=user-abc-001 page=campaign_overview",
        exc_info=True
    )
    # ← Tidak ada raise, eksekusi dilanjutkan
```

**Hasil**:
- CloudWatch Logs mencatat WARNING dengan stack trace
- Handler asli tetap dipanggil dan user mendapatkan response normal
- **Tidak ada HTTP 500** yang dikirim ke user

---

### Skenario 6 — Body Request Sangat Panjang (Proteksi Ukuran)

**Situasi**: Body request mengandung daftar 500 campaign IDs (total >5000 karakter).

**Proses di `extract_request_params()`**:
```python
raw_body = event.get("body")  # string panjang
truncated_body = raw_body[:1000]  # dipotong ke 1000 karakter
```

**Proses di `_sanitise_params()`**:
```python
# Setiap nilai yang lebih panjang dari 1000 char dipotong
for key, value in params.items():
    if len(str(value)) > 1000:
        safe[key] = str(value)[:1000]
```

Item DynamoDB tetap aman dari risiko melebihi batas 400 KB.

---

## Keterkaitan dengan Komponen Lain

### Bergantung pada:
- **Amazon DynamoDB** — tabel `AuditLog` (dikonfigurasi via env var `AUDIT_LOG_TABLE`)
- **`boto3`** — AWS SDK untuk menulis ke DynamoDB
- **API Gateway requestContext** — sumber data user identity dan IP address

### Digunakan oleh (sebagai decorator `@audit_log`):
- **`campaign_overview/handler.py`** — `@audit_log(page="campaign_overview")`
- **`campaign_comparison/handler.py`** — `@audit_log(page="campaign_comparison", action="compare")`
- **`time_analysis/handler.py`** — `@audit_log(page="time_analysis")`
- **`regional_performance/handler.py`** — `@audit_log(page="regional_performance")`
- **`customer_criteria/handler.py`** — `@audit_log(page="customer_criteria")`
- **`similar_campaign/handler.py`** — `@audit_log(page="similar_campaign")`
- **`export_service/handler.py`** — perlu ditambahkan: `@audit_log(page=..., action="export")` *(lihat Todo)*

### Pengaruh ke komponen lain jika komponen ini berubah:
- Jika schema DynamoDB berubah (misal: menambah field `session_id`), semua Lambda yang menggunakan decorator ini langsung mencatat field baru tanpa perubahan kode handler
- Jika `_TTL_DAYS` diubah, seluruh log baru menggunakan TTL yang baru; log lama tidak terpengaruh
- Jika nama tabel `_AUDIT_LOG_TABLE` berubah, env var di CDK stack perlu diupdate
- Jika struktur `requestContext.authorizer` dari Cognito berubah (misal: versi API Gateway baru), logika ekstraksi `user_id` perlu diupdate

---

## Requirements yang Dipenuhi

| Req ID | Deskripsi |
|--------|-----------|
| **7.4** | Setiap akses ke endpoint API dicatat ke DynamoDB AuditLog dengan: `user_id`, `timestamp`, `page_accessed`, `action`, `request_params`, `ip_address` |
| **7.4** | Log disimpan selama 90 hari menggunakan DynamoDB TTL sebelum dihapus otomatis |
| **7.4** | Kegagalan pencatatan audit tidak boleh mengganggu response handler utama (*best-effort*) |

---

## Catatan Penting

### Desain Best-Effort vs. Guaranteed Logging

Keputusan menggunakan best-effort (catch-all exception) adalah trade-off yang disengaja: **availabilitas aplikasi > kelengkapan audit log**. Dalam konteks dashboard internal, downtime DynamoDB yang menyebabkan semua endpoint error lebih berbahaya daripada beberapa entri log yang hilang. Untuk sistem yang membutuhkan audit log yang dijamin (misal: sistem trading atau pembayaran), arsitektur yang lebih robust diperlukan (SQS sebagai buffer, DLQ, dll.).

### Environment Variable Wajib

```bash
AUDIT_LOG_TABLE="AuditLog"   # default, overridable
```

Jika Lambda tidak memiliki IAM permission `dynamodb:PutItem` terhadap tabel `AuditLog`, setiap request akan menghasilkan WARNING log di CloudWatch tetapi handler tetap berjalan.

### Limitasi yang Diketahui

1. **Tidak ada deduplication**: Jika Lambda diinvoke ulang karena retry (misal: API Gateway timeout), entri ganda bisa terjadi karena SK `timestamp` berbeda per invocation.
2. **Granularitas timestamp**: Timestamp diambil saat decorator `wrapper` dieksekusi, bukan saat handler selesai. Untuk kasus di mana durasi eksekusi penting, perlu pendekatan berbeda.
3. **Tidak ada indexing sekunder**: Query audit log hanya efisien jika menggunakan `user_id` sebagai filter. Query seperti "semua akses ke halaman X oleh siapapun" memerlukan GSI (Global Secondary Index) yang belum dibuat.

### Asumsi yang Dibuat

- Tabel DynamoDB `AuditLog` sudah dibuat dengan TTL attribute dikonfigurasi ke field `expiry_timestamp` (TTL harus diaktifkan secara eksplisit di DynamoDB, tidak otomatis).
- Lambda memiliki IAM role dengan permission `dynamodb:PutItem` ke tabel `AuditLog`.
- `AUDIT_LOG_TABLE` env var dikonfigurasi di CDK stack (AuthStack atau ApiStack).

### Todo untuk Pengembangan Berikutnya

- [ ] Tambahkan `@audit_log(page=..., action="export")` ke `export_service/handler.py` (saat ini belum ada)
- [ ] Buat DynamoDB GSI pada `page_accessed` untuk query "siapa saja yang mengakses halaman X hari ini"
- [ ] Pertimbangkan menambah field `duration_ms` untuk mencatat durasi eksekusi handler
- [ ] Implementasi alarm CloudWatch: alert jika terjadi >X WARNING per menit (indikasi DynamoDB down)
- [ ] Tambah field `session_id` untuk korelasi request dalam satu sesi login yang sama
- [ ] Evaluasi apakah perlu menggunakan SQS sebagai buffer untuk guaranteed delivery audit log
