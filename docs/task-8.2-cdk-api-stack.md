# Task 8.2 — CDK API Stack (API Gateway & Lambda Routing)

## Ringkasan Singkat

`ApiStack` adalah CDK stack yang menyediakan seluruh lapisan API aplikasi Campaign Insight Generator: tujuh Lambda function (satu per endpoint), sebuah REST API Gateway dengan autentikasi Cognito, konfigurasi CORS, throttling (429 response), logging ke CloudWatch, serta IAM roles dengan prinsip *least privilege*.

---

## Penjelasan Awam (Non-Technical)

Bayangkan sebuah resepsionis di bank yang menerima semua permintaan dari nasabah/pengguna:

- **API Gateway** adalah resepsionis tersebut — ia menerima permintaan dari aplikasi web, memastikan pengguna sudah login (Cognito), lalu meneruskan permintaan ke bagian yang tepat.
- **Lambda functions** adalah staf di belakang meja — masing-masing punya keahlian khusus (overview kampanye, perbandingan, ekspor, dst.).
- **IAM roles** adalah aturan akses: staf hanya boleh membuka laci yang mereka butuhkan, tidak lebih.
- **Throttling** adalah pembatasan antrean: jika terlalu banyak permintaan sekaligus, resepsionis mengembalikan pesan "harap tunggu" (HTTP 429) agar sistem tidak kewalahan.
- **CloudWatch Logs** adalah buku harian: setiap aktivitas dicatat untuk audit dan pemecahan masalah.

Manfaat bagi pengguna bisnis: laporan kampanye tampil cepat dan aman, akses hanya untuk pengguna yang berwenang, dan sistem tidak down saat banyak pengguna mengakses bersamaan.

---

## Penjelasan Teknis

### File yang Dibuat / Dimodifikasi

| File | Aksi |
|------|------|
| `backend/infrastructure/stacks/api_stack.py` | Dibuat (menggantikan stub) |

### Library / Framework

- **AWS CDK v2** (`aws_cdk`) — Infrastructure as Code untuk AWS
- `aws_apigateway` — REST API Gateway constructs
- `aws_lambda` — Lambda function constructs
- `aws_iam` — IAM policy statements
- `aws_logs` — CloudWatch log group & retention

### Pola Arsitektur

- **Proxy Lambda Integration** (`proxy=True`) — API Gateway meneruskan seluruh event object ke Lambda, respons Lambda langsung dikembalikan ke klien.
- **Shared helper methods** — `_make_lambda()` dan `_attach_common_permissions()` menghindari duplikasi konfigurasi antar 7 fungsi.
- **Graceful stub handling** — `AuthStack` belum memiliki `user_pool` (diimplementasikan task 8.4); stack ini menggunakan `getattr(auth_stack, "user_pool", None)` dan fallback ke `AuthorizationType.NONE` agar CDK tetap dapat di-synthesize.

### Keputusan Desain Penting

1. **Lambda timeout = 35 detik** — sedikit di atas batas polling Athena 30 detik, memberi buffer jika kueri lambat.
2. **API GW integration timeout = 29 detik** — batas maksimum yang didukung API Gateway untuk integrasi Lambda.
3. **`data_trace_enabled=False`** — body request/response TIDAK dilog karena berisi data sensitif nasabah (PII).
4. **Handler path** — path handler di-convert dari slash (`lambdas/campaign_overview/handler.lambda_handler`) ke dot notation (`lambdas.campaign_overview.handler.lambda_handler`) sesuai konvensi Lambda.
5. **Presigned URL** — tidak memerlukan IAM action tambahan; `s3:GetObject` yang sudah diberikan cukup untuk `boto3.generate_presigned_url()`.

### Edge Cases yang Ditangani

- AuthStack stub (task 8.4 belum selesai): fallback ke `NONE` auth tanpa error
- Setiap Lambda mendapat log group sendiri dengan retensi 1 bulan
- GSI similarity table disertakan dalam IAM resource ARN (`/index/*`)

---

## Struktur Kode

### Class: `ApiStack(Stack)`

```python
class ApiStack(Stack):
    def __init__(self, scope, construct_id, env_name, data_stack, auth_stack, **kwargs)
    # → membangun seluruh infrastruktur API
```

### Private Helpers

