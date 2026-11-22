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


if __name__ == "__main__":
    seen = [pick(d) for d in range(1, 31)]
    assert all(seen[i] != seen[i + 1] for i in range(len(seen) - 1)), "ardışık tema tekrarı"
    assert all(pick(d) != pick(d, "story") for d in range(1, 31)), "post/story teması çakıştı"
    print("tema rotasyonu tamam:", " ".join(seen[:10]), "...")
