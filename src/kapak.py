"""Kitap fotoğraflarının arka planını keser.

Ürün fotoğrafı raf, masa, duvar gibi bir zeminde çekiliyor; sahnenin bordo
zemininde bu kalabalık duruyor. Burada kitap kesilip saydam PNG'ye alınıyor,
videoda zeminin üstünde gölgesiyle duruyor.

    python -m src.kapak mecmuatus-sarf     # tek kitap
    python -m src.kapak --hepsi            # assets/books altındaki bütün fotoğraflar

Orijinal dosya `<slug>-orijinal.<uzantı>` olarak saklanır; slug'a göre arama
yalnız `<slug>.<uzantı>` ile eşleştiği için kesilmiş PNG kullanılmaya başlar.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PIL import Image

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


def _fotograflar() -> list[Path]:
    return sorted(p for p in BOOKS.iterdir()
                  if p.suffix.lower() in KAYNAK
                  and "-orijinal" not in p.stem
                  and p.suffix.lower() != ".png")


def main(argv=None):
    ap = argparse.ArgumentParser(description="Kitap fotoğrafının arka planını keser")
    ap.add_argument("slug", nargs="?", help="örn. mecmuatus-sarf")
    ap.add_argument("--hepsi", action="store_true", help="kesilmemiş bütün fotoğraflar")
    a = ap.parse_args(argv)

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
