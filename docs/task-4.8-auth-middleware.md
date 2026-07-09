# Task 4.8 — Auth Middleware

## Ringkasan Singkat

Auth Middleware adalah modul bersama (`backend/shared/auth.py`) yang menyediakan fungsi-fungsi untuk validasi JWT, pemeriksaan masa berlaku sesi, dan pengambilan identitas pengguna dari event API Gateway. Modul ini tidak melakukan verifikasi kriptografi token secara mandiri — tugas itu sudah dilakukan oleh **Cognito authorizer** di API Gateway — melainkan fokus pada dekoding klaim JWT, penegakan batas sesi 8 jam, dan ekstraksi role pengguna (`divisi_bisnis` atau `divisi_data`). Setiap Lambda handler yang membutuhkan konteks pengguna terautentikasi memanggil modul ini sebelum memproses request.

---

## Penjelasan Awam (Non-Technical)

Bayangkan gedung kantor modern yang memiliki sistem kartu akses. Setiap karyawan memiliki kartu ID yang dikeluarkan oleh HRD. Ketika masuk ke ruangan tertentu:

1. **Satpam di pintu utama** memeriksa apakah kartu ID asli dan tidak palsu *(ini dilakukan oleh Cognito di API Gateway — bukan oleh modul ini)*.
2. **Sistem di dalam ruangan** kemudian membaca kartu untuk mengetahui: siapa orangnya, apa jabatannya, dan jam berapa ia masuk tadi.
3. Jika orang tersebut masuk ke kantor pukul 08:00, **kartu aksesnya otomatis tidak berlaku lagi pukul 16:00** (8 jam kemudian). Ini mencegah seseorang menggunakan kartu yang ditinggal di meja teman untuk masuk di malam hari.

Auth Middleware adalah "sistem di dalam ruangan" tersebut — ia membaca informasi dari kartu akses digital (JWT token), memverifikasi apakah sesi masih berlaku, dan memberikan tahu setiap handler siapa yang sedang mengakses dan dalam kapasitas apa.

Manfaat bagi pengguna bisnis:
- Jika Anda login pagi hari dan meninggalkan laptop tanpa dikunci, akun Anda otomatis aman setelah 8 jam.
- Tidak ada yang bisa menggunakan link/token lama untuk mengakses data setelah sesi berakhir.
- Sistem membedakan antara pengguna `divisi_bisnis` (yang hanya melihat laporan) dan `divisi_data` (yang bisa mengakses data lebih dalam).

---

## Penjelasan Teknis

### File yang Diimplementasi

- **`backend/shared/auth.py`** — modul middleware autentikasi

### Library/Framework yang Digunakan

| Library | Sumber | Kegunaan |
|---------|--------|----------|
| `base64` (stdlib) | Python | Dekoding payload JWT (base64url) |
| `json` (stdlib) | Python | Parse klaim JWT dan serialisasi response |
| `time` (stdlib) | Python | Perbandingan waktu sesi (`time.time()`) |

Tidak ada library JWT eksternal (seperti `PyJWT` atau `python-jose`) — ini disengaja karena verifikasi tanda tangan sudah dilakukan di layer API Gateway.

### Pola Arsitektur yang Diterapkan

1. **Middleware Pattern** — fungsi `require_auth()` dan `get_user_context()` dipanggil di awal setiap handler sebagai lapisan keamanan sebelum logika bisnis berjalan.
2. **Trust Boundary yang Jelas** — modul ini secara eksplisit mendokumentasikan bahwa verifikasi *kriptografi* diserahkan ke Cognito. Dekoding dilakukan tanpa re-verify signature untuk menghindari network call yang tidak perlu.
3. **Graceful Degradation** — fungsi `get_user_context()` tidak pernah melempar exception; kegagalan selalu menghasilkan context `is_authenticated: False`.

### Alur Validasi JWT

JWT (JSON Web Token) terdiri dari tiga bagian dipisah titik: `header.payload.signature`.

```
eyJhbGciOiJSUzI1NiJ9
  .eyJzdWIiOiJ1c2VyLTEyMyIsImN1c3RvbTpyb2xlIjoiZGl2aXNpX2Jpc25pcyIsImF1dGhfdGltZSI6MTcyMDQ5MDQwMH0
  .SIGNATURE_BY_COGNITO
```

