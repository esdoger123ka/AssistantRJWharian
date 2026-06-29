# -*- coding: utf-8 -*-
# =====================================================================
#  KONFIGURASI BOT ABSENSI BRIEFING RJW
# ---------------------------------------------------------------------
#  PENTING: JANGAN menaruh token / kredensial langsung di file ini.
#  Semua nilai sensitif diambil dari Environment Variables Railway.
#  (Railway > project > Variables). Lihat README.md langkah deploy.
# =====================================================================
import os

# --- Wajib diisi di Railway Variables ---
BOT_TOKEN        = os.environ.get("BOT_TOKEN", "")          # dari @BotFather
GROUP_CHAT_ID    = os.environ.get("GROUP_CHAT_ID", "")      # grup tujuan laporan, mis. -1002442951689
ADMIN_CHAT_ID    = os.environ.get("ADMIN_CHAT_ID", "")      # chat id admin (japri error)
SHEET_ID         = os.environ.get("SHEET_ID", "")           # ID Google Sheet master (jadwal + registrasi + log)

# Service account JSON: tempel SELURUH isi credentials.json ke 1 variable ini.
GOOGLE_CREDS_JSON = os.environ.get("GOOGLE_CREDS_JSON", "")

# --- Nama-nama worksheet di dalam Sheet master ---
WS_JADWAL   = os.environ.get("WS_JADWAL",   "JADWAL")    # hasil import jadwal piket
WS_DAFTAR   = os.environ.get("WS_DAFTAR",   "REGISTRASI")# telegram_id <-> NIK <-> nama
WS_LOG      = os.environ.get("WS_LOG",      "LOG_HADIR") # catatan check-in harian

# --- Jam laporan otomatis (WIB) ---
JAM_LAPORAN = os.environ.get("JAM_LAPORAN", "08:30")     # format HH:MM
TIMEZONE    = os.environ.get("TIMEZONE", "Asia/Jakarta")

# --- Jendela check-in (WIB). Di luar jam ini /hadir ditolak. ---
JAM_BUKA    = os.environ.get("JAM_BUKA", "05:30")
JAM_TUTUP   = os.environ.get("JAM_TUTUP", "08:30")

# --- Kode harian opsional (anti titip-absen lapis kedua) ---
# Jika "1": teknisi harus sertakan kode yang Anda umumkan saat briefing.
PAKAI_KODE_HARIAN = os.environ.get("PAKAI_KODE_HARIAN", "0") == "1"


def validasi():
    """Pastikan variabel wajib terisi; kembalikan daftar yang kurang."""
    wajib = {
        "BOT_TOKEN": BOT_TOKEN,
        "GROUP_CHAT_ID": GROUP_CHAT_ID,
        "SHEET_ID": SHEET_ID,
        "GOOGLE_CREDS_JSON": GOOGLE_CREDS_JSON,
    }
    return [k for k, v in wajib.items() if not v]
