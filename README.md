# Loker Bot 🔔

> 🛠 **Perawatan & kalau ada masalah:** baca [PANDUAN.md](PANDUAN.md).

Bot Telegram yang mengecek lowongan baru setiap 10 menit dari **JobStreet, Kalibrr, dan LinkedIn**,
lalu mengirim notifikasi + tombol link apply ke Telegram Anda.

## Cara kerja
```
cron-job.org ──tiap 10 menit──▶ GitHub Actions (python -m loker_bot.main)
                                   │  cari lowongan JobStreet / Kalibrr / LinkedIn
                                   │  kirim notifikasi ke Telegram
                                   ▼
Telegram ──perintah /pilih dll──▶ Cloudflare Worker (worker/) ──▶ Workers KV
                                   (balas instan)                 prefs, seen, config
```
1. **Cloudflare Worker** menerima perintah Telegram lewat webhook dan langsung membalas.
   Pilihan kategori/lokasi disimpan di Workers KV.
2. **GitHub Actions** (dipicu cron-job.org tiap 10 menit) membaca pilihan + daftar lowongan yang
   sudah dikirim dari Worker, mencari lowongan baru, mengirimnya ke Telegram, lalu menyimpan
   daftar terbaru ke Worker. Tidak ada commit otomatis.

## Setup (sekali saja, ±10 menit)

### 1. Buat bot Telegram
1. Buka Telegram, cari **@BotFather**, kirim `/newbot`.
2. Beri nama, mis. `Loker Fito` dan username, mis. `loker_fito_bot`.
3. Salin **token** yang diberikan (bentuknya `123456789:ABC...`).
4. Buka bot Anda, tekan **Start**, lalu kirim pesan `halo`.

### 2. Dapatkan chat ID
```bash
cd ~/Projects/loker-bot
TELEGRAM_BOT_TOKEN="token-anda" python3 -m loker_bot.get_chat_id
```

### 3. Coba di laptop
```bash
python3 -m loker_bot.main --dry-run          # hanya tampilkan di terminal
TELEGRAM_BOT_TOKEN="..." TELEGRAM_CHAT_ID="..." python3 -m loker_bot.main   # kirim ke Telegram
```

### 4. Jalankan otomatis di GitHub (gratis)
1. Buat repo baru di github.com (boleh **Private**).
2. Upload folder ini:
   ```bash
   git init && git add . && git commit -m "feat: loker bot"
   git branch -M main
   git remote add origin https://github.com/USERNAME/loker-bot.git
   git push -u origin main
   ```
3. Di repo: **Settings → Secrets and variables → Actions → New repository secret**, tambahkan:
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_CHAT_ID`
4. Tab **Actions** → pilih **Cek Lowongan** → **Run workflow** untuk tes pertama.

Setelah itu bot jalan sendiri tiap 30 menit, walaupun laptop mati.

## Memilih kategori dari Telegram
Kirim perintah ini ke bot (juga muncul di tombol menu `/`):

| Perintah | Fungsi |
|---|---|
| `/kategori` | Lihat kategori yang aktif |
| `/pilih fullstack` | Hanya cari fullstack (boleh beberapa: `/pilih video motion`) |
| `/tambah motion` | Aktifkan kategori tambahan |
| `/hapus video` | Matikan satu kategori |
| `/semua` | Aktifkan semua kategori |
| `/baru graphic designer` | Buat kategori baru (judul harus mengandung semua kata) |
| `/buang graphicdesigner` | Hapus kategori buatan sendiri (maks. 10 kategori buatan) |

| `/lokasi` | Lihat lokasi aktif |
| `/tambahlokasi bandung` | Tambah lokasi (boleh dua kata: `/tambahlokasi tangerang selatan`) |
| `/hapuslokasi bogor` | Hapus lokasi |
| `/semualokasi` | Cari di seluruh Indonesia |

Perintah dibalas **instan** oleh Cloudflare Worker. Lowongan untuk pilihan baru muncul di pengecekan berikutnya (maks. ±10 menit).
Hanya chat ID pemilik yang bisa mengubah pengaturan.

## Mengubah kata kunci / lokasi
Edit `config.json`:

| Field | Arti |
|---|---|
| `searches[].name` | Nama kategori untuk perintah Telegram (tanpa spasi) |
| `searches[].query` | Kata kunci pencarian |
| `searches[].title_must_include` | Judul harus mengandung salah satu kata ini (hapus field ini untuk menerima semua hasil) |
| `locations` | Lokasi yang diterima (kosongkan `[]` untuk seluruh Indonesia) |
| `include_remote` | Terima lowongan remote dari lokasi mana pun |
| `max_age_hours` | Abaikan lowongan yang lebih lama dari ini |

## Catatan
- Notifikasi tidak instan: jeda maksimal ±10 menit (+ delay GitHub beberapa menit).
- Maksimal 25 notifikasi per putaran; sisanya dikirim di putaran berikutnya.
- Glints & Instagram belum didukung (Glints memblokir akses otomatis, Instagram tidak punya API publik).
- Kalau suatu situs mengubah tampilannya, sumber itu akan gagal sementara tanpa menghentikan sumber lain
  (lihat log di tab Actions).

## Worker (Cloudflare)
```bash
cd worker
npx wrangler deploy                      # deploy perubahan
npx wrangler secret put TELEGRAM_BOT_TOKEN  # ganti token Telegram
npx wrangler tail                        # lihat log langsung
```
Secrets Worker: `TELEGRAM_BOT_TOKEN`, `OWNER_CHAT_ID`, `WEBHOOK_SECRET`, `STATE_SECRET`.
Secrets GitHub: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `STATE_URL`, `STATE_SECRET`.
Setelah deploy pertama atau ganti token: `curl -X POST -H "Authorization: Bearer <STATE_SECRET>" <STATE_URL>/setup`
untuk mendaftarkan webhook dan menu perintah.

## Tes
```bash
python3 -m unittest
cd worker && node --test
```
