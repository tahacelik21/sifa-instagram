"""Görsel temalar. Her gün farklı bir tema + farklı hareket varyantı düşer.

Tema = palet + arka plan modülü + giriş/çıkış animasyonu + efekt seçimi.
Şablon tek; çeşitlilik buradan geliyor.
"""
from __future__ import annotations

import hashlib

from .config import BRAND

C = BRAND["colors"]

THEMES: dict[str, dict] = {
    # 1 — kapak bordosu + altın geometrik kûfî örgü
    "kufi": {
        "dark": True,
        "bg": "kufi",
        "vars": {
            "--bg": C["bordo_koyu"], "--bg2": C["bordo"], "--ink": C["krem"],
            "--accent": C["altin"], "--accent2": C["altin_acik"],
            "--muted": "#C9B8A8", "--card": "rgba(255,255,255,.05)",
        },
        "enter": "zoomBlur", "text": "riseIn", "exit": "fadeOutUp",
        "sfx": {"transition": "whoosh", "accent": "chime"},
    },
    # 2 — şamua kâğıt, mürekkep akışı
    "samua": {
        "dark": False,
        "bg": "paper",
        "vars": {
            "--bg": C["samua"], "--bg2": "#EFE4D2", "--ink": C["murekkep"],
            "--accent": C["bordo"], "--accent2": C["altin"],
            "--muted": "#7A6A58", "--card": "rgba(94,17,24,.05)",
        },
        "enter": "inkBleed", "text": "blurIn", "exit": "fadeOutDown",
        "sfx": {"transition": "page", "accent": "chime"},
    },
    # 3 — koyu zemin, altın ışık huzmeleri
    "nur": {
        "dark": True,
        "bg": "rays",
        "vars": {
            "--bg": "#0E0B09", "--bg2": "#1C1510", "--ink": "#F7F1E6",
            "--accent": C["altin_acik"], "--accent2": C["altin"],
            "--muted": "#A1927E", "--card": "rgba(232,199,102,.07)",
        },
        "enter": "scaleFade", "text": "letterIn", "exit": "fadeOutScale",
        "sfx": {"transition": "whoosh", "accent": "impact"},
    },
    # 4 — beyaz editoryal ızgara, kırmızı aksan
    "editorial": {
        "dark": False,
        "bg": "grid",
        "vars": {
            "--bg": "#FFFFFF", "--bg2": "#F4F2EE", "--ink": "#141414",
            "--accent": C["kirmizi"], "--accent2": C["bordo"],
            "--muted": "#6C6C6C", "--card": "rgba(217,33,51,.06)",
        },
        "enter": "maskWipe", "text": "wipeRight", "exit": "wipeOutLeft",
        "sfx": {"transition": "whoosh", "accent": "impact"},
    },
    # 5 — arabesk çizgi animasyonu, krem zemin
    "arabesk": {
        "dark": False,
        "bg": "lines",
        "vars": {
            "--bg": "#F3EDE1", "--bg2": "#E6DAC6", "--ink": "#241B15",
            "--accent": C["yesil"], "--accent2": C["altin"],
            "--muted": "#6E6153", "--card": "rgba(31,77,61,.06)",
        },
        "enter": "foldIn", "text": "tiltIn", "exit": "fadeOutDown",
        "sfx": {"transition": "page", "accent": "chime"},
    },
    # 6 — zümrüt yeşili, yumuşak dalgalar
    "zumrut": {
        "dark": True,
        "bg": "waves",
        "vars": {
            "--bg": "#0E2A22", "--bg2": C["yesil"], "--ink": "#EFF6F1",
            "--accent": C["altin_acik"], "--accent2": "#8FD3BE",
            "--muted": "#9BB6AB", "--card": "rgba(255,255,255,.06)",
        },
        "enter": "slideUp", "text": "popIn", "exit": "fadeOutUp",
        "sfx": {"transition": "whoosh", "accent": "chime"},
    },
    # 7 — lacivert gece, toz zerrecikleri
    "lacivert": {
        "dark": True,
        "bg": "dust",
        "vars": {
            "--bg": "#0C1222", "--bg2": C["lacivert"], "--ink": "#EDF1F8",
            "--accent": C["altin"], "--accent2": C["teal"],
            "--muted": "#8C98B4", "--card": "rgba(255,255,255,.055)",
        },
        "enter": "dropIn", "text": "riseIn", "exit": "fadeOutScale",
        "sfx": {"transition": "whoosh", "accent": "impact"},
    },
    # 8 — ders tahtası, tebeşir dokusu
    "tahta": {
        "dark": True,
        "bg": "chalk",
        "vars": {
            "--bg": "#17211E", "--bg2": "#223029", "--ink": "#F2EFE6",
            "--accent": "#E8C766", "--accent2": "#9FC3A8",
            "--muted": "#9AA69C", "--card": "rgba(255,255,255,.05)",
        },
        "enter": "swipeLeft", "text": "wipeRight", "exit": "wipeOutLeft",
        "sfx": {"transition": "page", "accent": "chime"},
    },
}

