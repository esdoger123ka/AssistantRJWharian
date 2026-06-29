# -*- coding: utf-8 -*-
# =====================================================================
#  BOT ABSENSI MORNING BRIEFING - RJW
#  Fungsi:
#    /start, /bantuan         info
#    /daftar <NIK>            kaitkan akun Telegram dgn NIK (sekali saja)
#    /hadir                   mulai check-in (lalu kirim SELFIE)
#    kirim foto               -> tercatat hadir + simpan ke log
#    /rekap                   admin: laporan manual kapan saja
#    otomatis JAM_LAPORAN     kirim grid foto + daftar hadir/alpa ke grup
# =====================================================================
import datetime as dt
from zoneinfo import ZoneInfo

from telegram import Update, InputFile
from telegram.ext import (
    Application, CommandHandler, MessageHandler, ContextTypes, filters,
)

import config
import sheets
import gambar

# state ringan per-user: siapa yang sedang menunggu kirim selfie
_menunggu_selfie = {}   # telegram_id -> True
# kode harian (opsional) disimpan in-memory; admin set via /kode
_kode_harian = {"nilai": None, "tanggal": None}


def _wib():
    return dt.datetime.now(ZoneInfo(config.TIMEZONE))


def _dalam_jendela():
    n = _wib()
    h, m = map(int, config.JAM_BUKA.split(":"))
    buka = n.replace(hour=h, minute=m, second=0, microsecond=0)
    h, m = map(int, config.JAM_TUTUP.split(":"))
    tutup = n.replace(hour=h, minute=m, second=0, microsecond=0)
    return buka <= n <= tutup


def _is_admin(update):
    return str(update.effective_user.id) == str(config.ADMIN_CHAT_ID)


# ---------------------------------------------------------------------
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Bot Absensi Morning Briefing RJW.\n\n"
        "Langkah pertama (sekali saja): daftarkan diri Anda\n"
        "   /daftar <NIK Anda>\n"
        "   contoh: /daftar 20940711\n\n"
        "Setiap pagi saat briefing:\n"
        "   1. ketik /hadir\n"
        "   2. kirim SELFIE Anda\n\n"
        "Ketik /bantuan untuk info lengkap."
    )


