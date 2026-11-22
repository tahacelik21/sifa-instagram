"""Tek çalıştırmalık kontrol — ağ erişimi gerektirmez.

    python test_pipeline.py

Takvimi, temaları, zaman çizelgesini, HTML üretimini ve ses sentezini doğrular.
Gerçek TTS ve video kodlaması kapsam dışı (onlar `python -m src.build` ile test edilir).
"""
from __future__ import annotations

import sys

import numpy as np

for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")

from src import audio, render, scenes, themes
from src.build import caption, hashtags, load_calendar
from src.config import BOOKS, BRAND

SCENE_TYPES = {"hook", "concept", "point", "list", "compare", "quote", "stat", "book", "cta"}


def test_calendar():
    cal = load_calendar()
    assert len(cal) == 30, f"30 gün bekleniyor, {len(cal)} var"
    assert sorted(cal) == list(range(1, 31)), "gün numaraları 1..30 olmalı"

    books_used = 0
    for day, d in cal.items():
        for slot in ("post", "story"):
            assert slot in d, f"gün {day}: {slot} eksik"
            spec = d[slot]
            assert spec.get("scenes"), f"gün {day} {slot}: sahne yok"
            for i, s in enumerate(spec["scenes"]):
                assert s["type"] in SCENE_TYPES, f"gün {day} {slot} sahne {i}: bilinmeyen tip {s['type']}"
                if s.get("book"):
                    assert s["book"] in BOOKS, f"gün {day}: katalogda yok — {s['book']}"
                if s["type"] == "compare":
                    assert s.get("left") and s.get("right"), f"gün {day} {slot} sahne {i}: compare eksik"
                if s["type"] == "list":
                    assert s.get("items"), f"gün {day} {slot} sahne {i}: list boş"
            if spec.get("kind", "video") == "video":
                assert all(s.get("vo") for s in spec["scenes"]), f"gün {day} {slot}: vo eksik sahne var"
            else:
                assert all(s.get("dur") for s in spec["scenes"]), f"gün {day} {slot}: carousel'de dur eksik"
        assert d["post"].get("caption"), f"gün {day}: açıklama metni yok"
        if any(s.get("book") for s in d["post"]["scenes"]):
            books_used += 1

    assert 5 <= books_used <= 12, f"kitap önerisi dengesi bozuk: 30 günde {books_used}"
    print(f"  takvim: 30 gün, {books_used} gün kitap önerili")


def test_themes():
    posts = [themes.pick(d) for d in range(1, 31)]
    assert all(posts[i] != posts[i + 1] for i in range(29)), "ardışık gün aynı temayı aldı"
    assert all(themes.pick(d) != themes.pick(d, "story") for d in range(1, 31)), "post/story teması çakıştı"
    assert len(set(posts)) >= 6, "tema çeşitliliği düşük"
    v1, v2 = themes.variant("a"), themes.variant("b")
    assert v1 != v2 and themes.variant("a") == v1, "varyant deterministik değil"
    print(f"  temalar: {len(set(posts))} farklı tema dönüyor")


def test_timeline_and_html():
    cal = load_calendar()
    for day, d in cal.items():
        for slot, fmt in (("post", "post"), ("story", "story")):
            spec = d[slot]
            th = themes.resolve(spec.get("theme") or themes.pick(day, slot))
            brand = dict(BRAND, _theme_sfx=th["sfx"])
            tl = scenes.build(spec, brand, with_audio=False)

            t = 0.0
            for s in tl.scenes:
                assert abs(s["t0"] - t) < 1e-6, f"gün {day} {slot}: sahne başlangıcı kaymış"
                assert s["dur"] > 0
                t += s["dur"]
            assert abs(tl.total - t) < 1e-6

            html = render.build_html(tl, th, themes.variant(f"{day}{slot}"), fmt, brand, seed=day)
            assert "{{" not in html and "{%" not in html, f"gün {day} {slot}: şablon tam işlenmemiş"
            assert "window.seek" in html
            for s in tl.scenes:
                assert f'--t0:{s["t0"]}s' in html, f"gün {day} {slot}: sahne zamanı HTML'e geçmemiş"
    print(f"  zaman çizelgesi + HTML: {len(cal)*2} çıktı üretildi")