ORDER = list(THEMES)


def pick(day: int, slot: str = "post") -> str:
    """Gün bazlı tema. Post ve story aynı gün farklı tema alır, ardışık gün tekrar etmez."""
    off = 0 if slot == "post" else 3
    return ORDER[(day * 3 + off) % len(ORDER)]


def variant(seed_text: str) -> dict:
    """Aynı tema iki kez düşse bile hareket/kompozisyon farklı olsun diye."""
    h = hashlib.sha1(seed_text.encode("utf-8")).digest()
    def b(i: int) -> int: return h[i]
    return {
        "bg_speed": round(0.7 + b(0) / 255 * 0.9, 3),
        "bg_angle": b(1) % 360,
        "bg_scale": round(0.85 + b(2) / 255 * 0.5, 3),
        "accent_angle": -14 + b(3) % 28,
        "align": ["center", "left"][b(4) % 2],
        "rule": ["bar", "dot", "line", "frame"][b(5) % 4],
        "kinetic": round(0.85 + b(6) / 255 * 0.35, 3),
    }


def resolve(name: str) -> dict:
    t = dict(THEMES[name])
    t["name"] = name
    return t


# ═══════════════════════════════════════════════════════════════════
# Kompozisyon: 61. günden itibaren tema sabit listeden seçilmiyor,
# palet × arka plan × hareket seti olarak üretiliyor. Üç listenin
# uzunlukları aralarında asal (12 · 13 · 11) ve adımlar farklı, bu
# yüzden aynı üçlü 1716 slotta bir tekrar eder — 180 günde hiç.
# 1-60. günler üretildiği için eski rotasyonda bırakıldı.
# ═══════════════════════════════════════════════════════════════════

FROZEN_UNTIL = 60

PALETTES: dict[str, dict] = {
    name: {"dark": t["dark"], "vars": t["vars"]} for name, t in THEMES.items()
}
PALETTES.update({
    # 9 — patlıcan moru + altın
    "erguvan": {"dark": True, "vars": {
        "--bg": "#241028", "--bg2": "#3A1A3E", "--ink": "#F6EEF4",
        "--accent": C["altin"], "--accent2": C["altin_acik"],
        "--muted": "#B9A2BC", "--card": "rgba(201,162,39,.07)"}},
    # 10 — koyu kahve + bakır
    "bakir": {"dark": True, "vars": {
        "--bg": "#1A120C", "--bg2": "#2E2014", "--ink": "#F5EADF",
        "--accent": "#C97B3C", "--accent2": "#E3A469",
        "--muted": "#A89079", "--card": "rgba(201,123,60,.08)"}},
    # 11 — derin deniz mavisi + açık altın
    "deniz": {"dark": True, "vars": {
        "--bg": "#07202B", "--bg2": "#0E3443", "--ink": "#EFF6F8",
        "--accent": C["altin_acik"], "--accent2": C["teal"],
        "--muted": "#8FAFB9", "--card": "rgba(57,161,157,.09)"}},
    # 12 — açık kum + koyu kahve (aydınlık)
    "kum": {"dark": False, "vars": {
        "--bg": "#F3EADC", "--bg2": "#E6D8C3", "--ink": "#2A1E13",
        "--accent": "#8A5A2B", "--accent2": C["altin"],
        "--muted": "#7C6952", "--card": "rgba(138,90,43,.07)"}},
    # 13 — zeytin yeşili + altın
    "zeytin": {"dark": True, "vars": {
        "--bg": "#14180E", "--bg2": "#242B17", "--ink": "#F2F4E8",
        "--accent": C["altin"], "--accent2": "#A8B977",
        "--muted": "#9BA585", "--card": "rgba(201,162,39,.08)"}},
})

