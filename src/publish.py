"""O günün post + story içeriğini Instagram'a yayınlar.

Instagram medyayı kendi sunucusuyla indiriyor — dosyaların herkese açık bir
HTTPS adresinde durması gerekiyor (MEDIA_BASE). Doğrudan dosya yükleme yalnız
Facebook Login for Business kuran uygulamalara açık, bu yüzden kullanmıyoruz.

    python -m src.publish --slot post --deneme    # hiçbir şey yayınlamaz, kontrol eder
    python -m src.publish --slot post
    python -m src.publish --slot story --gun 3
    python -m src.publish --token-yenile

Gerekli ortam değişkenleri (.env ya da GitHub Secrets):
    IG_USER_ID    Instagram profesyonel hesabının kimliği
    IG_TOKEN      uzun ömürlü Instagram User access token (60 gün)
    IG_APP_SECRET sadece --token-yenile için değil, kısa ömürlüden uzun ömürlüye
                  geçerken gerekir; günlük yayında kullanılmaz
    MEDIA_BASE    out/ klasörünün herkese açık kök adresi, sonunda / olmadan
"""
from __future__ import annotations

import argparse
import os
import pathlib
import sys
import time
from datetime import date

import requests
import yaml

for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")

# Not: bilerek src'nin geri kalanını import etmiyoruz — yayın makinesinde
# yalnız requests + pyyaml kurulu olsun yeter, playwright/ffmpeg gerekmiyor.
ROOT = pathlib.Path(__file__).resolve().parent.parent
CONTENT, OUT = ROOT / "content", ROOT / "out"


def load_calendar() -> dict[int, dict]:
    data = yaml.safe_load((CONTENT / "calendar.yaml").read_text(encoding="utf-8"))
    return {int(d["day"]): d for d in data["days"]}

API = os.environ.get("IG_API", "https://graph.instagram.com/v23.0")
TIMEOUT = 60


# ------------------------------------------------------------------ yardımcılar
def _env(name: str) -> str:
    v = os.environ.get(name, "").strip()
    if not v:
        raise SystemExit(f"{name} tanımlı değil — .env dosyasına ya da GitHub Secrets'a ekle.")
    return v


def _call(method: str, path: str, **params) -> dict:
    params["access_token"] = _env("IG_TOKEN")
    r = requests.request(method, f"{API}/{path}", params=params, timeout=TIMEOUT)
    try:
        data = r.json()
    except ValueError:
        raise SystemExit(f"Instagram beklenmedik cevap verdi ({r.status_code}): {r.text[:300]}")
    if "error" in data:
        e = data["error"]
        raise SystemExit(f"Instagram hatası: {e.get('message')} "
                         f"(kod {e.get('code')}, {e.get('error_user_msg', '')})".strip())
    return data


def _plan() -> dict:
    return yaml.safe_load((CONTENT / "yayin.yaml").read_text(encoding="utf-8"))


def gun_for(today: date) -> int:
    """Takvimin kaçıncı günündeyiz — yayin.yaml'daki başlangıç tarihine göre."""
    return (today - _plan()["baslangic"]).days + 1


def url_for(rel: str) -> str:
    """out/ altındaki bir dosyanın herkese açık adresi."""
    return f"{_env('MEDIA_BASE').rstrip('/')}/{rel.replace(os.sep, '/')}"


def _files(day: int, slot: str, spec: dict) -> list[str]:
    """Yayınlanacak dosyaların out/ köküne göre yolları."""
    d = f"gun-{day:02d}"
    if spec.get("kind", "video") == "carousel":
        slides = sorted((OUT / d / slot).glob("*.jpg"))
        if not slides:
            raise SystemExit(f"{d}/{slot}/ içinde jpg yok — önce içeriği üret.")
        return [f"{d}/{slot}/{p.name}" for p in slides]
    return [f"{d}/{slot}.mp4"]


def _caption(day: int) -> str:
    p = OUT / f"gun-{day:02d}" / "aciklama.txt"
    return p.read_text(encoding="utf-8").strip() if p.exists() else ""


# ------------------------------------------------------------------ yayın akışı
def _container(**params) -> str:
    return _call("POST", f"{_env('IG_USER_ID')}/media", **params)["id"]


