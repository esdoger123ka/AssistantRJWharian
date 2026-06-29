# Bot Absensi Morning Briefing — RJW

Bot Telegram terpisah untuk mendata kehadiran teknisi di morning briefing harian.
Teknisi check-in dengan **selfie**; tiap pagi pada jam yang ditentukan bot mengirim
**grid foto + daftar hadir/belum hadir** ke grup, berdasarkan **jadwal piket**
(sel kosong = wajib briefing).

Dibuat sebagai service mandiri di **Railway** — tidak menyentuh bot DASHBOARD Anda
yang sudah ada.

---

## Cara kerja singkat

1. Teknisi daftar sekali: `/daftar <NIK>` → bot mengaitkan akun Telegram ↔ NIK.
2. Saat briefing: `/hadir` → kirim selfie → tercatat.
3. Pada `JAM_LAPORAN` (default 08:30 WIB) bot otomatis kirim laporan ke grup.
4. "Wajib hadir" dihitung dari tab JADWAL: **sel kosong pada tanggal hari ini = wajib**.
   Nilai apa pun (S/M/L/BANTEK/CT/C/SAKIT/IZIN/IJIN) = tidak wajib.

---

## Yang perlu Anda siapkan (sekali)

### 1. Google Sheet master
Buat satu Google Sheet, catat **ID**-nya (potongan di URL antara `/d/` dan `/edit`).
Buat 1 tab bernama **JADWAL**. Import isi `JADWAL_untuk_import.csv` ke tab itu
(File ▸ Import ▸ Upload ▸ Replace current sheet). Dua tab lain (REGISTRASI,
LOG_HADIR) dibuat otomatis oleh bot saat pertama kali dipakai.

> Catatan: NIK IQBAL FAUZI sudah dikoreksi jadi **18990146** di CSV ini agar tidak
> bentrok dengan RISMAN FAUZI (18940108).

### 2. Service account Google
- Di Google Cloud Console: buat Service Account, aktifkan **Google Sheets API** & **Drive API**, unduh **credentials.json**.
- **Bagikan** Google Sheet master ke alamat email service account (……@……iam.gserviceaccount.com) sebagai **Editor**.

### 3. Bot Telegram
- Buat bot via **@BotFather**, simpan token.
- Masukkan bot ke grup tujuan, jadikan admin (agar bisa kirim foto).
- Dapatkan **chat id grup** (mis. lewat @userinfobot atau cek update). Biasanya diawali `-100`.

### 4. Update jadwal tiap periode
Jadwal ini berbasis tanggal 16–15. Saat ganti periode, import CSV/Excel periode
baru ke tab **JADWAL** (Replace current sheet). Struktur kolom harus sama:
baris 1 = NIK,NAMA,16,17,… ; baris 2 = kode hari ; baris 3+ = data.

---

## Deploy ke Railway

1. Push folder ini ke sebuah repo GitHub (pastikan `credentials.json` **tidak** ikut — sudah di `.gitignore`).
2. Railway ▸ New Project ▸ Deploy from GitHub ▸ pilih repo.
3. Railway ▸ **Variables**, isi:

| Variable | Isi |
|---|---|
| `BOT_TOKEN` | token dari BotFather |
| `GROUP_CHAT_ID` | chat id grup, mis. `-1002442951689` |
| `ADMIN_CHAT_ID` | chat id Anda pribadi |
| `SHEET_ID` | ID Google Sheet master |
| `GOOGLE_CREDS_JSON` | **seluruh isi** credentials.json (copy-paste apa adanya) |
| `JAM_LAPORAN` | `08:30` (opsional) |
| `JAM_BUKA` / `JAM_TUTUP` | jendela check-in, default `05:30` / `08:30` |
| `PAKAI_KODE_HARIAN` | `1` untuk aktifkan kode harian, `0` mati (default) |

4. Railway akan menjalankan `python bot.py` (lihat `Procfile`). Cek **Deploy Logs**;
   harus muncul `Bot absensi RJW berjalan…`.

---

## Perintah

**Teknisi**
- `/daftar <NIK>` — sekali saja
- `/hadir` — lalu kirim selfie

**Admin** (hanya `ADMIN_CHAT_ID`)
- `/rekap` — kirim laporan ke grup kapan saja
- `/kode <kode>` — set kode harian (kalau `PAKAI_KODE_HARIAN=1`)

---

## Batasan jujur (baca ini)

- **Foto disimpan sebagai `file_id` Telegram**, bukan diunduh ke Drive. Hemat & cepat,
  tapi `file_id` hanya berlaku selama bot/akun bot sama. Untuk arsip jangka panjang,
  perlu modifikasi agar unduh ke Drive (bisa ditambahkan kalau dibutuhkan).
- **Anti titip-absen bertumpu pada selfie + review manusia.** Bot tidak mencocokkan
  wajah otomatis. Grid foto memudahkan Anda/koordinator memindai 28 wajah dalam
  beberapa detik. Ini pilihan desain yang sudah disepakati: lebih murah, lebih akurat
  untuk jumlah orang yang Anda kenal, tanpa beban database biometrik.
- **Kualitas laporan = kualitas pengisian jadwal.** Sel yang lupa diisi akan dianggap
  "wajib briefing" lalu muncul sebagai "belum hadir". Pastikan jadwal terisi lengkap.
- **Selfie real-time vs galeri**: Telegram tidak menjamin foto berasal dari kamera
  langsung. Pertahanan tetap pada mata peninjau.
- **UU PDP**: data wajah = data biometrik. Pastikan teknisi diberi tahu & setuju,
  dan ini sesuai kebijakan internal Telkom. Itu di luar lingkup kode.
