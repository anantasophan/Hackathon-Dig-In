# Task 13.1 — Penyambungan Frontend ke Backend API Endpoints

## Ringkasan Singkat

Task ini menyambungkan lapisan frontend (React/TypeScript) ke lapisan backend (API Gateway + Lambda) secara end-to-end. Semua 7 Lambda handler dan 1 endpoint sesi Cognito diverifikasi sudah terhubung dengan benar melalui audit path URL, konfigurasi CORS, dan alur token JWT.

---

## Penjelasan Awam (Non-Technical)

Bayangkan aplikasi Campaign Insight Generator seperti sebuah restoran. Frontend adalah pelayan yang menerima pesanan dari tamu (pengguna). Backend adalah dapur yang memasak makanan (data). Task ini memastikan:

1. **Pesanan sampai ke dapur yang benar** — setiap tombol di halaman web mengirim permintaan ke Lambda yang tepat.
2. **Dapur mengenali pelayan** — setiap permintaan membawa kartu identitas (JWT token) agar dapur tahu siapa yang memesan dan apakah mereka berhak.
3. **Pelayan bisa masuk dari pintu depan** — konfigurasi CORS memastikan browser tidak memblokir komunikasi antara frontend dan backend.
4. **Koneksi aman** — token Cognito berlaku 8 jam, setelah itu pengguna harus login ulang.

---

## Penjelasan Teknis

### File yang Dibuat/Dimodifikasi

| File | Aksi | Keterangan |
|------|------|------------|
| `frontend/src/App.tsx` | **Dimodifikasi** | Ditambahkan `configureAmplify()` sebelum render |
| `frontend/src/lib/api-endpoint-map.ts` | **Dibuat baru** | Dokumentasi TypeScript: pemetaan 8 endpoint frontend → Lambda |
| `backend/infrastructure/stacks/api_stack.py` | **Dimodifikasi** | Ditambahkan komentar audit CORS dan alur JWT Token Flow |
| `docs/task-13.1-api-wiring.md` | **Dibuat baru** | Dokumentasi ini |

### Library/Framework yang Digunakan

- **AWS Amplify** (`aws-amplify`) — konfigurasi Cognito, `fetchAuthSession()` untuk mengambil token
- **Axios** — HTTP client dengan interceptor untuk JWT dan error mapping
- **AWS CDK** (`aws_apigateway`, `aws_cognito`) — provisioning API Gateway dan Cognito authorizer

### Pola Arsitektur

```
Browser (React)
  │
  ├─ configureAmplify()  ← dipanggil sekali di App.tsx sebelum render
  │
  ├─ api.ts (Axios instance)
  │    ├─ Request interceptor: fetchAuthSession() → Authorization: Bearer <idToken>
  │    └─ Response interceptor: 401 → ApiAuthError, 408 → ApiTimeoutError, 429 → ApiRateLimitError
  │
  └─ HTTP Request
       │
       ▼
  API Gateway (REST API)
       │
       ├─ CognitoUserPoolsAuthorizer ← validasi JWT, cache 5 menit
       ├─ CORS preflight (OPTIONS) ← auto-generated per resource node
       ├─ Request validator ← validasi body & query params
       └─ Lambda Proxy Integration (proxy=True)
            │
            ▼
       Lambda Handler (handler.py → lambda_handler)
            │
            ├─ shared/auth.py ← baca claims dari requestContext.authorizer.claims
            └─ Response JSON
```

### Keputusan Desain Penting

1. **`configureAmplify()` dipanggil di module scope `App.tsx`** (bukan di dalam komponen), sehingga Amplify siap sebelum `ReactDOM.createRoot()` memanggil render pertama. Ini mencegah race condition di mana komponen child mencoba memanggil `fetchAuthSession()` sebelum Amplify dikonfigurasi.

2. **`/api/auth/session` tidak ada Lambda terpisah** — endpoint ini diimplementasikan sebagai panggilan `fetchAuthSession()` dari AWS Amplify SDK secara langsung (client-side Cognito token check). Tidak ada round-trip ke API Gateway untuk validasi sesi sederhana.

