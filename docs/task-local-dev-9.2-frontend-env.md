# Task 9.2 — Konfigurasi Frontend Environment (`frontend/.env.local`)

## Ringkasan Singkat

Task ini membuat file konfigurasi environment untuk aplikasi frontend React, yang memberitahu frontend ke mana harus mengirim permintaan API. File ini mengarahkan semua panggilan API ke local development server yang berjalan di `http://localhost:8000`.

## Penjelasan Awam (Non-Technical)

Bayangkan aplikasi frontend seperti resepsionis yang perlu tahu nomor telepon bagian back-office sebelum bisa meneruskan pertanyaan. File `.env.local` ini berisi "nomor telepon" tersebut — yaitu alamat server backend lokal. Tanpa konfigurasi ini, frontend tidak tahu harus mengirim data ke mana, sehingga semua fitur yang memerlukan data kampanye tidak akan berfungsi saat development.

Manfaat bagi tim: developer bisa menjalankan aplikasi lengkap secara lokal di laptop mereka sendiri tanpa perlu koneksi ke server production.

## Penjelasan Teknis

- **File yang dibuat**: `frontend/.env.local`
- **Isi file**:
  ```
  REACT_APP_API_URL=http://localhost:8000
  ```
- **Konvensi React**: Variabel environment dengan prefix `REACT_APP_` secara otomatis di-inject oleh Create React App (CRA) ke dalam bundle. Variabel ini tersedia di kode frontend melalui `process.env.REACT_APP_API_URL`.
- **`.env.local`** adalah file environment khusus lokal — tidak di-commit ke git (sudah masuk `.gitignore` secara default pada CRA). Ini memastikan setiap developer bisa punya konfigurasi lokal yang berbeda tanpa mempengaruhi kode bersama.
- **Port 8000** sesuai dengan FastAPI local development server yang dikonfigurasi di task-task sebelumnya (`backend/local_server/main.py`).

## Struktur Kode

File hanya berisi satu baris konfigurasi:

```dotenv
REACT_APP_API_URL=http://localhost:8000
```

Digunakan di kode frontend seperti:

```typescript
// Contoh penggunaan di API client
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const response = await fetch(`${API_BASE_URL}/campaigns/overview`);
```

## Simulasi / Skenario

**Skenario 1 — Development Normal**
- Developer menjalankan `uvicorn backend.local_server.main:app --port 8000`
- Developer menjalankan `npm start` di folder `frontend/`
- Frontend membaca `REACT_APP_API_URL=http://localhost:8000`
- Semua request API dikirim ke `http://localhost:8000/...`
- Data mock tampil di browser

**Skenario 2 — File Sudah Ada (Update)**
- Jika `.env.local` sudah ada dengan nilai berbeda (misal port lama)
- Task ini memastikan baris `REACT_APP_API_URL` diperbarui ke `http://localhost:8000`
- Baris lain yang sudah ada tidak diubah

## Keterkaitan dengan Komponen Lain

- **Bergantung pada**: Local development server (`backend/local_server/main.py`) yang harus berjalan di port 8000
- **Digunakan oleh**: Semua komponen frontend React yang melakukan API call (halaman Overview, Comparison, Time Analysis, Regional, dll)
- **Pengaruh ke**: Jika URL ini salah/berbeda, seluruh data kampanye tidak akan muncul di frontend

## Requirements yang Dipenuhi

- Frontend connectivity (task 9.2 dari spec `local-dev-server`)
- Memungkinkan frontend terhubung ke local mock backend tanpa konfigurasi tambahan

## Catatan Penting

- File ini **tidak boleh di-commit** ke git — sudah ditangani oleh `.gitignore` default CRA
- Untuk deployment production, gunakan environment variable yang sesuai di hosting platform (Vercel, Netlify, dll) — jangan hardcode URL production di file ini
- Jika backend berjalan di port berbeda, cukup ubah nilai di file ini tanpa mengubah kode frontend
