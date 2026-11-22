"""Günlük içerik üretimi: post (video ya da çoklu görsel) + story.

    python -m src.build --day 1
    python -m src.build --day 1 --only post
    python -m src.build --days 1-7
    python -m src.build --all
"""
from __future__ import annotations

import argparse
import hashlib
import random
import sys
import time
from pathlib import Path

import yaml

for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")

from . import render, scenes, themes
from .audio import to_wav_bytes
from .config import BRAND, CONTENT, OUT


def load_calendar() -> dict[int, dict]:
    data = yaml.safe_load((CONTENT / "calendar.yaml").read_text(encoding="utf-8"))
    return {int(d["day"]): d for d in data["days"]}


def hashtags(day: int, extra: list[str] | None = None) -> str:
    """Instagram gönderi başına en fazla 5 etikete izin veriyor (Aralık 2025).

    Sıra: sabit marka etiketleri → günün kendi etiketleri → havuzdan tamamlama.
    Beş yer az olduğu için alakasız etiket koymaktansa günün konusuna yakın
    olanlar tercih ediliyor; gün etiketleri content/calendar.yaml'da.
    """
    h = BRAND["hashtags"]
    limit = h.get("max", 5)
    tags = list(h.get("always", []))
    for t in list(extra or []) + random.Random(day * 977).sample(h["pool"], k=len(h["pool"])):
        if len(tags) >= limit:
            break
        if t not in tags:
            tags.append(t)
    return " ".join(tags[:limit])


def caption(day: int, spec: dict, book_url: str | None) -> str:
    lines = [spec["caption"].strip()]
    if book_url:
        lines += ["", f"📘 {spec.get('book_line', 'Kitap ve detaylar')}: {book_url}"]
    lines += ["", BRAND["handle"] + " · " + BRAND["site"], "", hashtags(day, spec.get("tags"))]
    return "\n".join(lines)


def _theme_for(day: int, slot: str, spec: dict) -> tuple[dict, dict]:
    name = spec.get("theme") or themes.pick(day, slot)
    th = themes.resolve(name)
    var = themes.variant(f"{day}-{slot}-{name}-{spec.get('title','')}")
    return th, var


def _brand_for(theme: dict) -> dict:
    b = dict(BRAND)
    b["_theme_sfx"] = theme["sfx"]
    return b


def _seed(day: int, slot: str) -> int:
    return int(hashlib.sha1(f"{day}{slot}".encode()).hexdigest()[:8], 16)


def build_slot(day: int, slot: str, spec: dict, outdir: Path) -> list[Path]:
    """slot: 'post' | 'story'. spec['kind']: 'video' | 'carousel'."""
    kind = spec.get("kind", "video")
    fmt = "post" if slot == "post" else "story"
    theme, var = _theme_for(day, slot, spec)
    brand = _brand_for(theme)
    made: list[Path] = []

    t0 = time.time()
    tl = scenes.build(spec, brand, with_audio=(kind == "video"))
    html = render.build_html(tl, theme, var, fmt, brand, seed=_seed(day, slot))
    name = f"gun{day:02d}-{slot}"

    if kind == "video":
        mp4 = outdir / f"{slot}.mp4"
        render.render_video(html, tl.total, mp4, to_wav_bytes(tl.mix), fmt,
                            loudness=brand["audio"]["loudness"], name=name)
        made.append(mp4)
        srt = outdir / f"{slot}.srt"
        srt.write_text(scenes.to_srt(tl.cues), encoding="utf-8")
        made.append(srt)
        # kapak karesi: ilk sahnenin tam oturduğu an
        cover = render.render_stills(html, [tl.scenes[0]["t0"] + 1.1],
                                     outdir / "_tmp", fmt, name=name)
        dest = outdir / f"{slot}-kapak.jpg"
        cover[0].replace(dest)
        cover[0].parent.rmdir()
        made.append(dest)
    else:
        times = [s["t0"] + s["dur"] * 0.72 for s in tl.scenes]
        made += render.render_stills(html, times, outdir / slot, fmt, name=name)

    warn = ""
    if kind == "video":
        lo, hi = (35, 55) if slot == "post" else (8, 20)
        if not lo <= tl.total <= hi:
            warn = f"  ⚠ süre hedef dışı ({lo}-{hi} sn) — seslendirme metnini kısalt/uzat"
    print(f"  {slot}: {kind}, {tl.total:.1f} sn, tema={theme['name']}, "
          f"{len(tl.scenes)} sahne — {time.time()-t0:.0f} sn{warn}")
    return made


