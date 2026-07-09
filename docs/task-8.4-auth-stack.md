# Task 8.4 — Auth Stack (Cognito User Pool & Authorizer)

## Ringkasan Singkat

`AuthStack` adalah CDK stack yang menyiapkan sistem autentikasi berbasis Amazon Cognito untuk Campaign Insight Generator. Stack ini membuat User Pool (daftar pengguna), User Pool Client (konfigurasi akses dari frontend), dan mengekspos properti yang dibutuhkan oleh `ApiStack` untuk memvalidasi JWT token di setiap API request.

---

## Penjelasan Awam (Non-Technical)

Bayangkan sebuah gedung kantor dengan sistem kartu akses. Tidak semua orang bisa masuk — hanya karyawan terdaftar yang mendapat kartu akses dari admin. Setelah masuk, kartu tersebut berlaku selama 8 jam kerja, setelah itu karyawan harus "login" ulang.

`AuthStack` adalah **sistem kartu akses digital** untuk dashboard Campaign Insight:
- **Admin mendaftarkan pengguna** — karyawan tidak bisa mendaftar sendiri
- **Dua jenis pengguna**: Divisi Bisnis (melihat data kampanye) dan Divisi Data (memantau efektivitas kampanye)
- **Sesi aktif 8 jam** — sesuai jam kerja normal, lalu otomatis diminta login ulang
- **Manfaat bisnis**: hanya orang yang berwenang yang bisa mengakses data kampanye sensitif

---

## Penjelasan Teknis

### File yang Dibuat/Dimodifikasi

| File | Aksi |
|------|------|
| `backend/infrastructure/stacks/auth_stack.py` | Dibuat (menggantikan stub) |

### Library/Framework

- **AWS CDK** (`aws_cdk`) — infrastructure as code
- **`aws_cdk.aws_cognito`** — construct library untuk Amazon Cognito
- **`aws_cdk.Duration`** — utility untuk token validity (8 jam, 30 hari)
- **`aws_cdk.RemovalPolicy`** — RETAIN di prod, DESTROY di non-prod

### Pola Arsitektur

`AuthStack` mengikuti pola yang sama dengan `DataStack`:
- Argumen `env_name` menentukan nama resource dan removal policy
- Properti publik (`user_pool`, `user_pool_client`, `user_pool_id`, `user_pool_client_id`) diekspos untuk digunakan oleh stack lain
- `CfnOutput` dengan `export_name` memungkinkan cross-stack referencing di CDK

### Keputusan Desain Penting

1. **`self_sign_up_enabled=False`**: Pengguna hanya bisa dibuat oleh admin — mencegah akses tidak sah ke data kampanye bank (Req 7.1)
2. **`generate_secret=False`**: Frontend SPA (React.js) adalah public client dan tidak dapat menyimpan secret dengan aman
3. **`access_token_validity=Duration.hours(8)`**: Sesuai Requirement 7.2 — sesi 8 jam per hari kerja
4. **Custom attribute `role`**: Menyimpan nilai `divisi_bisnis` atau `divisi_data` sebagai JWT claim untuk PII filtering di Lambda
5. **Removal policy kondisional**: User pool di `prod` dipertahankan (`RETAIN`) untuk mencegah hilangnya akun produksi; di `dev`/`staging` otomatis dihapus saat stack di-destroy

### Edge Cases yang Ditangani

- Token validity seragam: access token dan id token sama-sama 8 jam agar tidak ada inkonsistensi di frontend
- Callback URL menyertakan `localhost:3000` untuk keperluan development lokal
- `prevent_user_existence_errors=True`: mencegah enumerasi username (keamanan)

---

## Struktur Kode

### `AuthStack.__init__`

```python
def __init__(self, scope, construct_id, env_name, **kwargs) -> None:
    """Inisialisasi Cognito User Pool dan User Pool Client."""
```

**Urutan provisioning:**

1. `cognito.UserPool` → User Pool dengan password policy, custom attribute `role`, sign-in via username/email
2. `cognito.UserPoolClient` → Client SPA tanpa secret, OAuth2 authorization code flow, token 8 jam
3. Properti publik: `user_pool`, `user_pool_client`, `user_pool_id`, `user_pool_client_id`
4. `cdk.CfnOutput` → ekspor `UserPoolId` dan `UserPoolClientId` dengan nama `*-{env_name}`

---

## Simulasi / Skenario

### Skenario 1 — Login Pengguna Divisi Bisnis (Happy Path)

**Input**: Admin membuat akun dengan `custom:role = divisi_bisnis`

**Proses**:
1. Pengguna membuka dashboard → redirect ke Cognito Hosted UI
2. Masukkan username + password → Cognito memvalidasi
3. Cognito mengembalikan JWT (access token + id token, keduanya valid 8 jam)
4. Frontend menyimpan token di memory → API Gateway memvalidasi setiap request

**Output**: Pengguna bisa mengakses semua halaman dashboard; data PII difilter berdasarkan role

### Skenario 2 — Sesi Kedaluwarsa

**Input**: Pengguna aktif selama >8 jam tanpa refresh

**Proses**:
1. Access token expired (8 jam berlalu)
2. API Gateway menolak request → 401 Unauthorized
3. Frontend mendeteksi 401 → redirect ke halaman login dengan pesan "Sesi telah berakhir"

**Output**: Pengguna diarahkan login ulang; refresh token (30 hari) memungkinkan login seamless jika frontend menggunakannya

### Skenario 3 — Environment Dev vs Prod

**Input**: CDK deploy dengan `env_name="dev"` vs `env_name="prod"`

**Proses**:
- `dev`: `RemovalPolicy.DESTROY` → User Pool ikut terhapus saat `cdk destroy`
- `prod`: `RemovalPolicy.RETAIN` → User Pool tetap ada meskipun stack dihapus

**Output**: Data pengguna produksi terlindungi dari penghapusan tidak disengaja

---

## Keterkaitan dengan Komponen Lain

- **Bergantung pada**: Tidak ada dependensi ke stack lain
- **Digunakan oleh**: `ApiStack` — menggunakan `user_pool` untuk membuat Cognito Authorizer di API Gateway; Lambda handlers membaca JWT claims (`custom:role`) untuk PII filtering
- **Pengaruh ke**: Jika `user_pool_id` berubah (misal stack di-recreate), semua pengguna harus dibuat ulang dan frontend perlu update konfigurasi Amplify

---

## Requirements yang Dipenuhi

| Requirement | Deskripsi |
|-------------|-----------|
| **7.1** | Autentikasi berbasis Cognito; pengguna dibuat oleh admin |
| **7.2** | Sesi aktif 8 jam (access token validity = 8 jam) |
| **7.3** | Role attribute (`divisi_bisnis` / `divisi_data`) tersedia sebagai JWT claim |

---

## Catatan Penting

- **Custom attribute `custom:role`** harus di-set secara manual oleh admin saat membuat user, atau via Lambda trigger (AdminCreateUser)
- **Cognito Domain** tidak dikonfigurasi di stack ini — jika menggunakan Hosted UI, perlu tambahkan `cognito.UserPoolDomain`
- **MFA** tidak diaktifkan — pertimbangkan mengaktifkan TOTP di masa depan untuk keamanan lebih tinggi
- **OAuth callback URLs** menggunakan `example.com` sebagai placeholder — ganti dengan domain produksi aktual sebelum deploy
- Properti `user_pool` dan `user_pool_client` dapat diakses dari stack lain melalui dependency injection di `app.py`