async def bantuan(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    txt = (
        "PANDUAN\n"
        "/daftar <NIK>  – kaitkan akun Telegram dengan NIK (sekali saja)\n"
        "/hadir         – mulai check-in, lalu kirim selfie\n"
    )
    if config.PAKAI_KODE_HARIAN:
        txt += "                 (sertakan kode: /hadir <kode hari ini>)\n"
    if _is_admin(update):
        txt += (
            "\nADMIN:\n"
            "/rekap   – kirim laporan sekarang juga\n"
        )
        if config.PAKAI_KODE_HARIAN:
            txt += "/kode <kode> – set kode harian yang diumumkan saat briefing\n"
    await update.message.reply_text(txt)


async def daftar(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        await update.message.reply_text("Format: /daftar <NIK>\ncontoh: /daftar 20940711")
        return
    nik = ctx.args[0].strip()
    tid = update.effective_user.id
    try:
        ok, pesan = sheets.daftar_teknisi(tid, nik, update.effective_user.full_name)
    except Exception as e:
        await update.message.reply_text(
            "Maaf, sistem sedang gangguan saat menyimpan data. "
            "Admin sudah diberi tahu. Coba lagi beberapa saat.")
        await _japri_admin(ctx, f"Error /daftar (user {tid}, nik {nik}): {e}")
        return
    await update.message.reply_text(pesan)


async def kode(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _is_admin(update):
        return
    if not ctx.args:
        await update.message.reply_text("Format: /kode <kode hari ini>")
        return
    _kode_harian["nilai"] = ctx.args[0].strip().upper()
    _kode_harian["tanggal"] = _wib().strftime("%Y-%m-%d")
    await update.message.reply_text(f"Kode harian di-set: {_kode_harian['nilai']}")


async def hadir(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    tid = update.effective_user.id

    # harus terdaftar
    try:
        reg = sheets.ambil_registrasi()
    except Exception as e:
        await update.message.reply_text(
            "Maaf, sistem sedang gangguan. Admin sudah diberi tahu. Coba lagi sebentar.")
        await _japri_admin(ctx, f"Error baca registrasi (user {tid}): {e}")
        return
    if str(tid) not in reg:
        await update.message.reply_text(
            "Anda belum terdaftar. Ketik dulu:\n   /daftar <NIK Anda>")
        return

    # jendela waktu
    if not _dalam_jendela():
        await update.message.reply_text(
            f"Check-in hanya dibuka {config.JAM_BUKA}–{config.JAM_TUTUP} WIB.")
        return

    # sudah check-in?
    if sheets.sudah_checkin(tid):
        await update.message.reply_text("Anda sudah tercatat hadir hari ini. ✓")
        return

    # kode harian opsional
    if config.PAKAI_KODE_HARIAN:
        hari_ini = _wib().strftime("%Y-%m-%d")
        if _kode_harian["tanggal"] != hari_ini or not _kode_harian["nilai"]:
            await update.message.reply_text("Kode harian belum di-set admin. Hubungi koordinator.")
            return
        diberikan = (ctx.args[0].strip().upper() if ctx.args else "")
        if diberikan != _kode_harian["nilai"]:
            await update.message.reply_text("Kode salah. Format: /hadir <kode hari ini>")
            return

    _menunggu_selfie[tid] = True
    await update.message.reply_text("Silakan kirim SELFIE Anda sekarang untuk menyelesaikan check-in. 📸")


async def terima_foto(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    tid = update.effective_user.id
    if not _menunggu_selfie.get(tid):
        # foto tanpa /hadir lebih dulu
        await update.message.reply_text("Ketik /hadir dulu sebelum mengirim selfie.")
        return

    try:
        reg = sheets.ambil_registrasi()
        info = reg.get(str(tid))
        if not info:
            await update.message.reply_text("Anda belum terdaftar. Ketik /daftar <NIK>.")
            return
        if sheets.sudah_checkin(tid):
            _menunggu_selfie.pop(tid, None)
            await update.message.reply_text("Anda sudah tercatat hadir hari ini. ✓")
            return

        # ambil foto resolusi terbesar -> file_id (disimpan, bukan file mentah)
        file_id = update.message.photo[-1].file_id
        sheets.catat_kehadiran(tid, info["nik"], info["nama"], file_id)
        _menunggu_selfie.pop(tid, None)
        await update.message.reply_text(
            f"✓ Tercatat hadir: {info['nama']}\nTerima kasih, selamat briefing.")
    except Exception as e:
        await update.message.reply_text(f"Gagal menyimpan: {e}")
        await _japri_admin(ctx, f"Error simpan kehadiran: {e}")


# ---------------------------------------------------------------------
#  LAPORAN
# ---------------------------------------------------------------------
async def _susun_dan_kirim_laporan(ctx: ContextTypes.DEFAULT_TYPE, chat_id):
    tanggal_str = _wib().strftime("%Y-%m-%d")
    tgl_hari = _wib().day

    wajib = sheets.wajib_briefing_hari_ini(tgl_hari)         # [{nik,nama}]
    hadir = sheets.log_hari_ini(tanggal_str)                 # [{nik,nama,jam,file_id}]
    hadir_nik = {h["nik"] for h in hadir}

    # unduh foto untuk grid
    foto_list = []
    for h in hadir:
        img_bytes = None
        try:
            f = await ctx.bot.get_file(h["file_id"])
            ba = await f.download_as_bytearray()
            img_bytes = bytes(ba)
        except Exception:
            img_bytes = None
        foto_list.append({"nama": h["nama"], "jam": h["jam"], "img_bytes": img_bytes})

    judul = f"Kehadiran Briefing — {_wib().strftime('%d %b %Y')}"
    png = gambar.buat_grid_foto(
        [f for f in foto_list if f["img_bytes"]], judul)

    # daftar alpa = wajib tapi tidak ada di hadir
    alpa = [w for w in wajib if w["nik"] not in hadir_nik]

    # caption ringkas
    cap = (
        f"*Laporan Kehadiran Morning Briefing*\n"
        f"{_wib().strftime('%A, %d %B %Y')}\n\n"
        f"Wajib hadir : {len(wajib)} orang\n"
        f"Hadir       : {len(wajib) - len(alpa)} orang\n"
        f"Belum hadir : {len(alpa)} orang\n"
    )

    await ctx.bot.send_photo(chat_id=chat_id, photo=InputFile(png, filename="kehadiran.png"),
                             caption=cap, parse_mode="Markdown")

    # teks daftar nama (hadir & belum) — dipisah agar tidak kepanjangan di caption
    def _fmt(lst):
        return "\n".join(f"• {x['nama']} ({x['nik']})" for x in lst) or "—"

    hadir_wajib = [w for w in wajib if w["nik"] in hadir_nik]
    teks = (
        f"✅ HADIR ({len(hadir_wajib)}):\n{_fmt(hadir_wajib)}\n\n"
        f"❌ BELUM HADIR ({len(alpa)}):\n{_fmt(alpa)}"
    )
    # Telegram batas 4096 char; pecah bila perlu
    for bagian in _pecah(teks, 3900):
        await ctx.bot.send_message(chat_id=chat_id, text=bagian)


def _pecah(teks, n):
    out, buf = [], ""
    for baris in teks.split("\n"):
        if len(buf) + len(baris) + 1 > n:
            out.append(buf)
            buf = ""
        buf += baris + "\n"
    if buf:
        out.append(buf)
    return out


async def rekap(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _is_admin(update):
        await update.message.reply_text("Perintah ini khusus admin.")
        return
    await update.message.reply_text("Menyusun laporan…")
    try:
        await _susun_dan_kirim_laporan(ctx, config.GROUP_CHAT_ID)
    except Exception as e:
        await update.message.reply_text(f"Gagal: {e}")
        await _japri_admin(ctx, f"Error /rekap: {e}")


async def laporan_terjadwal(ctx: ContextTypes.DEFAULT_TYPE):
    try:
        await _susun_dan_kirim_laporan(ctx, config.GROUP_CHAT_ID)
    except Exception as e:
        await _japri_admin(ctx, f"Error laporan terjadwal: {e}")


async def _japri_admin(ctx, pesan):
    if config.ADMIN_CHAT_ID:
        try:
            await ctx.bot.send_message(chat_id=config.ADMIN_CHAT_ID, text="⚠️ " + pesan[:3900])
        except Exception:
            pass


# ---------------------------------------------------------------------
def main():
    kurang = config.validasi()
    if kurang:
        raise SystemExit("Variable wajib belum di-set: " + ", ".join(kurang))

    # cek kredensial lebih awal -> error jelas di Deploy Logs, bukan saat user pakai
    try:
        sheets._muat_creds_dict()
        print("GOOGLE_CREDS_JSON terbaca OK.")
    except Exception as e:
        raise SystemExit(f"GOOGLE_CREDS_JSON bermasalah: {e}")

    app = Application.builder().token(config.BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("bantuan", bantuan))
    app.add_handler(CommandHandler("help", bantuan))
    app.add_handler(CommandHandler("daftar", daftar))
    app.add_handler(CommandHandler("hadir", hadir))
    app.add_handler(CommandHandler("rekap", rekap))
    app.add_handler(CommandHandler("kode", kode))
    app.add_handler(MessageHandler(filters.PHOTO, terima_foto))

    # jadwalkan laporan harian pada JAM_LAPORAN WIB
    jam, menit = map(int, config.JAM_LAPORAN.split(":"))
    waktu = dt.time(hour=jam, minute=menit, tzinfo=ZoneInfo(config.TIMEZONE))
    app.job_queue.run_daily(laporan_terjadwal, time=waktu, name="laporan_harian")

    print("Bot absensi RJW berjalan…")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