Modul ini hanya membaca bagian tengah (payload), mendekode dari base64url, lalu mem-parse JSON-nya. Signature tidak diverifikasi ulang.

### Batas Sesi 8 Jam

Limit `_SESSION_MAX_SECONDS = 28_800` (8 × 3600). Perhitungan:

```
is_expired = (time.time() - claims["auth_time"]) > 28_800
```

`auth_time` adalah Unix timestamp (detik sejak epoch) yang di-set Cognito pada saat pengguna berhasil login, bukan pada saat token di-refresh. Ini berarti refresh token tidak memperpanjang sesi — pengguna *harus* login ulang setiap 8 jam.

### Dua Role yang Valid

```python
VALID_ROLES: frozenset[str] = frozenset({"divisi_bisnis", "divisi_data"})
```

Role diambil dari claim `custom:role` di JWT. Nilai lain (misal `"admin"`, `"superuser"`) dikembalikan sebagai `None` — tidak dikenali dan tidak diberi akses.

### Penanganan Header Case-Insensitive

API Gateway v1 meneruskan header dengan case asli (`Authorization`), sedangkan v2 menormalkan semua header ke lowercase (`authorization`). Kode menangani keduanya:

```python
auth_header = headers.get("Authorization") or headers.get("authorization")
```

### Edge Cases yang Ditangani

- Tidak ada header `Authorization` → HTTP 401 "Authentication required"
- Token bukan format JWT valid (kurang dari 3 segmen) → HTTP 401 "Invalid authentication token"
- Payload bukan JSON valid → HTTP 401 "Invalid authentication token"
- `auth_time` tidak ada di claims → sesi dianggap valid (fallback aman, Cognito token expiry jadi pengaman)
- Role tidak dikenal → `extract_user_role()` mengembalikan `None` (handler masing-masing memutuskan akses)

---

## Struktur Kode

```
backend/shared/auth.py
│
├── Konstanta
│   ├── _SESSION_MAX_SECONDS = 28_800      # 8 jam dalam detik
│   ├── _CORS_HEADERS — header CORS standar untuk semua response
│   └── VALID_ROLES = {"divisi_bisnis", "divisi_data"}
│
├── Internal Helper
│   └── _build_401(message) → dict
│       └── Membangun response 401 dengan CORS headers + redirect ke /login
│
└── Public API
    ├── extract_token(event) → str | None
    │   └── Baca header Authorization, strip prefix "Bearer "
    │
    ├── decode_token_claims(token) → dict | None
    │   └── Split JWT, base64url-decode payload, JSON-parse
    │
    ├── extract_user_role(claims) → str | None
    │   └── Baca claims["custom:role"], validasi ke VALID_ROLES
    │
    ├── extract_user_id(claims) → str | None
    │   └── Preferensi: claims["sub"] → claims["cognito:username"] → None
    │
    ├── is_session_expired(claims) → bool
    │   └── (time.time() - claims["auth_time"]) > 28_800
    │
    ├── require_auth(event) → tuple[dict | None, dict | None]
    │   └── Kombinasi: extract_token → decode → is_session_expired
    │       Return: (claims, None) atau (None, error_response)
    │
    └── get_user_context(event) → dict
        └── Wrapper yang tidak pernah raise; return:
            {"user_id": ..., "role": ..., "is_authenticated": bool}
```

### Signature Fungsi Utama

```python
def require_auth(event: dict) -> tuple[dict | None, dict | None]:
    """
    Validasi token dan sesi dari event Lambda.
    Return: (claims_dict, None) jika sukses
            (None, error_response_dict) jika gagal
    """

def get_user_context(event: dict) -> dict:
    """
    Convenience wrapper. Tidak pernah raise exception.
    Return: {"user_id": str|None, "role": str|None, "is_authenticated": bool}
    """

def decode_token_claims(token: str) -> dict | None:
    """
    Dekode payload JWT tanpa verifikasi signature.
    Return: dict claims, atau None jika token malformed.
    """

def is_session_expired(claims: dict) -> bool:
    """
    Cek apakah sesi > 8 jam berdasarkan klaim auth_time.
    """
```

