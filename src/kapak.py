"""Kitap fotoğraflarının arka planını keser.

Ürün fotoğrafı raf, masa, duvar gibi bir zeminde çekiliyor; sahnenin bordo
zemininde bu kalabalık duruyor. Burada kitap kesilip saydam PNG'ye alınıyor,
videoda zeminin üstünde gölgesiyle duruyor.

    python -m src.kapak mecmuatus-sarf     # tek kitap
    python -m src.kapak --hepsi            # assets/books altındaki bütün fotoğraflar
    python -m src.kapak --onizleme         # kesilmiş kapakları tek sayfada kontrol et
    python -m src.kapak --geri molla-cami  # kesimi beğenmedin, orijinale dön

Orijinal dosya `<slug>-orijinal.<uzantı>` olarak saklanır; slug'a göre arama
yalnız `<slug>.<uzantı>` ile eşleştiği için kesilmiş PNG kullanılmaya başlar.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .config import ROOT

for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")

BOOKS = ROOT / "assets" / "books"
KAYNAK = (".jpg", ".jpeg", ".png", ".webp")
_session = None


def _remove(im: Image.Image) -> Image.Image:
    global _session
    from rembg import new_session, remove
    if _session is None:
        # u2net: genel amaçlı model, ürün fotoğraflarında iyi sonuç veriyor.
        # İlk çağrıda modeli indirir (~176 MB), sonrası internetsiz çalışır.
        _session = new_session("u2net")
    return remove(im, session=_session)


def kes(src: Path) -> Path:
    im = Image.open(src).convert("RGBA")
    out = _remove(im)
    kutu = out.getbbox()          # saydam kenarları at
    if kutu:
        out = out.crop(kutu)
    dst = src.with_suffix(".png")

    yedek = src.with_name(f"{src.stem}-orijinal{src.suffix}")
    if src != dst and not yedek.exists():
        src.rename(yedek)
    elif src != dst:
        src.unlink()
    out.save(dst)

    alfa = out.getchannel("A").histogram()
    oran = sum(alfa[9:]) / (out.width * out.height)
    print(f"{src.name} → {dst.name}  {out.width}×{out.height}  "
          f"kitap kareyi %{oran*100:.0f} dolduruyor")
    return dst


def geri_al(slug: str) -> Path:
    """Kesim beğenilmediyse orijinal fotoğrafa dön."""
    yedek = next((p for p in BOOKS.glob(f"{slug}-orijinal.*")
                  if p.suffix.lower() in KAYNAK), None)
    if not yedek:
        raise SystemExit(f"{slug}-orijinal.* yok — geri alınacak bir şey bulunamadı.")
    png = BOOKS / f"{slug}.png"
    if png.exists():
        png.unlink()
    hedef = BOOKS / f"{slug}{yedek.suffix}"
    yedek.rename(hedef)
    print(f"{slug}: kesim silindi, orijinal geri geldi → {hedef.name}")
    return hedef


def onizleme(dst: Path | None = None) -> Path:
    """Kesilmiş bütün kapakları marka zemininde tek sayfada toplar.

    Saydam PNG'yi beyaz zeminde incelemek yanıltıyor — kenardaki hâle ancak
    videodaki koyu zeminde görünüyor. Bu yüzden önizleme bordo zemine basılıyor.
    """
    from .config import BRAND, OUT

    dst = dst or OUT / "kapak-onizleme.jpg"
    zemin = BRAND["colors"]["bordo"]
    pngler = sorted(BOOKS.glob("*.png"))
    if not pngler:
        raise SystemExit("assets/books altında kesilmiş kapak yok.")

    HUCRE, ETIKET, SUTUN = 420, 46, min(4, len(pngler))
    satir = -(-len(pngler) // SUTUN)
    sayfa = Image.new("RGB", (SUTUN * HUCRE, satir * (HUCRE + ETIKET)), zemin)
    try:
        font = ImageFont.load_default(size=22)
    except TypeError:          # eski Pillow
        font = ImageFont.load_default()
    kalem = ImageDraw.Draw(sayfa)

    for i, p in enumerate(pngler):
        im = Image.open(p).convert("RGBA")
        im.thumbnail((HUCRE - 60, HUCRE - 60))
        x, y = (i % SUTUN) * HUCRE, (i // SUTUN) * (HUCRE + ETIKET)
        sayfa.paste(im, (x + (HUCRE - im.width) // 2, y + (HUCRE - im.height) // 2), im)
        alfa = im.getchannel("A").histogram()
        oran = sum(alfa[9:]) / (im.width * im.height) * 100
        uyari = "  ⚠ kesime bak" if oran < 30 or oran > 97 else ""
        kalem.text((x + 16, y + HUCRE - 6), f"{p.stem}  ·  %{oran:.0f} dolu{uyari}",
                   fill="#E8C766", font=font)

    dst.parent.mkdir(parents=True, exist_ok=True)
    sayfa.save(dst, quality=92)
    print(f"\nönizleme: {dst}  ({len(pngler)} kapak)")
    return dst


def _fotograflar() -> list[Path]:
    return sorted(p for p in BOOKS.iterdir()
                  if p.suffix.lower() in KAYNAK
                  and "-orijinal" not in p.stem
                  and p.suffix.lower() != ".png")


def main(argv=None):
    ap = argparse.ArgumentParser(description="Kitap fotoğrafının arka planını keser")
    ap.add_argument("slug", nargs="?", help="örn. mecmuatus-sarf")
    ap.add_argument("--hepsi", action="store_true", help="kesilmemiş bütün fotoğraflar")
    ap.add_argument("--onizleme", action="store_true",
                    help="kesmeden, mevcut kapakları tek sayfada göster")
    ap.add_argument("--geri", metavar="SLUG", help="kesimi sil, orijinal fotoğrafa dön")
    a = ap.parse_args(argv)

    if a.geri:
        geri_al(a.geri)
        return
    if a.onizleme:
        onizleme()
        return
    if a.hepsi:
        hedef = _fotograflar()
    elif a.slug:
        hedef = [p for p in BOOKS.glob(f"{a.slug}.*")
                 if p.suffix.lower() in KAYNAK and p.suffix.lower() != ".png"]
        if not hedef:
            raise SystemExit(f"assets/books/{a.slug}.* bulunamadı "
                             f"(ya da zaten kesilmiş).")
    else:
        raise SystemExit("slug ver ya da --hepsi kullan")

    for p in hedef:
        kes(p)
    print(f"\n{len(hedef)} fotoğraf kesildi → ilgili günleri yeniden üret")


if __name__ == "__main__":
    main(sys.argv[1:])
