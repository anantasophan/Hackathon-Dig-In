# Git & GitHub Push — Panduan untuk Kiro

## Informasi Repository

- **Remote URL**: `https://github.com/anantasophan/Hackathon-Dig-In.git`
- **Owner**: `anantasophan`
- **Repo**: `Hackathon-Dig-In`
- **Default branch**: `main`

## GitHub Personal Access Token

Token tersimpan di `.kiro/settings/mcp.json` di field `GITHUB_PERSONAL_ACCESS_TOKEN`.

Gunakan token ini untuk autentikasi git push via HTTPS:

```powershell
git remote set-url origin "https://<TOKEN>@github.com/anantasophan/Hackathon-Dig-In.git"
git push -u origin main
```

## Cara Push yang Benar

Selalu gunakan token dari mcp.json — **jangan tanya user untuk token**.

Langkah standar:

1. Baca token dari `.kiro/settings/mcp.json`
2. Set remote URL dengan token: `git remote set-url origin "https://<TOKEN>@github.com/anantasophan/Hackathon-Dig-In.git"`
3. Stage semua file: `git add -A`
4. Commit: `git commit -m "pesan commit"`
5. Push: `git push -u origin main`
6. Jika ditolak karena history berbeda: `git push -u origin main --force`

## Aturan Penting

- **Jangan tanya user untuk Personal Access Token** — ambil langsung dari `.kiro/settings/mcp.json`
- **Jangan tanya GitHub username** — sudah diketahui: `anantasophan`
- **Jangan pakai branch baru** kecuali diminta — selalu push ke `main`
- **Force push diizinkan** jika remote menolak karena history berbeda
- Setelah push, verifikasi dengan `git log --oneline -3` atau cek via GitHub MCP
