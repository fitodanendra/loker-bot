# Panduan Perawatan Loker Bot

Panduan ini untuk merawat bot tanpa bantuan programmer. Sebagian besar waktu bot
berjalan sendiri — Anda hanya perlu memperhatikan **tanggal penting** dan tahu
**ke mana melihat kalau ada masalah**.

---

## 1. Tanggal penting ⚠️

| Kapan | Apa | Akibat kalau lupa |
|---|---|---|
| **Sebelum 31 Desember 2026** | Token GitHub `loker-bot-cron` (dipakai cron-job.org) kedaluwarsa | Bot **berhenti total** — tidak ada lowongan baru |

**Cara memperpanjang** (±5 menit, lakukan sekitar pertengahan Desember):
1. Buka https://github.com/settings/personal-access-tokens → klik **loker-bot-cron** → **Regenerate token**.
   Pilih masa berlaku terlama → salin token baru (`github_pat_...`).
2. Buka https://console.cron-job.org → **Loker Bot** → **EDIT** → tab **ADVANCED**.
3. Di header `Authorization`, ganti value menjadi `Bearer <token-baru>` → **SAVE**.
4. Tunggu 10 menit, lalu cek tab **History** di cron-job.org: harus **204**.

> Tips: pasang pengingat di kalender HP Anda untuk 15 Desember 2026.

---

## 2. Bagian-bagian bot (semua gratis)

| Layanan | Fungsi | Alamat |
|---|---|---|
| **GitHub** (akun `fitodanendra`) | Menyimpan kode + menjalankan pencarian lowongan | https://github.com/fitodanendra/loker-bot |
| **cron-job.org** | "Alarm" yang menjalankan bot tiap 10 menit | https://console.cron-job.org |
| **Cloudflare** | Membalas perintah Telegram secara instan + menyimpan catatan bot | https://dash.cloudflare.com → Workers & Pages → `loker-bot` |
| **Telegram** (@BotFather) | Bot `@pencarijob_bot` | Chat dengan @BotFather |

Alur singkat: cron-job.org → GitHub Actions mencari lowongan → kirim ke Telegram.
Perintah yang Anda ketik di Telegram → dijawab Cloudflare.

---

## 3. Penggunaan sehari-hari (dari Telegram)

| Perintah | Fungsi |
|---|---|
| `/kategori` | Lihat kategori aktif |
| `/pilih fullstack` | Hanya kategori ini |
| `/tambah motion` / `/hapus video` | Nyalakan / matikan kategori |
| `/semua` | Nyalakan semua kategori |
| `/baru graphic designer` | Buat kategori sendiri (judul harus mengandung semua kata) |
| `/buang graphicdesigner` | Hapus kategori buatan sendiri |
| `/lokasi` | Lihat lokasi aktif |
| `/tambahlokasi bandung` / `/hapuslokasi bogor` | Tambah / hapus lokasi |
| `/semualokasi` | Seluruh Indonesia |

Tips kata kunci: kata pendek (`3d`, `illustrator`) = hasil lebih banyak; kata panjang
(`3d artist`) = lebih sedikit tapi lebih tepat.

---

## 4. Kalau ada masalah

### A. Tidak ada notifikasi lowongan sama sekali (lebih dari setengah hari)
Hari libur/malam memang sepi — tapi kalau berlangsung lama:

1. **Cek cron-job.org** → Loker Bot → **History**:
   - `204` = normal, lanjut ke langkah 2.
   - `401 Unauthorized` = token GitHub kedaluwarsa/salah → ikuti **Bagian 1**.
   - `404 Not Found` = token tidak punya akses repo, atau URL berubah. Cek token punya akses
     ke `loker-bot` dengan izin **Actions: Read and write**, dan URL persis:
     `https://api.github.com/repos/fitodanendra/loker-bot/actions/workflows/loker.yml/dispatches`
   - Cronjob **nonaktif** (abu-abu) = cron-job.org bisa mematikan job yang gagal berkali-kali.
     Perbaiki penyebabnya, lalu nyalakan lagi (**Enable job**).
