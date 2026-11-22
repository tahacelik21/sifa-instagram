"""Google Cloud Text-to-Speech — LINEAR16 48 kHz mono, disk cache'li."""
from __future__ import annotations

import base64
import hashlib
import io
import json
import urllib.error
import urllib.request
import wave

import numpy as np

from .config import BRAND, CACHE, SR, tts_key

ENDPOINT = "https://texttospeech.googleapis.com/v1/text:synthesize"


def _cache_path(text: str, voice: str, rate: float):
    h = hashlib.sha1(f"{voice}|{rate}|{text}".encode("utf-8")).hexdigest()[:16]
    return CACHE / "tts" / f"{h}.wav"


def voice_for(lang: str) -> tuple[str, str, float]:
    """lang: 'tr' | 'ar' -> (dil kodu, ses adı, konuşma hızı)"""
    cfg = BRAND["tts"]
    if lang == "ar":
        return cfg["language_ar"], cfg["voice_ar"], cfg["speaking_rate_ar"]
    return cfg["language"], cfg["voice"], cfg["speaking_rate"]


def synth(text: str, lang: str = "tr", voice: str | None = None,
          rate: float | None = None) -> np.ndarray:
    """Metni seslendirir, float32 mono dizi döner. Aynı metin ikinci kez istenmez."""
    lang_code, dflt_voice, dflt_rate = voice_for(lang)
    voice = voice or dflt_voice
    rate = dflt_rate if rate is None else rate
    path = _cache_path(text, voice, rate)

    if not path.exists():
        body = {
            "input": {"text": text},
            "voice": {"languageCode": lang_code, "name": voice},
            "audioConfig": {
                "audioEncoding": "LINEAR16",
                "sampleRateHertz": SR,
                "speakingRate": rate,
            },
        }
        req = urllib.request.Request(
            f"{ENDPOINT}?key={tts_key()}",
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        try:
            raw = json.loads(urllib.request.urlopen(req, timeout=90).read())
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"TTS hatası {e.code}: {e.read().decode(errors='replace')[:500]}") from e
        path.write_bytes(base64.b64decode(raw["audioContent"]))

    return _read_wav(path.read_bytes())


def _read_wav(raw: bytes) -> np.ndarray:
    with wave.open(io.BytesIO(raw)) as w:
        assert w.getsampwidth() == 2, "16-bit bekleniyor"
        data = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2")
        if w.getnchannels() == 2:
            data = data.reshape(-1, 2).mean(axis=1)
        x = data.astype(np.float32) / 32768.0
    return _trim(x)


def _trim(x: np.ndarray, thresh: float = 2e-3, pad_ms: int = 60) -> np.ndarray:
    """Baş/sondaki sessizliği kırp — sahne zamanlaması TTS uzunluğundan türüyor."""
    loud = np.abs(x) > thresh
    if not loud.any():
        return x
    pad = int(SR * pad_ms / 1000)
    a = max(0, int(np.argmax(loud)) - pad)
    b = min(len(x), len(x) - int(np.argmax(loud[::-1])) + pad)
    return x[a:b]


def list_voices(lang: str = "tr-TR") -> list[str]:
    url = f"https://texttospeech.googleapis.com/v1/voices?languageCode={lang}&key={tts_key()}"
    data = json.loads(urllib.request.urlopen(url, timeout=30).read())
    return sorted(v["name"] for v in data.get("voices", []))


if __name__ == "__main__":
    import sys

    if "--voices" in sys.argv:
        print("\n".join(list_voices("ar-XA" if "--ar" in sys.argv else "tr-TR")))
    else:
        tr = synth("Bu ilmin adı")
        ar = synth("اَلصَّرْفُ", lang="ar")
        assert len(tr) > SR * 0.3 and len(ar) > SR * 0.3, "seslendirme boş döndü"
        print(f"tr {len(tr)/SR:.2f} sn · ar {len(ar)/SR:.2f} sn")