def build_day(day: int, only: str | None = None) -> Path:
    cal = load_calendar()
    if day not in cal:
        raise SystemExit(f"Takvimde {day}. gün yok.")
    d = cal[day]
    outdir = OUT / f"gun-{day:02d}"
    outdir.mkdir(parents=True, exist_ok=True)

    print(f"\n[gün {day:02d}] {d.get('title','')}")
    for slot in ("post", "story"):
        if only and slot != only:
            continue
        if slot not in d:
            continue
        build_slot(day, slot, d[slot], outdir)

    write_caption(day, d)
    return outdir


def write_caption(day: int, d: dict) -> Path:
    outdir = OUT / f"gun-{day:02d}"
    outdir.mkdir(parents=True, exist_ok=True)
    book = d["post"].get("book_url")
    if not book:
        slug = next((s.get("book") for s in d["post"]["scenes"] if s.get("book")), None)
        if slug:
            from .config import BOOKS
            book = BOOKS[slug]["url"]
    p = outdir / "aciklama.txt"
    p.write_text(caption(day, d["post"], book), encoding="utf-8")
    return p


def check(days: list[int]) -> int:
    """Render etmeden sadece süreleri ölç. TTS cache'e girer, asıl üretim hızlanır."""
    cal = load_calendar()
    bad = 0
    for day in days:
        d = cal[day]
        line = []
        for slot in ("post", "story"):
            spec = d[slot]
            if spec.get("kind", "video") != "video":
                line.append(f"{slot}: karusel")
                continue
            th = themes.resolve(spec.get("theme") or themes.pick(day, slot))
            tl = scenes.build(spec, _brand_for(th), with_audio=True)
            lo, hi = (35, 55) if slot == "post" else (8, 20)
            ok = lo <= tl.total <= hi
            bad += not ok
            line.append(f"{slot}: {tl.total:5.1f} sn {'  ' if ok else '⚠ '}")
        print(f"gün {day:02d}  " + " | ".join(line))
    print()
    print(f"hedef dışı: {bad}")
    return bad


def main(argv=None):
    ap = argparse.ArgumentParser(description="Şifa Yayınevi Instagram içerik üreticisi")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--day", type=int)
    g.add_argument("--days", help="aralık, örn. 1-7")
    g.add_argument("--all", action="store_true")
    ap.add_argument("--only", choices=["post", "story"])
    ap.add_argument("--aciklama", action="store_true",
                    help="render etme, sadece aciklama.txt dosyalarını yeniden yaz")
    ap.add_argument("--check", action="store_true",
                    help="render etme, sadece süreleri ölç")
    a = ap.parse_args(argv)

    if a.all:
        days = sorted(load_calendar())
    elif a.days:
        lo, hi = (int(x) for x in a.days.split("-"))
        days = list(range(lo, hi + 1))
    else:
        days = [a.day]

    if a.aciklama:
        for d in days:
            write_caption(d, load_calendar()[d])
        print(f"{len(days)} açıklama yenilendi")
        return
    if a.check:
        raise SystemExit(1 if check(days) else 0)

    for d in days:
        build_day(d, a.only)
    print(f"\nbitti → {OUT}")


if __name__ == "__main__":
    main(sys.argv[1:])