---

## Simulasi / Skenario

### Skenario 1 — Login Normal, Sesi Valid (Happy Path)

**Konteks**: User `robin_123` login pada pukul **08:00 WIB** (UTC: 01:00). Token JWT dikeluarkan oleh Cognito.

**JWT Claims yang didekode**:
```json
{
  "sub": "user-123",
  "cognito:username": "robin_123",
  "custom:role": "divisi_bisnis",
  "auth_time": 1720490400,
  "exp": 1720494000,
  "iat": 1720490400
}
```

Di mana `auth_time = 1720490400` = Jumat 9 Agustus 2024, pukul 01:00 UTC (08:00 WIB).

**Request pukul 10:00 WIB** (elapsed = 2 jam = 7.200 detik):
```
is_session_expired = (7200 > 28800) = False
```

**Hasil `require_auth(event)`**:
```python
(
  {"sub": "user-123", "custom:role": "divisi_bisnis", "auth_time": 1720490400, ...},
  None  # tidak ada error
)
```

**Hasil `get_user_context(event)`**:
```python
{
  "user_id": "user-123",
  "role": "divisi_bisnis",
  "is_authenticated": True
}
```

---

### Skenario 2 — Sesi Berakhir (>8 Jam)

**Konteks**: User yang sama, request datang pada pukul **16:01 WIB** (elapsed = 8 jam 1 menit = 28.860 detik).

**Kalkulasi**:
```
is_session_expired = (28860 > 28800) = True
```

**Hasil `require_auth(event)`**:
```python
(
  None,
  {
    "statusCode": 401,
    "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*", ...},
    "body": "{\"message\": \"Your session has expired after 8 hours. Please log in again.\", \"redirect\": \"/login\"}"
  }
)
```

**Frontend** menerima redirect ke `/login` dan menampilkan pesan "Sesi Anda telah berakhir, silakan login kembali."

---

### Skenario 3 — Token Tidak Ada (Request Tanpa Autentikasi)

**Request tanpa header `Authorization`**:
```python
event = {
  "headers": {},
  "body": "{\"page\": \"campaign_overview\"}"
}
```

**Proses**:
1. `extract_token(event)` → `None` (header tidak ada)
2. `require_auth` langsung return error

**Response (HTTP 401)**:
```json
{
  "message": "Authentication required. Please log in.",
  "redirect": "/login"
}
```

---

### Skenario 4 — Decode JWT Claims Secara Detail

Token Bearer yang diterima:
```
Bearer eyJhbGciOiJSUzI1NiJ9.eyJzdWIiOiJ1c2VyLTEyMyIsImN1c3RvbTpyb2xlIjoiZGl2aXNpX2Jpc25pcyIsImF1dGhfdGltZSI6MTcyMDQ5MDQwMH0.SIGNATURE
```

Proses `decode_token_claims()`:
1. Split pada `.` → `["eyJhbGciOiJSUzI1NiJ9", "eyJzdWIiOiJ1c2VyLTEyMyIs...", "SIGNATURE"]`
2. Ambil segmen index 1 (payload)
3. Tambah padding `=` jika panjang bukan kelipatan 4
4. `base64.urlsafe_b64decode(payload_b64)` → bytes
5. `json.loads(decoded_bytes.decode("utf-8"))` → dict claims

**Claims yang didekode**:
```json
{
  "sub": "user-123",
  "custom:role": "divisi_bisnis",
  "auth_time": 1720490400
}
```

---

### Skenario 5 — Role Tidak Dikenal

**Claims**:
```json
{
  "sub": "user-456",
  "custom:role": "admin_super",
  "auth_time": 1720490400
}
```

**Hasil `extract_user_role(claims)`**:
```python
None  # "admin_super" tidak ada di VALID_ROLES
```

Handler yang memanggil `get_user_context()` akan mendapat `role: None` dan dapat menolak akses atau membatasi fitur sesuai logika bisnis masing-masing.

---

## Keterkaitan dengan Komponen Lain

