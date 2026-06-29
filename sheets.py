# -*- coding: utf-8 -*-
# =====================================================================
#  LAPISAN GOOGLE SHEETS
#  - autentikasi service account (pola didaur ulang dari dashboard.py)
#  - baca jadwal piket -> tentukan siapa WAJIB briefing hari ini
#  - registrasi telegram_id <-> NIK
#  - tulis & baca log kehadiran harian
# =====================================================================
import json
import datetime as dt
from zoneinfo import ZoneInfo

import gspread
from google.oauth2.service_account import Credentials

import config

_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]
_gc = None


def _client():
    global _gc
    if _gc is None:
        info = json.loads(config.GOOGLE_CREDS_JSON)
        creds = Credentials.from_service_account_info(info, scopes=_SCOPES)
        _gc = gspread.authorize(creds)
    return _gc


def _wb():
    return _client().open_by_key(config.SHEET_ID)


def _ws(nama, buat_jika_kosong_header=None):
    wb = _wb()
    try:
        return wb.worksheet(nama)
    except gspread.WorksheetNotFound:
        ws = wb.add_worksheet(title=nama, rows=200, cols=20)
        if buat_jika_kosong_header:
            ws.append_row(buat_jika_kosong_header)
        return ws


def now_wib():
    return dt.datetime.now(ZoneInfo(config.TIMEZONE))


# ---------------------------------------------------------------------
#  JADWAL  ->  siapa wajib briefing hari ini
# ---------------------------------------------------------------------
# Format sheet JADWAL (hasil import dari Excel):
#   Baris 1 : NIK | NAMA | 16 | 17 | 18 | ... (angka tanggal)
#   Baris 2 : (kosong) | (kosong) | S | R | K | ... (kode hari, diabaikan)
#   Baris 3+: data per teknisi
#
# ATURAN (dikonfirmasi user):
#   sel KOSONG  -> WAJIB briefing (masuk shift pagi)
#   sel TERISI apa pun (S/s/M/L/BANTEK/CT/C/SAKIT/IZIN/IJIN/...) -> TIDAK wajib
def baca_jadwal():
    """Kembalikan (header_tanggal, list baris).
    Tiap baris = dict {nik, nama, sel: {tanggal:int -> nilai:str}}.
    """
    ws = _ws(config.WS_JADWAL)
    rows = ws.get_all_values()
    if len(rows) < 3:
        return [], []

    header = rows[0]
    # kolom 0,1 = NIK,NAMA. kolom 2.. = tanggal
    tanggal_kol = []
    for idx in range(2, len(header)):
        try:
            tanggal_kol.append((idx, int(str(header[idx]).strip())))
        except (ValueError, TypeError):
            tanggal_kol.append((idx, None))

    teknisi = []
    for r in rows[2:]:  # lewati baris kode hari
        if len(r) < 2:
            continue
        nik = str(r[0]).strip()
        nama = str(r[1]).strip()
        if not nik and not nama:
            continue
        sel = {}
        for idx, tgl in tanggal_kol:
            if tgl is None:
                continue
            val = r[idx].strip() if idx < len(r) and r[idx] else ""
            sel[tgl] = val
        teknisi.append({"nik": nik, "nama": nama, "sel": sel})
    return header, teknisi


def wajib_briefing_hari_ini(tanggal_hari=None):
    """Daftar teknisi yang WAJIB briefing untuk tanggal (default: hari ini WIB).
    Mengembalikan list dict {nik, nama}.
    """
    if tanggal_hari is None:
        tanggal_hari = now_wib().day
    _, teknisi = baca_jadwal()
    hasil = []
    for t in teknisi:
        val = t["sel"].get(tanggal_hari, None)
        if val is None:
            # tanggal ini tidak ada di jadwal (mis. jadwal periode lain) -> lewati
            continue
        if val == "":          # KOSONG -> wajib
            hasil.append({"nik": t["nik"], "nama": t["nama"]})
    return hasil


# ---------------------------------------------------------------------
#  REGISTRASI  telegram_id <-> NIK <-> nama
# ---------------------------------------------------------------------
_HEADER_DAFTAR = ["telegram_id", "nik", "nama", "didaftarkan_pada"]


def ambil_registrasi():
    ws = _ws(config.WS_DAFTAR, _HEADER_DAFTAR)
    rows = ws.get_all_records()
    by_tid = {}
    for r in rows:
        tid = str(r.get("telegram_id", "")).strip()
        if tid:
            by_tid[tid] = {"nik": str(r.get("nik", "")).strip(),
                           "nama": str(r.get("nama", "")).strip()}
    return by_tid


def daftar_teknisi(telegram_id, nik, nama):
    """Tambah/replace registrasi. Kembalikan (ok, pesan)."""
    ws = _ws(config.WS_DAFTAR, _HEADER_DAFTAR)
    rows = ws.get_all_values()
    tid = str(telegram_id)
    # cek apakah NIK ini terdaftar di jadwal
    _, teknisi = baca_jadwal()
    cocok = next((t for t in teknisi if t["nik"] == str(nik).strip()), None)
    if not cocok:
        return False, f"NIK {nik} tidak ditemukan di jadwal. Periksa kembali."
    nama_resmi = cocok["nama"]
    # apakah telegram_id sudah terdaftar -> update barisnya
    for i, r in enumerate(rows):
        if i == 0:
            continue
        if len(r) >= 1 and str(r[0]).strip() == tid:
            ws.update(f"A{i+1}:D{i+1}",
                      [[tid, str(nik).strip(), nama_resmi, now_wib().strftime("%Y-%m-%d %H:%M")]])
            return True, f"Registrasi diperbarui: {nama_resmi} (NIK {nik})."
    ws.append_row([tid, str(nik).strip(), nama_resmi, now_wib().strftime("%Y-%m-%d %H:%M")])
    return True, f"Terdaftar: {nama_resmi} (NIK {nik})."


# ---------------------------------------------------------------------
#  LOG KEHADIRAN HARIAN
# ---------------------------------------------------------------------
_HEADER_LOG = ["tanggal", "jam", "telegram_id", "nik", "nama", "file_id"]


def sudah_checkin(telegram_id, tanggal_str=None):
    if tanggal_str is None:
        tanggal_str = now_wib().strftime("%Y-%m-%d")
    ws = _ws(config.WS_LOG, _HEADER_LOG)
    for r in ws.get_all_records():
        if (str(r.get("telegram_id", "")).strip() == str(telegram_id)
                and str(r.get("tanggal", "")).strip() == tanggal_str):
            return True
    return False


def catat_kehadiran(telegram_id, nik, nama, file_id):
    n = now_wib()
    ws = _ws(config.WS_LOG, _HEADER_LOG)
    ws.append_row([n.strftime("%Y-%m-%d"), n.strftime("%H:%M:%S"),
                   str(telegram_id), str(nik), nama, file_id])


def log_hari_ini(tanggal_str=None):
    if tanggal_str is None:
        tanggal_str = now_wib().strftime("%Y-%m-%d")
    ws = _ws(config.WS_LOG, _HEADER_LOG)
    hadir = []
    for r in ws.get_all_records():
        if str(r.get("tanggal", "")).strip() == tanggal_str:
            hadir.append({"nik": str(r.get("nik", "")).strip(),
                          "nama": str(r.get("nama", "")).strip(),
                          "jam": str(r.get("jam", "")).strip(),
                          "file_id": str(r.get("file_id", "")).strip()})
    return hadir
