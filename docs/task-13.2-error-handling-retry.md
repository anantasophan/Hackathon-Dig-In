# Task 13.2 — Error Handling & Retry Logic

## Ringkasan Singkat

Task ini mengimplementasikan mekanisme ketahanan (resilience) untuk lapisan komunikasi antara frontend dan backend. Ketika layanan API mengalami gangguan sementara, sistem akan secara otomatis mencoba ulang permintaan dengan jeda waktu yang semakin panjang (exponential backoff). Apabila kegagalan terus terjadi hingga 5 kali berturut-turut, sistem akan menampilkan banner peringatan kepada pengguna sehingga mereka tahu layanan sedang bermasalah dan tidak perlu terus mencoba secara manual.

---

## Penjelasan Awam (Non-Technical)

**Analoginya seperti kasir di bank yang sedang sibuk:**

Bayangkan Anda ingin bertransaksi di counter bank, tetapi teller-nya sedang melayani banyak nasabah lain dan sistem ATM-nya lambat. Alih-alih langsung bilang "maaf tidak bisa", kasir akan:

1. **Mencoba lagi** — setelah 1 detik, lalu 2 detik, lalu 4 detik (total 3 percobaan ulang)
2. **Memberi tahu Anda** — setelah 5 kali gagal berturut-turut, teller pasang pengumuman di loket: "Layanan sementara tidak tersedia. Harap coba lagi nanti."
3. **Ada tombol "Coba Lagi"** — saat sistem sudah pulih, Anda tinggal klik tombol untuk memulai kembali tanpa perlu me-refresh halaman.

**Manfaat bagi pengguna bisnis (Campaign Owner):**
- Tidak perlu refresh halaman berulang kali saat server sibuk
- Mendapat informasi yang jelas ketika layanan betul-betul bermasalah
- Pengalaman lebih nyaman: kegagalan kecil diselesaikan secara otomatis di balik layar

---

## Penjelasan Teknis

### File yang Dibuat / Dimodifikasi

| File | Aksi | Deskripsi |
|------|------|-----------|
| `frontend/src/services/retryService.ts` | **Baru** | Fungsi `withRetry` dengan exponential backoff |
| `frontend/src/hooks/useCircuitBreaker.ts` | **Baru** | React hook `useCircuitBreaker` |
| `frontend/src/components/CircuitBreakerBanner.tsx` | **Baru** | Komponen banner peringatan |
| `frontend/src/services/api.ts` | **Diperbarui** | Tambah class `ApiServiceUnavailableError` (503) dan handler di response interceptor |
| `backend/shared/rate_limiter.py` | **Baru** | Helper Python untuk membangun respons 429 dengan header `Retry-After` |

### Library / Framework

- **Frontend**: React 18, TypeScript (strict mode)
- **Backend**: Python 3.11, AWS API Gateway Lambda Proxy pattern

### Pola Arsitektur

#### 1. Exponential Backoff (`retryService.ts`)

```typescript
// Urutan delay: 1000ms → 2000ms → 4000ms (maksimal 3 retry)
const delayMs = baseDelayMs * Math.pow(2, attempt - 1);
```

Hanya error *transient* yang di-retry:
- `ApiTimeoutError` (HTTP 408) — query Athena melewati batas waktu
- `ApiServiceUnavailableError` (HTTP 503) — layanan sementara tidak tersedia

Error *permanen* langsung dilempar tanpa retry:
- 400 Bad Request — data input tidak valid
- 401 Unauthorized — sesi expired
- 429 Rate Limited — quota habis
- 500 Internal Server Error — bug di server

#### 2. Circuit Breaker (`useCircuitBreaker.ts`)

Pattern klasik circuit breaker dalam bentuk React hook:
- **Closed** (normal): `isOpen = false`, permintaan berjalan seperti biasa
- **Open** (tripped): `isOpen = true` setelah N kegagalan berturut-turut
- **Reset**: satu sukses atau panggilan `reset()` mengembalikan ke Closed

```typescript
// Threshold default: 5 kegagalan berturut-turut
const { isOpen, recordFailure, recordSuccess, reset } = useCircuitBreaker(5);
```

#### 3. Banner Peringatan (`CircuitBreakerBanner.tsx`)

- Hanya ditampilkan ketika `isOpen = true` (return `null` jika closed)
- Menggunakan `role="alert"` dan `aria-live="assertive"` untuk aksesibilitas screen reader
- Styling inline (tidak bergantung file CSS eksternal) untuk portabilitas

