"""HTML -> kare -> mp4 / png.

Animasyonlar CSS'te mutlak gecikmeyle tanımlı; her kare için
`window.seek(t)` tüm animasyonları o ana sabitliyor. Böylece render
gerçek zamandan bağımsız ve tekrar üretilebilir.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
from playwright.sync_api import sync_playwright

from .config import ASSETS, CACHE, FORMATS, FPS, ROOT, SR, TPL, ffmpeg

# format -> (ölçek, pad_top, pad_h, pad_bottom, gap, altyazı yüksekliği, filigran yüksekliği)
METRICS = {
    "post":  dict(scale=1.00, pad_t=110, pad_h=96,  pad_b=200, gap=26, sub_b=96,  wm_b=42),
    "story": dict(scale=1.04, pad_t=320, pad_h=104, pad_b=640, gap=30, sub_b=420, wm_b=300),
}

CHROME_ARGS = [
    "--force-color-profile=srgb",
    "--font-render-hinting=none",
    "--disable-lcd-text",
    "--hide-scrollbars",
    "--disable-gpu-vsync",
]


def _dust(n: int, seed: int) -> list[dict]:
    import random

    r = random.Random(seed)
    return [
        {
            "x": round(r.random() * 100, 2),
            "y": round(40 + r.random() * 70, 2),
            "s": r.choice([3, 3, 4, 5, 7]),
            "dur": round(9 + r.random() * 16, 1),
            "delay": round(r.random() * 22, 1),
        }
        for _ in range(n)
    ]


def build_html(timeline, theme: dict, variant: dict, fmt: str, brand: dict, seed: int = 0) -> str:
    W, H = FORMATS[fmt]
    m = METRICS[fmt]
    sc = m["scale"]
    if fmt == "story":  # 9:16'da sola yaslı kompozisyon boş duruyor
        variant = dict(variant, align="center")

    env = Environment(loader=FileSystemLoader(str(TPL)), autoescape=select_autoescape(["html"]))
    tpl = env.get_template("base.html.j2")

    scenes = []
    for s in timeline.scenes:
        s = dict(s)
        rel = s.pop("_image_rel", "") or ""
        if rel:
            p = (ROOT / rel).resolve()
            s["image"] = p.as_uri() if p.exists() else ""
        scenes.append(s)

    def scale(px):
        return round(px * sc)

    return tpl.render(
        W=W, H=H, format=fmt,
        theme=theme, v=variant, brand=brand,
        scenes=scenes, cues=timeline.cues, total=timeline.total,
        assets=Path(ASSETS).as_uri(),
        dust=_dust(46, seed),
        s=scale, s2=scale,
        pad_t=m["pad_t"], pad_h=m["pad_h"],
        # altyazı yoksa (çoklu görsel) alttaki altyazı payı da gerekmiyor
        pad_b=m["pad_b"] if timeline.cues else m["pad_t"],
        gap=m["gap"], sub_b=m["sub_b"], wm_b=m["wm_b"],
    )


def _page(pw, html_path: Path, fmt: str):
    W, H = FORMATS[fmt]
    browser = pw.chromium.launch(args=CHROME_ARGS)
    page = browser.new_page(viewport={"width": W, "height": H}, device_scale_factor=1)
    page.goto(html_path.as_uri())
    page.wait_for_function("window.__ready === true", timeout=60_000)
    return browser, page


def render_video(html: str, total: float, out_path: Path, wav: bytes, fmt: str,
                 loudness: int = -14, name: str = "render") -> Path:
    html_path = CACHE / "render" / f"{name}-{fmt}.html"
    html_path.parent.mkdir(parents=True, exist_ok=True)
    html_path.write_text(html, encoding="utf-8")

    wav_path = CACHE / "render" / f"{name}.wav"
    wav_path.write_bytes(wav)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    frames = int(round(total * FPS))

    cmd = [
        ffmpeg(), "-y", "-loglevel", "error",
        "-f", "image2pipe", "-framerate", str(FPS), "-i", "-",
        "-i", str(wav_path),
        "-vf", "scale=in_range=full:out_range=limited,format=yuv420p",
        "-color_range", "tv", "-colorspace", "bt709",
        "-color_primaries", "bt709", "-color_trc", "bt709",
        "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-r", str(FPS),
        "-c:a", "aac", "-b:a", "192k", "-ar", str(SR),
        "-af", f"loudnorm=I={loudness}:TP=-1.5:LRA=11",
        "-movflags", "+faststart", "-shortest",
        str(out_path),
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)

    with sync_playwright() as pw:
        browser, page = _page(pw, html_path, fmt)
        try:
            for i in range(frames):
                page.evaluate("t => window.seek(t)", i / FPS)
                proc.stdin.write(page.screenshot(type="jpeg", quality=96))
        finally:
            browser.close()

    proc.stdin.close()
    err = proc.stderr.read().decode(errors="replace")
    if proc.wait() != 0:
        raise RuntimeError(f"ffmpeg hatası:\n{err}")
    return out_path


def render_stills(html: str, times: list[float], out_dir: Path, fmt: str,
                  name: str = "slide") -> list[Path]:
    html_path = CACHE / "render" / f"{name}-{fmt}.html"
    html_path.parent.mkdir(parents=True, exist_ok=True)
    html_path.write_text(html, encoding="utf-8")
    out_dir.mkdir(parents=True, exist_ok=True)

    paths = []
    with sync_playwright() as pw:
        browser, page = _page(pw, html_path, fmt)
        try:
            for i, t in enumerate(times, 1):
                page.evaluate("t => window.seek(t)", t)
                p = out_dir / f"{i:02d}.jpg"   # Instagram yalnız JPEG kabul ediyor
                page.screenshot(path=str(p), type="jpeg", quality=95)
                paths.append(p)
        finally:
            browser.close()
    return paths