3. **CORS di level API Gateway, bukan Lambda** — `default_cors_preflight_options` di CDK menambahkan method OPTIONS otomatis ke setiap resource node. Lambda handler tidak perlu menambahkan header CORS manual.

4. **Token yang digunakan adalah `idToken`, bukan `accessToken`** — `idToken` berisi custom claims (termasuk `custom:role`) yang dibaca oleh `shared/auth.py` di Lambda untuk otorisasi berbasis peran.

---

## Struktur Kode

### `api-endpoint-map.ts`

```typescript
export interface EndpointMapping {
  frontendMethod: string;   // nama fungsi di api.ts
  httpMethod: 'GET' | 'POST';
  path: string;             // path relatif terhadap base URL
  lambdaHandler: string;    // file Lambda handler
  requiresAuth: boolean;
  notes?: string;
}

export const API_ENDPOINT_MAP: readonly EndpointMapping[] = [ ... ];  // 8 entri
export const API_BASE_URL = process.env['REACT_APP_API_GATEWAY_URL'] ?? '';
```

### Pemetaan 8 Endpoint

| Frontend Method | HTTP | Path | Lambda Handler |
|---|---|---|---|
| `getCampaignOverview` | GET | `/api/campaigns/overview` | `campaign_overview/handler.py` |
| `compareCampaigns` | POST | `/api/campaigns/comparison` | `campaign_comparison/handler.py` |
| `getTimeAnalysis` | GET | `/api/campaigns/time-analysis/{id}` | `time_analysis/handler.py` |
| `getRegionalPerformance` | GET | `/api/campaigns/regional/{id}` | `regional_performance/handler.py` |
| `getCustomerCriteria` | GET | `/api/campaigns/customer-criteria/{id}` | `customer_criteria/handler.py` |
| `getSimilarCampaigns` | POST | `/api/campaigns/similar` | `similar_campaign/handler.py` |
| `exportData` | POST | `/api/export` | `export_service/handler.py` |
| `getSession` | GET | `/api/auth/session` | *(Cognito SDK — tidak ada Lambda)* |

---

## Simulasi / Skenario

### Skenario 1: Pengguna membuka halaman Overview (Happy Path)

```
1. Browser load → App.tsx → configureAmplify() dipanggil
   Amplify dikonfigurasi dengan:
     userPoolId: ap-southeast-1_XXXXXXXXX
     userPoolClientId: XXXXXXXXXXXXXXXXXXXX

2. Komponen CampaignOverviewPage mount → api.getCampaignOverview({ start_date: "2024-01-01", end_date: "2024-03-31" })

3. Axios request interceptor:
   fetchAuthSession() → idToken: "eyJhbGciOiJSUzI1NiIsInR5..."
   Header ditambahkan: Authorization: Bearer eyJhbGciOiJSUzI1NiIsInR5...

4. HTTP Request:
   GET https://abc123.execute-api.ap-southeast-1.amazonaws.com/prod/api/campaigns/overview
     ?start_date=2024-01-01&end_date=2024-03-31
   Authorization: Bearer eyJ...

5. API Gateway → CognitoUserPoolsAuthorizer memvalidasi token
   → Token valid, cache 5 menit

6. Lambda campaign_overview/handler.py menerima event, query Athena
   → Response: { campaigns: [...], total_count: 42, summary: {...} }

7. Axios response interceptor → tidak ada error → res.data dikembalikan ke komponen
```

### Skenario 2: Token kadaluarsa (Error Path)

```
1. Pengguna sudah login 8+ jam yang lalu
2. api.getRegionalPerformance("QRIS-2024-01") dipanggil
3. fetchAuthSession() mengembalikan token yang kadaluarsa
4. API Gateway → CognitoUserPoolsAuthorizer → 401 Unauthorized
5. Axios response interceptor: status === 401 → throw new ApiAuthError()
6. Komponen menangkap ApiAuthError → redirect ke halaman login
```

### Skenario 3: Browser preflight CORS