def _bekle(cid: str, label: str = "") -> None:
    """Konteyner hazır olana kadar bekle. Doküman: dakikada bir, en fazla 5 dakika."""
    for _ in range(30):
        st = _call("GET", cid, fields="status_code,status").get("status_code")
        if st == "FINISHED":
            return
        if st in ("ERROR", "EXPIRED"):
            detay = _call("GET", cid, fields="status").get("status", "")
            raise SystemExit(f"Konteyner {label} {st}: {detay}")
        time.sleep(10)
    raise SystemExit(f"Konteyner {label} 5 dakikada hazır olmadı.")


def _yayinla(cid: str) -> str:
    return _call("POST", f"{_env('IG_USER_ID')}/media_publish", creation_id=cid)["id"]


def publish(day: int, slot: str, deneme: bool = False) -> str | None:
    cal = load_calendar()
    if day not in cal:
        raise SystemExit(f"Takvimde {day}. gün yok — takvim 1-{max(cal)} arası.")
    spec = cal[day][slot]
    rels = _files(day, slot, spec)
    caption = "" if slot == "story" else _caption(day)   # story'de açıklama desteklenmiyor

    print(f"gün {day:02d} · {slot} · {spec.get('kind', 'video')} · {len(rels)} dosya")
    for rel in rels:
        print("   ", url_for(rel))

    if deneme:
        for rel in rels:
            r = requests.head(url_for(rel), timeout=TIMEOUT, allow_redirects=True)
            boyut = int(r.headers.get("content-length", 0)) / 1e6
            durum = "açık" if r.ok else f"ERİŞİLEMEDİ ({r.status_code})"
            print(f"    {durum}  {boyut:.1f} MB  {r.headers.get('content-type', '?')}")
        if caption:
            print(f"    açıklama: {len(caption)} karakter, {caption.count('#')} etiket")
        return None

    if slot == "story":
        cid = _container(media_type="STORIES", video_url=url_for(rels[0]))
    elif len(rels) > 1:  # karusel
        kids = []
        for rel in rels:
            k = _container(image_url=url_for(rel), is_carousel_item="true")
            _bekle(k, rel)
            kids.append(k)
        cid = _container(media_type="CAROUSEL", children=",".join(kids), caption=caption)
    else:
        cid = _container(media_type="REELS", video_url=url_for(rels[0]), caption=caption)

    _bekle(cid, slot)
    mid = _yayinla(cid)
    print(f"  yayınlandı → https://www.instagram.com/p/ (media id {mid})")
    return mid


def token_yenile() -> str:
    """Uzun ömürlü token'ı 60 gün daha uzatır. Token en az 24 saatlik olmalı."""
    r = requests.get(f"https://graph.instagram.com/refresh_access_token",
                     params={"grant_type": "ig_refresh_token",
                             "access_token": _env("IG_TOKEN")}, timeout=TIMEOUT)
    d = r.json()
    if "access_token" not in d:
        raise SystemExit(f"Token yenilenemedi: {d}")
    print(f"token yenilendi, {int(d.get('expires_in', 0)) // 86400} gün geçerli", file=sys.stderr)
    return d["access_token"]


def main(argv=None):
    ap = argparse.ArgumentParser(description="Günün içeriğini Instagram'a yayınlar")
    ap.add_argument("--slot", choices=["post", "story"])
    ap.add_argument("--gun", type=int, help="belirtilmezse yayin.yaml'daki tarihten hesaplanır")
    ap.add_argument("--deneme", action="store_true", help="yayınlama, sadece dosyaları kontrol et")
    ap.add_argument("--token-yenile", action="store_true",
                    help="yeni token'ı stdout'a basar, gerisini iş akışı halleder")
    a = ap.parse_args(argv)

    if a.token_yenile:
        print(token_yenile())
        return
    if not a.slot:
        raise SystemExit("--slot post|story gerekli")

    gun = a.gun or gun_for(date.today())
    if gun < 1:
        print(f"Yayın {_plan()['baslangic']} tarihinde başlıyor, henüz erken.")
        return
    if gun > max(load_calendar()):
        print(f"Takvim {max(load_calendar())}. günde bitti — content/calendar.yaml'a yeni gün ekle.")
        return
    publish(gun, a.slot, deneme=a.deneme)


if __name__ == "__main__":
    main(sys.argv[1:])