def test_cues():
    parts = scenes._chunks("Sarf kelimenin içini çözer. Nahiv ise cümledeki yerini belirler.")
    assert parts and all(len(p[0]) <= scenes.MAX_CUE + 12 for p in parts), parts
    srt = scenes.to_srt([{"t0": 0.0, "t1": 1.5, "text": "deneme"}])
    assert "00:00:00,000 --> 00:00:01,500" in srt, srt
    print(f"  altyazı: {len(parts)} satıra bölündü")


def test_audio():
    m = audio.Mixer(3.0)
    m.add_sfx(audio.ambience(3.0), 0, 0.1)
    m.add_sfx(audio.whoosh(), 0.3, 0.5)
    m.add_sfx(audio.impact(), 0.9, 0.5)
    m.add_sfx(audio.chime(), 1.5, 0.4)
    m.add_sfx(audio.riser(1.2), 1.6, 0.4)
    m.add_vo(np.sin(np.linspace(0, 400, audio.SR)).astype(np.float32) * 0.4, 1.0)
    out = m.render()
    assert np.isfinite(out).all(), "ses tasarımında NaN/inf"
    assert np.abs(out).max() <= 1.0, "kırpma riski"
    assert len(audio.to_wav_bytes(out)) > 44
    print(f"  ses: {len(out)/audio.SR:.1f} sn, tepe {np.abs(out).max():.2f}")


def test_caption():
    cal = load_calendar()
    c = caption(1, cal[1]["post"], "https://ornek")
    assert BRAND["handle"] in c and "https://ornek" in c and "#" in c
    # Instagram gönderi başına 5 etiketle sınırlı (Aralık 2025)
    for gun in (1, 7, 22, 30):
        t = hashtags(gun, cal[gun]["post"].get("tags"))
        assert len(t.split()) == 5, f"gün {gun}: {t}"
        assert len(set(t.split())) == 5, f"gün {gun} tekrar eden etiket: {t}"
    assert caption(1, cal[2]["post"], None).count("http") == 0, "kitapsız günde link çıkmamalı"
    print(f"  açıklama: {len(c)} karakter, {len(hashtags(1).split())} etiket")


def test_publish():
    """Yayın: gün hesabı, dosya seçimi, story'de açıklama olmaması."""
    import datetime
    import os
    os.environ.setdefault("MEDIA_BASE", "https://ornek.test/out")
    from src import publish

    bas = publish._plan()["baslangic"]
    assert publish.gun_for(bas) == 1, "başlangıç günü 1 olmalı"
    assert publish.gun_for(bas + datetime.timedelta(days=29)) == 30
    assert publish.url_for("gun-01/post.mp4") == "https://ornek.test/out/gun-01/post.mp4"

    cal = publish.load_calendar()
    video = publish._files(1, "post", cal[1]["post"])
    assert video == ["gun-01/post.mp4"], video
    karusel = next(d for d in cal if cal[d]["post"].get("kind") == "carousel")
    slaytlar = publish._files(karusel, "post", cal[karusel]["post"])
    assert len(slaytlar) >= 2 and all(f.endswith(".jpg") for f in slaytlar), slaytlar
    assert 2 <= len(slaytlar) <= 10, f"karusel 2-10 arası olmalı: {len(slaytlar)}"
    print(f"  yayın: gün hesabı tamam, karusel {karusel}. günde {len(slaytlar)} slayt")


if __name__ == "__main__":
    for fn in (test_calendar, test_themes, test_timeline_and_html, test_cues, test_audio, test_caption, test_publish):
        print(f"{fn.__name__} …")
        fn()
    print("\nhepsi geçti.")