#### 4. Rate Limit Response (`rate_limiter.py`)

API Gateway sudah mengkonfigurasi throttling di level infrastruktur (`throttling_rate_limit=100`, `throttling_burst_limit=50`), sehingga 429 dari API Gateway sudah termasuk header `Retry-After`. Fungsi `rate_limit_response()` disediakan untuk Lambda handler yang perlu menerapkan **application-level** rate limiting (misalnya quota per-user berdasarkan DynamoDB).

### Keputusan Desain Penting

1. **Retry hanya untuk 408 dan 503** — 500 tidak di-retry karena biasanya merupakan bug server yang tidak akan sembuh dengan mencoba ulang. Retry pada 500 justru bisa memperburuk beban server.

2. **Max 3 retry (4 total call)** — sesuai spesifikasi task. Total waktu tunggu maksimum: 1s + 2s + 4s = 7 detik sebelum menyerah.

3. **Circuit breaker di frontend** — Meski backend sudah mempunyai retry built-in, circuit breaker di frontend mencegah "thundering herd" — yaitu situasi di mana banyak komponen serentak mengirim request ke server yang sudah kewalahan.

4. **`onRetry` callback opsional** — Memungkinkan komponen menampilkan UI "Sedang mencoba ulang... (percobaan 2/4)" tanpa coupling ke logika retry.

---

## Struktur Kode

### `retryService.ts`

```typescript
// Type untuk konfigurasi retry
interface RetryOptions {
  maxAttempts?: number;     // default 3
  baseDelayMs?: number;     // default 1000
  onRetry?: (attempt: number, error: Error, delayMs: number) => void;
}

// Fungsi utama — wrapper async dengan retry
async function withRetry<T>(fn: () => Promise<T>, options?: RetryOptions): Promise<T>

// Helper internal
function isRetryable(error: unknown): boolean  // cek ApiTimeoutError | ApiServiceUnavailableError
function sleep(ms: number): Promise<void>       // Promise.setTimeout wrapper
```

### `useCircuitBreaker.ts`

```typescript
interface CircuitBreakerState {
  isOpen: boolean;
  recordFailure: () => void;   // panggil saat request gagal
  recordSuccess: () => void;   // panggil saat request berhasil
  reset: () => void;           // paksa tutup circuit + reset counter
}

function useCircuitBreaker(threshold?: number): CircuitBreakerState
```

### `CircuitBreakerBanner.tsx`

```tsx
interface CircuitBreakerBannerProps {
  isOpen: boolean;
  failureCount?: number;   // untuk pesan yang lebih informatif
  onReset: () => void;     // dipanggil saat tombol "Coba Lagi" diklik
}

const CircuitBreakerBanner: React.FC<CircuitBreakerBannerProps>
```

### `rate_limiter.py`

```python
def rate_limit_response(
    retry_after_seconds: int = 60,
    message: str = "Terlalu banyak permintaan — harap tunggu sebelum mencoba lagi.",
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Membangun respons 429 Lambda proxy lengkap dengan header Retry-After."""
```

---

## Simulasi / Skenario

### Skenario 1: Retry Berhasil pada Percobaan Ke-2

**Input**: Pengguna membuka halaman Campaign Overview. Server Athena sedang sibuk.

**Proses**:
```
Attempt 1 → 408 Timeout (Athena query timeout)
  → isRetryable: true
  → wait 1000ms
Attempt 2 → 200 OK ✅
```

**Output**: Halaman tampil normal. Pengguna tidak melihat apapun — retry terjadi di balik layar.

---

### Skenario 2: Circuit Breaker Terbuka

**Input**: Koneksi internet pengguna buruk. Lima permintaan berturut-turut ke server gagal.

**Proses**:
```
Request 1 → Error → recordFailure() → failures = 1
Request 2 → Error → recordFailure() → failures = 2
Request 3 → Error → recordFailure() → failures = 3
Request 4 → Error → recordFailure() → failures = 4
Request 5 → Error → recordFailure() → failures = 5 → isOpen = true
```

**Output**: Banner kuning muncul di halaman:
> ⚠️ Layanan sementara tidak tersedia (5 kegagalan berturut-turut). Harap coba lagi nanti.
> [Coba Lagi]

---

### Skenario 3: Reset Circuit Breaker

