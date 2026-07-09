# Auto Documentation — Campaign Insight Generator

## Tujuan

Setiap kali sebuah task dari spec `campaign-insight-generator` selesai dikerjakan, **buat atau update file dokumentasi** di folder `C:\Users\robin\OneDrive\Documents\Project Kiro\docs\`.

---

## Kapan Dokumentasi Dibuat

Buat dokumentasi segera setelah:
1. Sebuah task spec ditandai `completed`
2. Sebuah file implementasi baru selesai dibuat (Lambda handler, ETL job, CDK stack, frontend component, dll)
3. Sebuah kelompok task (wave/batch) selesai dieksekusi

---

## Nama File dan Struktur Folder

Nama file menggunakan format: `{nomor-task}-{nama-singkat}.md`

Contoh:
- `task-1.6-athena-client.md`
- `task-4.1-campaign-overview-lambda.md`
- `task-7.2-aggregate-metrics-etl.md`
- `task-8.1-cdk-infrastructure.md`
- `task-10.x-frontend-core.md`

Simpan di: `C:\Users\robin\OneDrive\Documents\Project Kiro\docs\`

---

## Format Dokumen (Wajib Diikuti)

Setiap file dokumentasi harus mengandung SEMUA bagian berikut:

```markdown
# [Nama Task] — [Judul Deskriptif]

## Ringkasan Singkat
Satu paragraf: apa yang dibangun, untuk tujuan apa, siapa yang menggunakannya.

## Penjelasan Awam (Non-Technical)
Jelaskan seperti menjelaskan kepada orang yang tidak mengerti coding:
- Apa fungsinya dalam bahasa sehari-hari?
- Analoginya dengan kehidupan nyata apa?
- Apa manfaatnya bagi pengguna bisnis?

## Penjelasan Teknis
Detail implementasi untuk developer:
- File yang dibuat/dimodifikasi
- Library/framework yang digunakan
- Pola arsitektur yang diterapkan
- Keputusan desain penting dan alasannya
- Edge cases yang ditangani

## Struktur Kode (jika relevan)
Ringkasan fungsi/class utama dengan signature dan deskripsi singkat.

## Simulasi / Skenario
Berikan 1-3 skenario konkret:
- Input → Proses → Output
- Termasuk contoh data nyata jika memungkinkan
- Skenario happy path DAN skenario error/edge case

## Keterkaitan dengan Komponen Lain
- Bergantung pada: (komponen apa yang dibutuhkan)
- Digunakan oleh: (komponen apa yang memanggil ini)
- Pengaruh ke: (apa yang berubah jika ini berubah)

## Requirements yang Dipenuhi
Daftar requirement spec yang diselesaikan oleh task ini.

## Catatan Penting
Hal-hal yang perlu diperhatikan saat menggunakan/mengubah komponen ini:
- Limitasi yang diketahui
- Asumsi yang dibuat
- Todo untuk pengembangan berikutnya
```

---

## Aturan Penulisan

1. **Bahasa Indonesia** untuk konten, kecuali nama teknis (function, class, endpoint path) tetap dalam bahasa aslinya
2. **Tidak ada jargon tanpa penjelasan** — setiap istilah teknis harus dijelaskan dalam konteks awam
3. **Simulasi harus menggunakan data realistis** dari domain kampanye bank (QRIS, leads, nasabah, dll)
4. **Setiap kode snippet** harus disertai komentar penjelasan
5. **Panjang dokumen** proporsional dengan kompleksitas task — task sederhana boleh singkat, task kompleks harus lengkap

---

## Update Index

Setelah membuat dokumentasi baru, **selalu update** file `C:\Users\robin\OneDrive\Documents\Project Kiro\docs\README.md` dengan menambahkan entry baru ke tabel index.
