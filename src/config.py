"""Yollar, marka verisi ve ortam ayarları."""
from __future__ import annotations

import os
import sys
from pathlib import Path

for _s in (sys.stdout, sys.stderr):  # Windows konsolu cp1254, Arapça/Türkçe yazdırılabilsin
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")

import yaml

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
CONTENT = ROOT / "content"
OUT = ROOT / "out"
CACHE = ROOT / ".cache"
TPL = Path(__file__).resolve().parent / "templates"

for _d in (OUT, CACHE / "tts", CACHE / "img"):
    _d.mkdir(parents=True, exist_ok=True)

SR = 48_000  # tüm ses zinciri 48 kHz mono


def _load(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


BRAND = _load(ROOT / "brand.yaml")
BOOKS = _load(CONTENT / "books.yaml")


def _dotenv() -> dict[str, str]:
    f = ROOT / ".env"
    if not f.exists():
        return {}
    out = {}
    for line in f.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip().strip('"').strip("'")
    return out


_ENV = _dotenv()


def tts_key() -> str:
    key = os.environ.get("GOOGLE_TTS_API_KEY") or _ENV.get("GOOGLE_TTS_API_KEY")
    if not key:
        raise RuntimeError(
            "GOOGLE_TTS_API_KEY yok. .env dosyasına ekle ya da ortam değişkeni ver."
        )
    return key


def ffmpeg() -> str:
    """Sistemde ffmpeg aramıyoruz; imageio-ffmpeg'in getirdiği binary yeterli."""
    import imageio_ffmpeg

    return imageio_ffmpeg.get_ffmpeg_exe()


FORMATS = {
    "post": (1080, 1080),
    "story": (1080, 1920),
}
FPS = 30