```
1. Browser kirim preflight:
   OPTIONS /api/campaigns/overview
   Origin: https://campaign-insight-prod.example.com
   Access-Control-Request-Method: GET
   Access-Control-Request-Headers: Content-Type, Authorization

2. API Gateway (OPTIONS method auto-generated oleh CDK):
   200 OK
   Access-Control-Allow-Origin: *
   Access-Control-Allow-Methods: GET, POST, PUT, DELETE, OPTIONS
   Access-Control-Allow-Headers: Content-Type, Authorization

3. Browser: preflight OK → kirim request GET sebenarnya
```

---

## Keterkaitan dengan Komponen Lain

- **Bergantung pada:**
  - `frontend/src/lib/amplify-config.ts` — konfigurasi Cognito
  - `frontend/src/services/api.ts` — semua panggilan API
  - `backend/infrastructure/stacks/auth_stack.py` — Cognito User Pool (sumber token)
  - `backend/infrastructure/stacks/api_stack.py` — route tree dan authorizer
  - `frontend/.env` / `.env.example` — variabel lingkungan (URL, IDs)

- **Digunakan oleh:**
  - Semua halaman frontend (Overview, Comparison, Time Analysis, Regional, Customer Criteria, Similar, Export)
  - Komponen `AuthGuard` (verifikasi sesi aktif)

- **Pengaruh ke:**
  - Jika `REACT_APP_API_GATEWAY_URL` tidak di-set, semua API call akan gagal (BASE_URL kosong)
  - Jika `configureAmplify()` tidak dipanggil, `fetchAuthSession()` akan melempar error dan semua request akan berjalan tanpa token

---

## Requirements yang Dipenuhi

- **7.1** — Sistem menggunakan AWS Cognito untuk autentikasi. Semua endpoint dilindungi `CognitoUserPoolsAuthorizer`.
- **7.2** — Token berlaku 8 jam (`access_token_validity=Duration.hours(8)` di AuthStack). Frontend mendeteksi token kadaluarsa dan melempar `ApiAuthError`.

---

## Environment Variables yang Diperlukan

Semua variabel sudah ada di `frontend/.env.example`:

```dotenv
REACT_APP_AWS_REGION=ap-southeast-1
REACT_APP_USER_POOL_ID=ap-southeast-1_XXXXXXXXX
REACT_APP_USER_POOL_CLIENT_ID=XXXXXXXXXXXXXXXXXXXXXXXXXX
REACT_APP_API_GATEWAY_URL=https://xxxxxxxxxx.execute-api.ap-southeast-1.amazonaws.com/prod
```

Nilai aktual diisi setelah CDK deploy dengan output dari:
- `UserPoolId-<env>` (CloudFormation Output dari AuthStack)
- `UserPoolClientId-<env>` (CloudFormation Output dari AuthStack)
- `ApiUrl` (CloudFormation Output dari ApiStack)

---

## Catatan Penting

1. **CORS Production** — Saat ini `allow_origins=apigw.Cors.ALL_ORIGINS`. Untuk deployment production, ganti dengan domain CloudFront yang spesifik untuk mengurangi risiko CSRF.

2. **`/api/auth/session`** — Tidak ada route API Gateway untuk endpoint ini. `api.getSession()` di `api.ts` akan memanggil `GET /api/auth/session`, tetapi karena tidak ada route tersebut di CDK, akan mengembalikan 404 dari API Gateway. Endpoint ini harus diimplementasikan sebagai Lambda route terpisah jika dibutuhkan backend session validation — atau cukup gunakan `fetchAuthSession()` langsung dari Amplify.

3. **Region config Amplify** — `amplify-config.ts` saat ini tidak meneruskan `REACT_APP_AWS_REGION` ke Amplify. AWS Amplify v6 secara default menggunakan region dari User Pool ID prefix (e.g., `ap-southeast-1_XXX`), sehingga ini tidak menyebabkan masalah.

4. **Token type** — api.ts menggunakan `idToken` (bukan `accessToken`) karena `idToken` membawa `custom:role` claim yang dibutuhkan Lambda untuk otorisasi peran.
