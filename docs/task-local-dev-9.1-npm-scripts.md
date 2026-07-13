# Task 9.1 — Root `package.json` dengan npm Scripts

## Ringkasan Singkat

Membuat file `package.json` di root project yang menyediakan tiga npm script untuk menjalankan local development server: `dev:backend` (FastAPI), `dev:frontend` (React), dan `dev` (keduanya sekaligus via `concurrently`). File ini memungkinkan developer menjalankan seluruh stack lokal dengan satu perintah sederhana.

## Penjelasan Awam (Non-Technical)

Bayangkan sebuah proyek memiliki dua bagian: bagian belakang (backend, seperti dapur restoran) dan bagian depan (frontend, seperti meja pelanggan). Biasanya developer harus membuka dua terminal terpisah dan menjalankan dua perintah berbeda secara manual. Dengan `package.json` ini, cukup satu perintah `npm run dev` dan kedua bagian akan berjalan bersamaan secara otomatis — seperti menekan satu tombol untuk menyalakan seluruh restoran sekaligus.

Manfaat untuk pengguna bisnis: developer bisa mulai bekerja lebih cepat tanpa harus hafal perintah-perintah teknis yang panjang.

## Penjelasan Teknis

**File yang dibuat:**
- `c:\Users\robin\OneDrive\Documents\Project Kiro\package.json` (baru)

**Library yang digunakan:**
- `concurrently` v8.2.0 — paket npm yang memungkinkan beberapa perintah dijalankan secara paralel dalam satu terminal, dengan output yang diberi label berbeda agar mudah dibedakan

**Script yang ditambahkan:**

| Script | Perintah | Keterangan |
|--------|----------|------------|
| `dev:backend` | `cd backend && uvicorn local_server.main:app --reload --port 8000` | Menjalankan FastAPI local server di port 8000 dengan hot-reload |
| `dev:frontend` | `cd frontend && npm start` | Menjalankan React development server |
| `dev` | `concurrently "npm run dev:backend" "npm run dev:frontend"` | Menjalankan keduanya secara paralel |

**Kompatibilitas Windows PowerShell:**
- Menggunakan sintaks `cd backend && command` yang kompatibel dengan PowerShell dan CMD
- Tidak menggunakan operator `&&` dengan cara yang berbeda antar shell (yang bisa menyebabkan masalah di Windows)

**Keputusan desain:**
- `"private": true` mencegah package ini dipublikasikan ke npm secara tidak sengaja
- `concurrently` ditempatkan di `devDependencies` (bukan `dependencies`) karena hanya dibutuhkan saat development, tidak di production
- Versi `^8.2.0` mengikuti minor/patch updates secara otomatis namun terkunci di major version 8

## Struktur Kode

```json
{
  "name": "campaign-insight-generator-workspace",
  "private": true,
  "scripts": {
    "dev:backend": "cd backend && uvicorn local_server.main:app --reload --port 8000",
    "dev:frontend": "cd frontend && npm start",
    "dev": "concurrently \"npm run dev:backend\" \"npm run dev:frontend\""
  },
  "devDependencies": {
    "concurrently": "^8.2.0"
  }
}
```

## Simulasi / Skenario

### Skenario 1 — Menjalankan backend saja
```powershell
# Di root project
npm run dev:backend
# Output: Uvicorn running on http://127.0.0.1:8000
```

### Skenario 2 — Menjalankan frontend saja
```powershell
npm run dev:frontend
# Output: React App started on http://localhost:3000
```

### Skenario 3 — Menjalankan keduanya sekaligus
```powershell
# Install concurrently terlebih dahulu (hanya sekali)
npm install

# Jalankan full stack
npm run dev
# Output:
# [dev:backend]  Uvicorn running on http://127.0.0.1:8000
# [dev:frontend] React App started on http://localhost:3000
```

## Keterkaitan dengan Komponen Lain

- **Bergantung pada:** `backend/local_server/main.py` (FastAPI app entry point), `frontend/` (React app)
- **Digunakan oleh:** Developer yang ingin menjalankan local stack tanpa Docker/AWS
- **Pengaruh ke:** Task 9.2 (`frontend/.env.local`) yang mengatur `REACT_APP_API_URL=http://localhost:8000` agar frontend terhubung ke backend lokal ini

## Requirements yang Dipenuhi

- **Requirement 1.2**: Local_Server dapat dijalankan via npm script `npm run dev:backend` dari root project
- **Requirement 10.5**: npm script `dev:backend` di `package.json` root tersedia untuk menjalankan Local_Server

## Catatan Penting

- **Install dependencies terlebih dahulu:** Jalankan `npm install` di root project untuk menginstall `concurrently` sebelum menggunakan `npm run dev`
- **Python wajib tersedia:** Script `dev:backend` membutuhkan `uvicorn` yang hanya tersedia jika Python dan dependencies backend sudah diinstall (`pip install -r backend/requirements-dev.txt`)
- **Port 8000 harus bebas:** Pastikan tidak ada proses lain yang menggunakan port 8000 sebelum menjalankan backend
- **Frontend port:** React defaultnya menggunakan port 3000; jika sudah terpakai, React akan menawarkan port alternatif secara otomatis