| Method | Deskripsi |
|--------|-----------|
| `_build_shared_env(env_name)` | Membuat dict env vars yang diinjeksikan ke semua Lambda (Athena DB, S3 bucket, DynamoDB table names) |
| `_make_lambda(construct_id, handler, environment)` | Membuat Lambda function dengan runtime, timeout, memory, dan log retention standar |
| `_attach_common_permissions(fn)` | Melampirkan Athena managed policy + IAM statements S3/DynamoDB ke sebuah Lambda |
| `_add_method(resource, http_method, fn, ...)` | Menambahkan method HTTP ke resource API Gateway dengan Lambda integration |

### Exposed Attributes

```python
self.api      # apigw.RestApi — digunakan cross-stack jika diperlukan
self.api_url  # str — base URL API yang dideploy
```

---

## Simulasi / Skenario

### Skenario 1 — GET /api/campaigns/overview (Happy Path)

```
Pengguna membuka dashboard → browser mengirim:
  GET https://<api-id>.execute-api.ap-southeast-1.amazonaws.com/dev/api/campaigns/overview
  Authorization: Bearer <cognito-jwt-token>
  
API Gateway:
  1. Validasi token JWT dengan Cognito (cache 5 menit)
  2. Throttle check: 85 req/s saat ini → OK (di bawah 100)
  3. Forward ke CampaignOverviewFn

Lambda (CampaignOverviewFn):
  - Query Athena → campaign_overview_agg
  - Return JSON response

API Gateway → Browser: 200 OK { total_leads: 15000, take_up_rate: 12.3%, ... }
```

### Skenario 2 — Rate Limit Terlampaui (429)

```
Bot atau user yang mengirim terlalu banyak request:
  → 51 request simultan diterima API Gateway
  → Request ke-51 melebihi burst limit (50)
  
API Gateway mengembalikan:
  429 Too Many Requests
  { "message": "Too Many Requests" }
  
Lambda TIDAK dipanggil → biaya terkontrol.
```

### Skenario 3 — Stub AuthStack (sebelum task 8.4 selesai)

```
CDK synth dijalankan:
  auth_stack.user_pool = None  (belum diimplementasikan)
  
ApiStack mendeteksi: getattr(auth_stack, "user_pool", None) → None
  authorizer = None
  auth_type = AuthorizationType.NONE
  
CDK synthesize BERHASIL — deployment dapat dilanjutkan.
Setelah task 8.4 selesai: user_pool tersedia → authorizer aktif otomatis.
```

---

## Keterkaitan dengan Komponen Lain

- **Bergantung pada:**
  - `DataStack` (task 8.1) — ARN S3 buckets dan DynamoDB tables
  - `AuthStack` (task 8.4) — Cognito user pool (stub saat ini)
  - Semua Lambda handlers di `backend/lambdas/*/handler.py` (tasks 4.1–4.7)

- **Digunakan oleh:**
  - Frontend React app (task 10.x) — memanggil endpoint via `api.ts`
  - `app.py` — entry point CDK yang meng-instantiate stack ini

- **Pengaruh ke:**
  - Mengubah `throttling_rate_limit` → mempengaruhi biaya dan perilaku burst
  - Mengubah `timeout` Lambda → mempengaruhi batas waktu kueri Athena
  - Menambah endpoint baru → tambah resource + method + Lambda di sini

---

## Requirements yang Dipenuhi

| Requirement | Keterangan |
|-------------|------------|
| **1.2** | Semua 7 endpoint API terdaftar dan dapat diakses melalui API Gateway |
| **7.1** | Infrastruktur CDK as Code — dapat di-deploy ulang secara konsisten |
| **7.4** | CloudWatch logging, throttling (429), dan Cognito authorizer terpasang |

---

## Catatan Penting

1. **AuthStack masih stub** — setelah task 8.4 menambahkan `self.user_pool`, authorizer akan aktif secara otomatis tanpa perubahan di file ini.
2. **Lambda code asset** — `lambda_.Code.from_asset("../")` mengemas seluruh direktori `backend/`. Untuk produksi, pertimbangkan Docker bundling atau Lambda layers untuk dependensi besar.
3. **Athena workgroup** — environment variable `ATHENA_WORKGROUP` harus dibuat secara manual atau melalui Glue stack (task 8.3) sebelum deployment pertama.
4. **CORS** — saat ini mengizinkan semua origin (`ALL_ORIGINS`). Untuk produksi, ganti dengan daftar domain yang spesifik.
5. **Integration timeout 29 detik** — batas keras dari API Gateway; kueri Athena yang melebihi 29 detik akan mendapatkan 504 Gateway Timeout meski Lambda masih berjalan.