**Input**: Pengguna klik tombol "Coba Lagi" setelah circuit breaker terbuka.

**Proses**:
```
onReset() dipanggil
  → reset() → failures = 0, isOpen = false
  → Banner menghilang
  → Fetch data dipanggil ulang
Request → 200 OK → recordSuccess()
```

**Output**: Halaman memuat data baru berhasil.

---

### Skenario 4: Rate Limit dari Backend (Lambda)

**Input**: Lambda handler mendeteksi pengguna sudah melampaui quota.

**Proses (Python)**:
```python
from shared.rate_limiter import rate_limit_response

return rate_limit_response(retry_after_seconds=30)
```

**Output** (respons HTTP):
```json
HTTP 429
Retry-After: 30
Content-Type: application/json

{
  "message": "Terlalu banyak permintaan — harap tunggu sebelum mencoba lagi.",
  "retry_after": 30
}
```

Frontend menerima 429 → `ApiRateLimitError` di-throw → **tidak** di-retry (non-retryable) → UI menampilkan pesan "harap tunggu 30 detik".

---

## Keterkaitan dengan Komponen Lain

**Bergantung pada:**
- `frontend/src/services/api.ts` — `ApiTimeoutError`, `ApiServiceUnavailableError` harus sudah terdefinisi sebelum `retryService.ts` mengimpornya
- React & `useState`, `useCallback` — untuk `useCircuitBreaker`

**Digunakan oleh:**
- Setiap page component yang memanggil API (CampaignOverviewPage, CampaignComparisonPage, dst.)
- Contoh pola integrasi:
  ```tsx
  const { isOpen, recordFailure, recordSuccess, reset } = useCircuitBreaker();

  const fetchData = async () => {
    try {
      const result = await withRetry(() => api.getCampaignOverview(params));
      recordSuccess();
      setData(result);
    } catch (err) {
      recordFailure();
    }
  };

  return (
    <>
      <CircuitBreakerBanner isOpen={isOpen} onReset={() => { reset(); fetchData(); }} />
      {/* ... */}
    </>
  );
  ```

**Pengaruh jika diubah:**
- Mengubah `isRetryable()` di `retryService.ts` akan mengubah error mana yang mendapat retry
- Mengubah `threshold` default di `useCircuitBreaker` akan mengubah sensitivitas deteksi kegagalan
- `CircuitBreakerBanner` menggunakan inline styles — tidak ada CSS global yang perlu diperbarui jika styling berubah

---

## Requirements yang Dipenuhi

| Requirement | Deskripsi |
|-------------|-----------|
| **8.4** | Frontend retry dengan exponential backoff (1s, 2s, 4s) untuk status 408 dan 503, maksimal 3 percobaan ulang |
| **8.5** | Circuit breaker: tampilkan banner peringatan setelah 5 kegagalan berturut-turut; tombol "Coba Lagi" untuk reset |

---

## Catatan Penting

### Limitasi yang Diketahui

1. **Circuit breaker bersifat per-komponen** — setiap page yang memanggil `useCircuitBreaker()` mendapat instance terpisah. Jika ingin circuit breaker global (shared across pages), perlu di-lift ke Context API atau state management (Redux/Zustand).

2. **Tidak ada half-open state** — implementasi ini tidak mengimplementasikan transisi "half-open" (uji coba satu request untuk melihat apakah server sudah pulih). Reset dilakukan secara manual oleh pengguna via tombol "Coba Lagi".

3. **Rate limiter di backend adalah opsional** — API Gateway sudah menangani throttling di level infrastruktur. `rate_limiter.py` hanya dipakai jika Lambda handler mengimplementasikan logika quota tambahan.

### Asumsi yang Dibuat

- `withRetry` tidak menyimpan state — setiap panggilan `withRetry()` memulai hitungan retry dari nol
- Threshold circuit breaker default (5) sudah mencakup kemungkinan error transient normal
- Status 503 dari API Gateway (tidak dari Lambda) juga akan ditangkap oleh `ApiServiceUnavailableError`

### Todo untuk Pengembangan Berikutnya

- [ ] Implementasi circuit breaker global via React Context
- [ ] Tambah state "half-open" untuk auto-recovery
- [ ] Integrasi `onRetry` callback ke UI (toast "Mencoba lagi... 2/4")
- [ ] Unit test untuk `withRetry` (vitest + fake timers)
- [ ] Unit test untuk `useCircuitBreaker` (React Testing Library)
