"""Ses tasarımı: efektler numpy ile sentezlenir, müzik dosyası kullanılmaz.

Tasarım kararı: tonal/müzikal yatak yok. Geçiş ve vurgular için gürültü
tabanlı (whoosh, impact, sayfa) efektler ve tonal olmayan bir ortam dokusu
kullanılıyor. brand.yaml'da audio.pad=true yapılırsa hafif tonal yastık eklenir.
"""
from __future__ import annotations

import numpy as np

from .config import SR

_rng = np.random.default_rng(7)


# ---------------------------------------------------------------- yardımcılar
def _t(dur: float) -> np.ndarray:
    return np.arange(int(SR * dur), dtype=np.float32) / SR


def _env(n: int, attack: float, decay: float, curve: float = 2.0) -> np.ndarray:
    """Attack/decay zarfı, 0..1."""
    a = max(1, int(SR * attack))
    d = max(1, n - a)
    return np.concatenate([
        np.linspace(0, 1, a, dtype=np.float32) ** 0.6,
        (np.linspace(1, 0, d, dtype=np.float32) ** curve),
    ])[:n]


def _tv_onepole(x: np.ndarray, cutoff: np.ndarray, highpass: bool = False) -> np.ndarray:
    """Zamanla değişen tek kutuplu filtre.

    ponytail: saf Python döngüsü — birkaç yüz bin örnek için (~50 ms) yeterli.
    Darboğaz olursa scipy.signal.sosfilt ile blok blok yaklaşık filtreye geç.
    """
    a = np.exp(-2.0 * np.pi * np.clip(cutoff, 20, SR / 2.2) / SR).astype(np.float64)
    y = np.empty(len(x), dtype=np.float64)
    prev = 0.0
    xs = x.astype(np.float64)
    for i in range(len(xs)):
        prev = (1.0 - a[i]) * xs[i] + a[i] * prev
        y[i] = prev
    return (xs - y if highpass else y).astype(np.float32)


def _pink(n: int) -> np.ndarray:
    """1/f gürültü — frekans alanında şekillendirilmiş."""
    spec = np.fft.rfft(_rng.standard_normal(n))
    f = np.arange(len(spec))
    f[0] = 1
    spec /= np.sqrt(f)
    out = np.fft.irfft(spec, n).astype(np.float32)
    return out / (np.abs(out).max() + 1e-9)


def _norm(x: np.ndarray, peak: float = 1.0) -> np.ndarray:
    m = float(np.abs(x).max())
    return x * (peak / m) if m > 1e-9 else x


# ---------------------------------------------------------------- efektler
def whoosh(dur: float = 0.55, up: bool = True, bright: float = 1.0) -> np.ndarray:
    """Sahne geçişi. Gürültü, süpürülen alçak geçiren filtreden geçer."""
    n = int(SR * dur)
    cut = np.geomspace(350, 5200 * bright, n) if up else np.geomspace(5200 * bright, 300, n)
    x = _tv_onepole(_pink(n) * 2.2, cut.astype(np.float32))
    body = x * _env(n, dur * 0.35, dur * 0.65, 2.4)
    air = _tv_onepole(_pink(n), np.full(n, 2600, np.float32), highpass=True)
    air *= _env(n, dur * 0.5, dur * 0.5, 3.0) * 0.25
    return _norm(body + air, 0.9)


def impact(dur: float = 0.85, root: float = 62.0) -> np.ndarray:
    """Vurgu / yere oturma. Düşen sinüs + kısa tık."""
    n = int(SR * dur)
    t = _t(dur)
    f = root * np.exp(-t * 4.0) + root * 0.55
    sub = np.sin(2 * np.pi * np.cumsum(f) / SR).astype(np.float32)
    sub *= np.exp(-t * 6.0)
    click = _tv_onepole(_pink(int(SR * 0.05)), np.full(int(SR * 0.05), 3500, np.float32))
    click *= _env(len(click), 0.002, 0.048, 3.0) * 0.5
    out = sub.copy()
    out[: len(click)] += click
    return _norm(out, 0.95)


def chime(freq: float = 880.0, dur: float = 1.6) -> np.ndarray:
    """Anahtar kelime / Arapça terim belirince çalan yumuşak çan."""
    t = _t(dur)
    partials = [(1.0, 1.0), (2.76, 0.42), (5.40, 0.22), (8.93, 0.11)]
    out = np.zeros_like(t)
    for ratio, amp in partials:
        out += amp * np.sin(2 * np.pi * freq * ratio * t) * np.exp(-t * (2.0 + ratio * 0.5))
    out *= _env(len(t), 0.004, dur - 0.004, 1.0)
    return _norm(out.astype(np.float32), 0.65)