### Bergantung pada:
- **Amazon Cognito** (via API Gateway authorizer) — melakukan verifikasi kriptografi signature JWT sebelum request sampai ke Lambda. Modul ini hanya *membaca* hasil verifikasi tersebut.
- Tidak ada dependency Python eksternal — hanya stdlib.

### Digunakan oleh:
- **Semua Lambda handlers** yang memerlukan konteks user:
  - `campaign_overview/handler.py`
  - `campaign_comparison/handler.py`
  - `time_analysis/handler.py`
  - `regional_performance/handler.py`
  - `customer_criteria/handler.py`
  - `similar_campaign/handler.py`
  - `export_service/handler.py`
- **`shared/audit.py`** — menggunakan identitas user yang sama (dari event requestContext) untuk mencatat audit log

### Pengaruh ke komponen lain jika komponen ini berubah:
- Jika `_SESSION_MAX_SECONDS` diubah, semua endpoint terpengaruh; perlu update dokumentasi pengguna
- Jika `VALID_ROLES` ditambah nilai baru, handler-handler yang mengecek role perlu disesuaikan
- Jika format response 401 (`_build_401`) berubah, frontend perlu update cara mendeteksi sesi berakhir
- Jika nama claim JWT berubah (misal `custom:role` → `role`), semua handler terpengaruh

---

## Requirements yang Dipenuhi

| Req ID | Deskripsi |
|--------|-----------|
| **7.1** | Sistem menggunakan JWT dari Cognito untuk autentikasi |
| **7.2** | Sesi pengguna dibatasi maksimal 8 jam sejak login (`auth_time`) |
| **7.3** | Role-based access: hanya `divisi_bisnis` dan `divisi_data` yang dikenali |

---

## Catatan Penting

### Keputusan Keamanan yang Perlu Dipahami

1. **Tidak ada re-verifikasi signature JWT**: Ini *by design*. Signature sudah divalidasi oleh Cognito authorizer di API Gateway sebelum request sampai ke Lambda. Verifikasi ulang di dalam Lambda memerlukan network call ke Cognito JWKS endpoint yang tidak perlu dan menambah latency.

2. **`auth_time` vs `exp`**: Modul ini menggunakan `auth_time` (waktu login awal) untuk batas 8 jam, bukan `exp` (waktu expiry token). Ini berarti meskipun Cognito mengeluarkan token baru saat refresh, sesi tetap berakhir 8 jam setelah login pertama.

3. **Fallback ke `"anonymous"` di audit.py**: Modul audit menggunakan mekanisme ekstraksi user tersendiri yang berbeda dari `require_auth` di sini. Handler yang sudah menggunakan `require_auth` sebaiknya meneruskan `user_id` ke fungsi audit secara eksplisit daripada mengandalkan fallback.

### Asumsi yang Dibuat

- Cognito dikonfigurasi dengan custom attribute `custom:role` yang diisi saat registrasi user.
- API Gateway dikonfigurasi sebagai **Cognito User Pools authorizer** sehingga setiap request yang sampai ke Lambda dijamin sudah memiliki token valid secara kriptografi.
- Lambda dijalankan dengan `TZ=UTC` atau tidak ada konversi timezone — `time.time()` mengembalikan Unix epoch UTC.

### Limitasi yang Diketahui

- **Tidak ada blacklisting token**: Jika token perlu di-revoke (misal karena akun diblokir), tidak ada mekanisme untuk memvalidasi blacklist. Revokasi hanya bisa dilakukan dengan menunggu token expired atau menghapus user di Cognito.
- **Role tunggal per user**: Struktur klaim `custom:role` hanya mendukung satu role per user. Multi-role tidak didukung.

### Todo untuk Pengembangan Berikutnya

- [ ] Tambah pengecekan role spesifik per endpoint (misal: hanya `divisi_data` yang bisa akses `customer_criteria`)
- [ ] Implementasi token blacklisting via DynamoDB untuk kasus logout paksa / akun diblokir
- [ ] Pertimbangkan caching decoded claims untuk mengurangi komputasi pada Lambda yang dipanggil berulang dalam satu sesi pendek
