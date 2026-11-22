"""İçerik tanımını zaman çizelgesine çevirir: sahne süreleri, altyazı kuyruğu, ses yerleşimi.

Sahne süreleri seslendirmenin gerçek uzunluğundan türüyor — önce TTS, sonra render.

Seslendirme iki dilli: `vo` metnindeki Arapça harf içeren kelimeler otomatik
algılanır ve Arapça sesle okunur, gerisi Türkçe sesle. Türkçe seslendiriciye
Arapça okutmak yerine dili değiştiriyoruz; aynı ses karakteri (Schedar) iki
dilde de bulunduğu için geçiş aynı anlatıcı gibi duyuluyor.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

import numpy as np

from . import audio as A
from . import tts
from .config import BOOKS, ROOT, SR

LEAD = 0.35   # sahne oturduktan sonra ses başlar
TAIL = 0.45   # ses bittikten sonra sahne biraz nefes alır
MIN_DUR = 2.2
MAX_CUE = 42  # altyazı satır uzunluğu (karakter)

# Arapça blokları + Arapça sunum formları
AR_CHARS = re.compile(
    r"[؀-ۿݐ-ݿࢠ-ࣿﭐ-﷿ﹰ-﻿]"
)


# Karşılaştırma için sadeleştirme: harekeler, noktalama, büyük/küçük harf atılır
_HARAKAT = re.compile("[ً-ْٰـ]")   # tenvin/hareke/şedde/sükûn/tatvîl
_PUNCT = re.compile("[^\\w\\s؀-ۿ]+", re.UNICODE)


def _norm(s: str) -> str:
    s = _HARAKAT.sub("", (s or "").replace("<br>", " "))
    return " ".join(_PUNCT.sub(" ", s).lower().split())


def _visible(scene: dict) -> str:
    """Sahnede ekranda duran bütün metin — altyazı bunu tekrar etmesin diye."""
    parts = [scene.get(k, "") for k in
             ("tr", "ar", "body", "label", "big", "title", "title_tr", "subtitle", "kicker")]
    parts += [str(x) for x in scene.get("items", [])]
    for side in ("left", "right"):
        col = scene.get(side) or {}
        parts += [col.get("ar", ""), col.get("title", ""), col.get("text", "")]
    return _norm(" ".join(str(p) for p in parts if p))


@dataclass
class Timeline:
    scenes: list[dict]
    cues: list[dict]
    total: float
    mix: np.ndarray = field(repr=False)


BOOK_DIR = "assets/books"
_IMG_EXT = (".jpg", ".jpeg", ".png", ".webp")


def _book_image(slug: str) -> str:
    """assets/books/<slug>.<uzanti> — dosya adi slug ile ayni olmali."""
    d = ROOT / BOOK_DIR
    return next((f"{BOOK_DIR}/{f.name}" for f in sorted(d.glob(f"{slug}.*"))
                 if f.suffix.lower() in _IMG_EXT), "")


def _resolve_book(scene: dict) -> dict:
    """book sahnesi katalogdan dolar; sahnede verilen alanlar üstüne yazar."""
    slug = scene.get("book")
    if not slug:
        return scene
    b = BOOKS[slug]
    out = dict(scene)
    out.setdefault("title", b["title"])
    out.setdefault("title_tr", b["title_tr"])
    out.setdefault("subtitle", b.get("subtitle", ""))
    out.setdefault("chips", b.get("meta", []))
    out["_image_rel"] = _book_image(slug)
    return out


def segments(vo: str) -> list[tuple[str, str]]:
    """vo metnini dile göre parçalara ayırır -> [('tr'|'ar', metin), …]

    Kelime bazlı: içinde Arapça harf geçen kelime Arapça sayılır, ardışık aynı
    dildeki kelimeler tek parçada toplanır. Noktalama kendi kelimesiyle kalır.
    """
    groups: list[list] = []
    for w in vo.split():
        lang = "ar" if AR_CHARS.search(w) else "tr"
        if groups and groups[-1][0] == lang:
            groups[-1][1].append(w)
        else:
            groups.append([lang, [w]])
    return [(lang, " ".join(words)) for lang, words in groups]


def _chunks(text: str) -> list[tuple[str, float]]:
    """Altyazıyı satırlara böl, her satıra bir ağırlık ver.

    ponytail: ağırlık = karakter sayısı + noktalama duraklaması. TTS hızı sabit
    olduğu için yeterince isabetli. Kelime kelime hassasiyet gerekirse
    v1beta1 `enableTimePointing` + SSML <mark> ile gerçek zaman damgasına geç.
    """
    words = text.split()
    lines: list[str] = []
    cur = ""
    for w in words:
        if cur and len(cur) + 1 + len(w) > MAX_CUE:
            lines.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
        if cur.endswith((".", "?", "!", ":")) and len(cur) > MAX_CUE * 0.55:
            lines.append(cur)
            cur = ""
    if cur:
        lines.append(cur)

    out = []
    for ln in lines:
        w = len(ln) + 3.0 * len(re.findall(r"[.?!:;,—]", ln))
        out.append((ln, float(w)))
    return out


def build(spec: dict, brand: dict, with_audio: bool = True) -> Timeline:
    """spec['scenes'] -> zamanlanmış sahneler + altyazı + miks."""
    raw = [_resolve_book(s) for s in spec["scenes"]]
    gap = brand["tts"].get("gap", 0.2)

    # 1) seslendirme — her sahne için dil parçaları
    per_scene: list[list[tuple[str, str, np.ndarray]]] = []
    for s in raw:
        vo = s.get("vo")
        if vo and with_audio:
            per_scene.append([(lang, txt, tts.synth(txt, lang=lang))
                              for lang, txt in segments(vo)])
        else:
            per_scene.append([])

    # 2) süreler + altyazı + ses yerleşimi
    t = 0.0
    scenes, cues, placements = [], [], []
    for s, segs in zip(raw, per_scene):
        if segs:
            vdur = sum(len(a) / SR for _, _, a in segs) + gap * (len(segs) - 1)
            dur = max(MIN_DUR, LEAD + vdur + TAIL)
        else:
            dur = float(s.get("dur", 2.6))

        out = dict(s)
        out["t0"] = round(t, 3)
        out["dur"] = round(dur, 3)
        scenes.append(out)

        shown = _visible(out)

        def hidden(line: str) -> bool:
            n = _norm(line)
            return len(n) > 10 and n in shown

        c = t + LEAD
        for lang, text, aud in segs:
            d = len(aud) / SR
            placements.append((aud, c))
            if lang == "ar":
                # Arapça parça tek satır kalır — kırmak okunurluğu bozuyor
                cues.append({"t0": round(c, 3), "t1": round(c + d, 3),
                             "text": text, "rtl": True, "hidden": hidden(text)})
            else:
                parts = _chunks(text)
                tot_w = sum(w for _, w in parts) or 1.0
                cc = c
                for line, w in parts:
                    span = d * w / tot_w
                    cues.append({"t0": round(cc, 3), "t1": round(cc + span, 3),
                                 "text": line, "rtl": False, "hidden": hidden(line)})
                    cc += span
            c += d + gap
        t += dur

    total = round(t, 3)
    mix = _mix(scenes, placements, total, brand) if with_audio else np.zeros(1, np.float32)
    return Timeline(scenes=scenes, cues=cues, total=total, mix=mix)


def _mix(scenes, placements, total, brand) -> np.ndarray:
    cfg = brand["audio"]
    sfx_g = cfg["sfx_gain"]
    m = A.Mixer(total)

    if cfg.get("ambience", True):
        m.add_sfx(A.ambience(total + 1.0, pad=cfg.get("pad", False)), 0.0, cfg["ambience_gain"])

    trans = brand["_theme_sfx"]["transition"]
    accent = brand["_theme_sfx"]["accent"]
    whoosh_up = A.whoosh(0.55, up=True)
    whoosh_dn = A.whoosh(0.5, up=False)
    pg = A.page()
    acc = A.chime(784.0) if accent == "chime" else A.impact()

    for i, s in enumerate(scenes):
        t0 = s["t0"]
        if i:  # ilk sahnede geçiş sesi yok
            sig = pg if trans == "page" else (whoosh_up if i % 2 else whoosh_dn)
            m.add_sfx(sig, max(0.0, t0 - 0.22), sfx_g * 0.8)
        else:
            m.add_sfx(A.impact(0.9), 0.12, sfx_g * 0.75)

        if s["type"] in ("concept", "stat", "quote"):
            m.add_sfx(acc, t0 + 0.34, sfx_g * 0.55)
        if s["type"] == "book":
            m.add_sfx(pg, t0 + 0.1, sfx_g * 0.7)
        if s["type"] == "cta":
            m.add_sfx(A.riser(1.5), max(0.0, t0 - 1.35), sfx_g * 0.45)
            m.add_sfx(A.impact(1.0, 58.0), t0 + 0.1, sfx_g * 0.6)

    for vo, at in placements:
        m.add_vo(vo, at, 1.0)

    return m.render(duck=cfg["duck"])


def to_srt(cues: list[dict]) -> str:
    def ts(x: float) -> str:
        h, r = divmod(x, 3600)
        mnt, sec = divmod(r, 60)
        return f"{int(h):02d}:{int(mnt):02d}:{int(sec):02d},{int(round((sec % 1) * 1000)):03d}"

    return "\n".join(
        f"{i}\n{ts(c['t0'])} --> {ts(c['t1'])}\n{c['text']}\n"
        for i, c in enumerate(cues, 1)
    )


if __name__ == "__main__":
    segs = segments("Bu ilmin adı اَلصَّرْف, yani kelimenin iç yapısı.")
    assert [l for l, _ in segs] == ["tr", "ar", "tr"], segs
    assert segments("sadece türkçe") == [("tr", "sadece türkçe")]
    assert segments("اَلنَّحْو") == [("ar", "اَلنَّحْو")]
    parts = _chunks("Sarf kelimenin içini çözer. Nahiv ise cümledeki yerini belirler.")
    assert parts and all(len(p[0]) <= MAX_CUE + 12 for p in parts), parts
    assert "00:00:00,000 --> 00:00:01,500" in to_srt([{"t0": 0.0, "t1": 1.5, "text": "x"}])
    sc = {"tr": "Sözün yerinde ve etkili olması.", "ar": "اَلْبَلَاغَة"}
    assert _visible(sc) and "sözün yerinde ve etkili olması" in _visible(sc)
    assert _norm("اَلْبَلَاغَة.") in _visible(sc), "harekeler sadeleşmedi"
    print("dil ayrımı tamam:", [(l, t[:18]) for l, t in segs])