def riser(dur: float = 2.0) -> np.ndarray:
    """Kapanıştan / büyük açıklamadan önce gerilim."""
    n = int(SR * dur)
    cut = np.geomspace(180, 4800, n).astype(np.float32)
    x = _tv_onepole(_pink(n) * 2.0, cut, highpass=True)
    ramp = np.linspace(0, 1, n, dtype=np.float32) ** 2.2
    return _norm(x * ramp, 0.7)


def page(dur: float = 0.38) -> np.ndarray:
    """Sayfa çevirme — kitap sahnelerinde."""
    n = int(SR * dur)
    cut = np.geomspace(1200, 7000, n).astype(np.float32)
    x = _tv_onepole(_pink(n) * 1.6, cut, highpass=True)
    grit = _rng.standard_normal(n).astype(np.float32) * (_rng.random(n) < 0.004) * 0.6
    return _norm((x + grit) * _env(n, 0.06, dur - 0.06, 2.0), 0.6)


def ambience(dur: float, pad: bool = False) -> np.ndarray:
    """Tonal olmayan oda dokusu + çok hafif alçak uğultu."""
    n = int(SR * dur)
    bed = _tv_onepole(_pink(n), np.full(n, 1400, np.float32))
    lfo = 0.75 + 0.25 * np.sin(2 * np.pi * 0.06 * np.arange(n, dtype=np.float32) / SR)
    bed = bed * lfo
    t = np.arange(n, dtype=np.float32) / SR
    rumble = np.sin(2 * np.pi * 48 * t) * 0.18
    out = _norm(bed, 0.8) + rumble * 0.35
    if pad:
        for f, a in ((146.8, 0.5), (220.0, 0.32), (293.7, 0.2)):
            out += np.sin(2 * np.pi * f * t + _rng.random()) * a * 0.12
    return _norm(out.astype(np.float32), 0.55)


# ---------------------------------------------------------------- mikser
class Mixer:
    """Zaman çizelgesine ses yerleştirir, VO'ya göre ducking uygular."""

    def __init__(self, duration: float):
        self.n = int(SR * duration) + SR  # sonda 1 sn kuyruk
        self.vo = np.zeros(self.n, dtype=np.float32)
        self.bed = np.zeros(self.n, dtype=np.float32)

    def _place(self, target: np.ndarray, sig: np.ndarray, at: float, gain: float):
        i = max(0, int(SR * at))
        j = min(self.n, i + len(sig))
        if j > i:
            target[i:j] += sig[: j - i] * gain

    def add_vo(self, sig: np.ndarray, at: float, gain: float = 1.0):
        self._place(self.vo, sig, at, gain)

    def add_sfx(self, sig: np.ndarray, at: float, gain: float = 1.0):
        self._place(self.bed, sig, at, gain)

    def _duck(self, amount: float) -> np.ndarray:
        """VO varken yatağı kıs. Zarf: 40 ms tepe takibi + yumuşatma."""
        win = int(SR * 0.04)
        env = np.abs(self.vo)
        env = np.maximum.reduceat(env, np.arange(0, len(env), win))
        env = np.repeat(env, win)[: self.n]
        k = np.hanning(int(SR * 0.25)).astype(np.float32)
        env = np.convolve(env, k / k.sum(), mode="same")
        env = np.clip(env / (np.percentile(env, 97) + 1e-6), 0, 1)
        return 1.0 - (1.0 - amount) * env

    def render(self, duck: float = 0.45) -> np.ndarray:
        mix = self.vo + self.bed * self._duck(duck)
        mix = np.tanh(mix * 1.15) * 0.87  # yumuşak limiter
        return _norm(mix, 0.97)


def to_wav_bytes(x: np.ndarray) -> bytes:
    import io
    import wave

    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype("<i2").tobytes())
    return buf.getvalue()


if __name__ == "__main__":
    m = Mixer(4.0)
    m.add_sfx(ambience(4.0), 0, 0.12)
    m.add_sfx(whoosh(), 0.2, 0.5)
    m.add_sfx(impact(), 0.7, 0.5)
    m.add_sfx(chime(), 1.6, 0.4)
    m.add_sfx(riser(), 2.0, 0.4)
    out = m.render()
    assert np.isfinite(out).all() and np.abs(out).max() <= 1.0
    print(f"ses tasarımı demo: {len(out)/SR:.2f} sn, tepe {np.abs(out).max():.3f}")