BGS = ["kufi", "paper", "rays", "grid", "lines", "waves", "dust", "chalk",
       "mihrab", "tezhip", "nokta", "ipek", "yildiz", "sedef"]

MOTIONS: list[dict] = [
    {"enter": "zoomBlur",  "text": "riseIn",      "exit": "fadeOutUp",
     "sfx": {"transition": "whoosh", "accent": "chime"}},
    {"enter": "inkBleed",  "text": "blurIn",      "exit": "fadeOutDown",
     "sfx": {"transition": "page", "accent": "chime"}},
    {"enter": "scaleFade", "text": "letterIn",    "exit": "fadeOutScale",
     "sfx": {"transition": "whoosh", "accent": "impact"}},
    {"enter": "maskWipe",  "text": "wipeRight",   "exit": "wipeOutLeft",
     "sfx": {"transition": "whoosh", "accent": "impact"}},
    {"enter": "foldIn",    "text": "tiltIn",      "exit": "fadeOutDown",
     "sfx": {"transition": "page", "accent": "chime"}},
    {"enter": "slideUp",   "text": "popIn",       "exit": "fadeOutUp",
     "sfx": {"transition": "whoosh", "accent": "chime"}},
    {"enter": "dropIn",    "text": "riseIn",      "exit": "fadeOutScale",
     "sfx": {"transition": "whoosh", "accent": "impact"}},
    {"enter": "swipeLeft", "text": "wipeRight",   "exit": "wipeOutLeft",
     "sfx": {"transition": "page", "accent": "impact"}},
    {"enter": "curtainIn", "text": "slideDownIn", "exit": "fadeOutSide",
     "sfx": {"transition": "whoosh", "accent": "chime"}},
    {"enter": "irisIn",    "text": "spreadIn",    "exit": "irisOut",
     "sfx": {"transition": "whoosh", "accent": "impact"}},
    {"enter": "tiltUp",    "text": "stackIn",     "exit": "fadeOutTilt",
     "sfx": {"transition": "page", "accent": "chime"}},
]

PAL_NAMES = list(PALETTES)


def compose(day: int, slot: str = "post") -> dict:
    """Gün ve slota göre palet × arka plan × hareket birleşimi."""
    i = (day - 1) * 2 + (0 if slot == "post" else 1)
    pal = PAL_NAMES[i % len(PAL_NAMES)]           # 13 — 60'ı bölmüyor
    bg = BGS[(i * 5 + 1) % len(BGS)]              # 14, adım 5 (aralarında asal)
    mot = MOTIONS[(i * 3) % len(MOTIONS)]         # 11, adım 3
    p = PALETTES[pal]
    return {"name": f"{pal}·{bg}", "dark": p["dark"], "bg": bg, "vars": p["vars"],
            "enter": mot["enter"], "text": mot["text"], "exit": mot["exit"],
            "sfx": mot["sfx"]}


def for_day(day: int, slot: str = "post") -> dict:
    """O günün teması. 1-60 eski rotasyon, sonrası kompozisyon."""
    return resolve(pick(day, slot)) if day <= FROZEN_UNTIL else compose(day, slot)


if __name__ == "__main__":
    seen = [pick(d) for d in range(1, 31)]
    assert all(seen[i] != seen[i + 1] for i in range(len(seen) - 1)), "ardışık tema tekrarı"
    assert all(pick(d) != pick(d, "story") for d in range(1, 31)), "post/story teması çakıştı"

    # Kompozisyon: 180 günde aynı üçlü iki kez düşmesin
    uclu = [(t["name"], t["enter"]) for d in range(61, 181)
            for t in (for_day(d, "post"), for_day(d, "story"))]
    assert len(set(uclu)) == len(uclu), "kompozisyon tekrar etti"
    for d in range(61, 180):
        a, b = for_day(d, "post"), for_day(d + 1, "post")
        assert (a["bg"], a["enter"]) != (b["bg"], b["enter"]), f"gün {d}-{d+1} aynı hareket"
        assert a["name"] != for_day(d, "story")["name"], f"gün {d} post/story çakıştı"
    print(f"tema: 1-60 sabit rotasyon, 61+ kompozisyon "
          f"({len(PALETTES)} palet × {len(BGS)} zemin × {len(MOTIONS)} hareket)")
    print("  örnek:", ", ".join(for_day(d)["name"] for d in (61, 62, 91, 121, 151)))