2. **Cek GitHub** → https://github.com/fitodanendra/loker-bot/actions → **Cek Lowongan**:
   - ✅ hijau = bot jalan normal, memang belum ada lowongan baru yang cocok.
   - ❌ merah = klik run-nya → klik langkah yang merah → baca pesan `ERROR`.
   - Ada banner "workflows disabled" = klik **Enable workflow**.

### B. Lowongan dari satu situs berhenti muncul
Di log GitHub (langkah "Check new jobs and notify Telegram") akan ada baris seperti
`WARNING JobStreet search for 'video editor' failed: ...`.
Artinya situs itu mengubah sistemnya. Situs lain tetap jalan. Perbaikan butuh perubahan kode —
lihat **Bagian 6**.

### C. Bot tidak membalas perintah Telegram
1. Buka GitHub → **Actions** → **Daftarkan Ulang Telegram** → **Run workflow**.
   Tunggu ±30 detik; harus hijau ✅. Coba kirim `/kategori` lagi.
2. Kalau run itu merah: token Telegram di Cloudflare kemungkinan salah → lihat **Bagian 5**.

### D. Lowongan yang sama terkirim berulang
Biasanya karena bot gagal menyimpan catatan ke Cloudflare. Cek log GitHub: baris
`ERROR State PUT failed`. Kalau Cloudflare sedang gangguan, biasanya pulih sendiri.

### E. Mematikan bot sementara
cron-job.org → Loker Bot → matikan **Enable job**. Nyalakan lagi kapan saja.

---

## 5. Mengganti token Telegram (disarankan sekali, lalu bila bocor)

1. Telegram → **@BotFather** → kirim `/revoke` → pilih `@pencarijob_bot` → salin token baru.
2. **GitHub**: repo → **Settings** → **Secrets and variables** → **Actions** →
   `TELEGRAM_BOT_TOKEN` → ✏️ **Update** → tempel token baru.
3. **Cloudflare**: dash.cloudflare.com → **Workers & Pages** → `loker-bot` → **Settings** →
   **Variables and Secrets** → `TELEGRAM_BOT_TOKEN` → **Edit** → tempel token baru → **Deploy/Save**.
4. **GitHub** → **Actions** → **Daftarkan Ulang Telegram** → **Run workflow** (wajib!).
5. Kirim `/kategori` ke bot untuk memastikan.

Jangan pernah menempel token di chat, screenshot, atau file di repo (repo ini **public**).

---

## 6. Mengubah pengaturan lanjutan / kode

**Tanpa koding** — edit `config.json` langsung di GitHub (klik file → ikon ✏️ → **Commit changes**):
- `max_age_hours`: umur maksimal lowongan (default 48 jam).
- `include_remote`: `true`/`false` untuk lowongan remote.
- `searches`: kategori bawaan (nama, kata kunci, filter judul).
- `locations`: lokasi default (dipakai sampai Anda mengubahnya lewat `/tambahlokasi` dll).

Kalau salah ketik dan bot error, buka file → **History** → kembalikan versi sebelumnya.

**Butuh perubahan kode** (mis. situs berubah, fitur baru): repo ini public, jadi Anda bisa
memberikan link repo + isi `README.md` + pesan error dari log ke asisten AI mana pun
atau ke teman programmer. Semua kode punya tes otomatis (`python -m unittest` dan
`cd worker && node --test`) yang dijalankan GitHub setiap kali bot jalan — kalau perubahan
merusak sesuatu, run-nya akan merah dan bot tidak mengirim apa pun yang salah.

---

## 7. Batas layanan gratis (untuk ketenangan)

| Layanan | Batas gratis | Pemakaian bot |
|---|---|---|
| GitHub Actions (repo public) | Tidak terbatas | ±144 run/hari |
| Cloudflare Workers | 100.000 permintaan/hari | puluhan/hari |
| Cloudflare KV (tulis) | 1.000/hari | ≤ ±150/hari |
| cron-job.org | Gratis | 144 panggilan/hari |

Selama repo tetap **public**, semuanya gratis. Kalau repo diubah ke private, kuota GitHub
hanya 2.000 menit/bulan → ubah jadwal cron-job.org ke **30 menit** agar tidak habis.
