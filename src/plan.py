"""Ürün tanıtım planını katalogla karşılaştırır.

Katalog ya da plan değiştiğinde atlanan, iki kez geçen veya artık var olmayan
bir başlık kalmadığını kontrol eder.

    python -m src.plan            # özet
    python -m src.plan --kontrol  # sorun varsa çıkış kodu 1
"""
from __future__ import annotations

import argparse
import sys

import yaml

from .config import BOOKS, CONTENT

for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")


def oku() -> dict:
    return yaml.safe_load((CONTENT / "tanitim-plani.yaml").read_text(encoding="utf-8"))


def denetle() -> list[str]:
    plan = oku()
    bitti = list(plan["tamamlanan"]["basliklar"])
    kalan: list[str] = []
    for e in plan["plan"]:
        kalan += [e["book"]] if e.get("book") else list(e["koleksiyon"])

    hepsi = bitti + kalan
    sorun = []
    for b in sorted(set(hepsi)):
        if b not in BOOKS:
            sorun.append(f"katalogda yok: {b}")
    for b in sorted(set(hepsi)):
        if hepsi.count(b) > 1:
            sorun.append(f"{hepsi.count(b)} kez geçiyor: {b}")
    for k in BOOKS:
        if k not in hepsi:
            sorun.append(f"hiç tanıtılmıyor: {k}")

    gunler = [e["day"] for e in plan["plan"]]
    if gunler != sorted(gunler):
        sorun.append("plan gün sırası bozuk")

    son = gunler[-1]
    print(f"katalog {len(BOOKS)} başlık · 1-{plan['tamamlanan']['araliq'].split('-')[-1]} "
          f"arası {len(bitti)} tanıtıldı · {gunler[0]}-{son} arası {len(plan['plan'])} kitap günü")
    print(f"kapsanan: {len(set(hepsi))}/{len(BOOKS)} başlık")
    return sorun


def main(argv=None):
    ap = argparse.ArgumentParser(description="Tanıtım planını katalogla karşılaştır")
    ap.add_argument("--kontrol", action="store_true", help="sorun varsa çıkış kodu 1")
    a = ap.parse_args(argv)

    sorun = denetle()
    for s in sorun:
        print("  ⚠", s)
    if not sorun:
        print("plan tutarlı — atlanan, tekrarlanan ya da kayıp başlık yok.")
    if a.kontrol:
        raise SystemExit(1 if sorun else 0)


if __name__ == "__main__":
    main(sys.argv[1:])
