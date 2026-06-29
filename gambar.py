# -*- coding: utf-8 -*-
# =====================================================================
#  PENYUSUN GAMBAR LAPORAN  (grid foto + label nama)
#  Pola font fallback didaur ulang dari dashboard.py (_ambil_font).
# =====================================================================
import io
import math

from PIL import Image, ImageDraw, ImageFont

_FONT_BOLD = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
]
_FONT_REG = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]


def _font(size, bold=False):
    cands = _FONT_BOLD if bold else _FONT_REG
    for p in cands:
        try:
            return ImageFont.truetype(p, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _potong_teks(draw, teks, font, lebar_maks):
    if draw.textlength(teks, font=font) <= lebar_maks:
        return teks
    while teks and draw.textlength(teks + "…", font=font) > lebar_maks:
        teks = teks[:-1]
    return teks + "…"


def buat_grid_foto(foto_list, judul):
    """foto_list: list dict {nama, jam, img_bytes}. Kembalikan PNG bytes.
    Menyusun semua selfie jadi satu kanvas grid dengan nama + jam di bawah tiap foto.
    """
    if not foto_list:
        return _kanvas_kosong(judul)

    CELL_W, IMG_H, LABEL_H = 220, 220, 46
    PAD, KOL = 16, 4
    JUDUL_H = 64

    n = len(foto_list)
    baris = math.ceil(n / KOL)
    total_w = PAD + KOL * (CELL_W + PAD)
    total_h = JUDUL_H + PAD + baris * (IMG_H + LABEL_H + PAD)

    kanvas = Image.new("RGB", (total_w, total_h), (245, 247, 250))
    draw = ImageDraw.Draw(kanvas)

    fj = _font(28, bold=True)
    draw.text((PAD, 18), judul, fill=(20, 40, 80), font=fj)

    fn = _font(17, bold=True)
    ft = _font(14)

    for i, item in enumerate(foto_list):
        rr, cc = divmod(i, KOL)
        x = PAD + cc * (CELL_W + PAD)
        y = JUDUL_H + PAD + rr * (IMG_H + LABEL_H + PAD)

        # bingkai kartu
        draw.rectangle([x, y, x + CELL_W, y + IMG_H + LABEL_H],
                       fill=(255, 255, 255), outline=(210, 216, 224), width=1)

        # foto
        try:
            im = Image.open(io.BytesIO(item["img_bytes"])).convert("RGB")
            im = _crop_kotak(im, CELL_W, IMG_H)
            kanvas.paste(im, (x, y))
        except Exception:
            draw.rectangle([x, y, x + CELL_W, y + IMG_H], fill=(225, 228, 232))
            draw.text((x + 12, y + IMG_H // 2 - 8), "(foto gagal)",
                      fill=(120, 120, 120), font=ft)

        nama = _potong_teks(draw, item.get("nama", "-"), fn, CELL_W - 16)
        draw.text((x + 8, y + IMG_H + 6), nama, fill=(25, 30, 40), font=fn)
        draw.text((x + 8, y + IMG_H + 26), "✓ " + item.get("jam", ""),
                  fill=(20, 130, 60), font=ft)

    buf = io.BytesIO()
    kanvas.save(buf, format="PNG")
    return buf.getvalue()


def _crop_kotak(im, w, h):
    src_w, src_h = im.size
    rasio = max(w / src_w, h / src_h)
    nw, nh = int(src_w * rasio), int(src_h * rasio)
    im = im.resize((nw, nh))
    left, top = (nw - w) // 2, (nh - h) // 2
    return im.crop((left, top, left + w, top + h))


def _kanvas_kosong(judul):
    kanvas = Image.new("RGB", (640, 160), (245, 247, 250))
    draw = ImageDraw.Draw(kanvas)
    draw.text((20, 24), judul, fill=(20, 40, 80), font=_font(26, bold=True))
    draw.text((20, 80), "Belum ada teknisi yang check-in.",
              fill=(120, 120, 120), font=_font(18))
    buf = io.BytesIO()
    kanvas.save(buf, format="PNG")
    return buf.getvalue()
