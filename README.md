# Şifa Yayınevi — Instagram içerik üretim sistemi

Arapça eğitimi ve dinî ilimler üzerine günlük Instagram içeriği üretir:
her gün bir **post** (video ya da çoklu görsel) ve bir **story** (9:16 video).

Videolar HTML/CSS ile animasyonlanır, kare kare yakalanır, seslendirme Google TTS'ten
gelir, geçiş/vurgu/ortam sesleri numpy ile sentezlenir. Hiç stok müzik ya da
hazır şablon dosyası kullanılmaz.

---

## Kurulum

```bash
python -m pip install playwright jinja2 numpy imageio-ffmpeg requests pyyaml pillow
```

```bash
python -m playwright install chromium
```

`ffmpeg` ayrıca kurulmaz — `imageio-ffmpeg` kendi binary'siyle gelir.

API anahtarı `.env` dosyasında:

```
GOOGLE_TTS_API_KEY=...
```

> Bu anahtar sohbet üzerinden paylaşıldı. Google Cloud konsolundan
> **yenileyip** kullanımını yalnız Text-to-Speech API'siyle sınırlamanı tavsiye ederim.

---

## Kullanım

```bash
python -m src.build --day 1
```

```bash
python -m src.build --days 1-7
```

```bash
python -m src.build --all
```

Sadece bir slot: `--only post` ya da `--only story`.

Render etmeden bütün günlerin süresini ölçmek için (TTS cache'e girer, asıl
üretim hızlanır):

```bash
python -m src.build --all --check
```

Çıktı `out/gun-01/` altında:

| Dosya | Nedir |
|---|---|
| `post.mp4` | 1080×1080, altyazılı, sesli |
| `post.srt` | ayrı altyazı dosyası (IG'ye ayrıca yüklemek istersen) |
| `post-kapak.png` | kapak karesi |
| `post/01.png …` | çoklu görsel günlerinde karusel slaytları |
| `story.mp4` | 1080×1920 |
| `story.srt`, `story-kapak.png` | — |
| `aciklama.txt` | gönderi metni + link + hashtag |

Doğrulama:

```bash
python test_pipeline.py
```

Takvimi, tema rotasyonunu, sahne zamanlamasını, HTML üretimini ve ses
sentezini ağ olmadan kontrol eder. İçerik ekledikten sonra bunu çalıştır.

---

## İçeriği düzenlemek

Günlük içerik tek dosyada: **`content/calendar.yaml`**.

```yaml
- day: 3
  title: "el-Binâ: 35 bâb"
  post:
    kind: video          # video | carousel
    theme: kufi          # boş bırakılırsa rotasyondan düşer
    caption: |
      Gönderi metni…
    scenes:
      - type: concept
        kicker: "EL-BİNÂ"
        ar: "اَلْبِنَاء"
        translit: "el-Binâ"
        tr: "Fiilin kuruluş kalıpları."
        vo: "Binâ, fiilin hangi kalıpta kurulduğunu öğreten metindir."
```

**Sahne süresi `vo` metninden hesaplanır** — önce seslendirme üretilir, gerçek
uzunluğu ölçülür, sahne ona göre zamanlanır. Videoyu kısaltmak için `vo`'yu kısalt.
Çoklu görselde `vo` yerine `dur` (saniye) yazılır.

### İki dilli seslendirme

`vo` içine **doğrudan Arapça yaz**. Arapça harf içeren kelimeler otomatik
algılanır ve Arapça sesle (`ar-XA-Chirp3-HD-Schedar`) okunur, gerisi Türkçe
sesle. İki dilde de aynı ses karakteri kullanıldığı için geçiş aynı anlatıcı
gibi duyulur.

```yaml
vo: "اَلصَّرْفُ. Kelimenin kendi içindeki değişimini inceleyen ilim."
```

Arapçayı **harekeli** yaz — TTS harekeyi dikkate alıyor, harekesiz metni
tahmin ederek okuyor. Arapça parçalar `tts.speaking_rate_ar` hızıyla (varsayılan
0.88) okunur ki terimler tane tane duyulsun; dil değişiminde `tts.gap` kadar
nefes bırakılır.

Altyazı da parçaya göre ayrılır: Arapça satırlar Amiri fontuyla, sağdan sola
yazılır. Ekranda görünen Arapça ise `ar` alanına yazılır — `vo` ile aynı
kelimeyi kullanırsan ses ve görüntü örtüşür.

### Sahne tipleri

| Tip | Alanlar | Ne için |
|---|---|---|
| `hook` | kicker, tr, ar, body | Açılış sorusu / merak |
| `concept` | kicker, ar, translit, tr, body | Terim tanıtımı |
| `point` | kicker, tr, ar, body | Tek fikir |
| `list` | kicker, tr, items[] | Maddeli anlatım |
| `compare` | kicker, tr, left{ar,title,text}, right{…} | İki şeyi karşılaştırma |
| `quote` | kicker, ar, tr, src | Âyet / klasik metin alıntısı |
| `stat` | kicker, big, label, body | Sayı vurgusu |
| `book` | kicker, book (slug) | Kitap tanıtımı (görsel varsa otomatik) |
| `cta` | tr, body | Kapanış |

### Etiketler

Instagram **gönderi başına en fazla 5 etikete** izin veriyor (Aralık 2025'ten beri;
önceki sınır 30'du). Beş yer az olduğu için etiketler günün konusuna göre seçiliyor:

- `brand.yaml` → `hashtags.always`: her gönderide çıkan 2 etiket
- `content/calendar.yaml` → her günün `post.tags` alanı: o güne özel 3 etiket
- Gün etiket tanımlamamışsa kalan yerler `hashtags.pool` havuzundan tamamlanır

Etiketleri değiştirdikten sonra videoları yeniden üretmeye gerek yok:

```bash
python -m src.build --all --aciklama
```

Sadece `aciklama.txt` dosyalarını yeniden yazar.

### Kitaplar

`content/books.yaml` — slug, başlık, alt başlık, künye, link. `book: mecmuatus-sarf`
yazınca sahne buradan dolar. **Fiyat gösterilmiyor.**

Kitap görselleri **`assets/books/`** altında, dosya adı slug ile aynı:

```
assets/books/mecmuatus-sarf.jpg
assets/books/molla-cami.png
```

Uzantı `jpg / jpeg / png / webp` olabilir, başka ayar gerekmez — o kitabın
sahnesine otomatik yerleşir. Hangi dosya adı bekleniyor, hangisi eksik:
`assets/books/OKUBENI.txt`. Görseli olmayan kitapta sahne yazıyla kurulur.

> **Not:** `mecmuatus-sarf` kaydındaki alt başlık ("Klasik sarf metinleri tek
> ciltte") genel tutuldu — ürün sayfası cilt içindeki risalelerin listesini
> vermiyor. Elindeki nüshadan bakıp (el-Emsile, el-Binâ, el-Maksûd, el-İzzî,
> Merâh…) birebir yazman daha iyi olur.

---

## Otomatik yayın

Her gün o günün story'si ve postu Instagram'a kendiliğinden gider; iş GitHub
Actions'ta dönüyor, bilgisayarın açık olması gerekmiyor.

Kurulum adımları: **[KURULUM-INSTAGRAM.md](KURULUM-INSTAGRAM.md)**

```bash
python -m src.publish --slot post --gun 1 --deneme
```

`--deneme` hiçbir şey paylaşmaz, sadece dosyaların herkese açık adresten
erişilebildiğini kontrol eder. Başlangıç tarihi `content/yayin.yaml`,
saatler `.github/workflows/yayin.yml` içinde.

Instagram medyayı verdiğin adresten kendisi indirdiği için `out/` klasörü
depoya giriyor ve depo herkese açık olmak zorunda.

---

## Marka kimliği

`brand.yaml` — tek kaynak. Renkler sitenin CSS'inden (`#d92133`) ve
Mecmûatü's-Sarf kapağından (bordo + altın + şamua) türetildi.

| | |
|---|---|
| Ana renk | bordo `#5E1118` |
| Aksan | altın `#C9A227`, kırmızı `#D92133` |
| Zemin | şamua `#F6EFE2` |
| Başlık fontu | Playfair Display |
| Metin fontu | Inter |
| Arapça | Amiri |
| Ton | Sakin, öğretici, iddiasız. "Efsane / inanılmaz / şok" yok. |

Seslendirme: `tr-TR-Chirp3-HD-Schedar` (erkek, sıcak).
Arapça: `ar-XA-Chirp3-HD-Schedar` — aynı karakterin Arapça sürümü.
Değiştirmek için `brand.yaml` → `tts.voice` / `tts.voice_ar`. Listeler:

```bash
python -m src.tts --voices
```

```bash
python -m src.tts --voices --ar
```

---

## Temalar

`src/themes.py` — 8 tema. Gün bazlı rotasyon; ardışık gün aynı temayı almaz,
post ile story aynı gün farklı tema alır.

| Tema | Palet | Arka plan |
|---|---|---|
| `kufi` | bordo + altın | geometrik kûfî örgü |
| `samua` | şamua kâğıt | mürekkep lekeleri |
| `nur` | siyah + altın | ışık huzmeleri |
| `editorial` | beyaz + kırmızı | editoryal ızgara |
| `arabesk` | krem + yeşil | arabesk çizgi animasyonu |
| `zumrut` | zümrüt yeşili | yumuşak dalgalar |
| `lacivert` | lacivert gece | toz zerrecikleri |
| `tahta` | ders tahtası | tebeşir dokusu |

Aynı tema iki kez düşse bile hareket farklı olur: `themes.variant()` gün
tohumundan arka plan hızı, açı, hizalama, giriş animasyonu üretir.

---

## Ses tasarımı

`src/audio.py` — hepsi numpy ile sentezlenir, dosya kullanılmaz.

| | |
|---|---|
| `whoosh()` | sahne geçişi — süpürülen filtreden geçen gürültü |
| `impact()` | vurgu — düşen sinüs + tık |
| `chime()` | terim belirince yumuşak çan |
| `riser()` | kapanış öncesi gerilim |
| `page()` | kitap sahnelerinde sayfa sesi |
| `ambience()` | oda dokusu — **kapalı** (`audio.ambience: false`); hafif bir uğultu bırakıyordu |

**Müzik yok, arka plan uğultusu yok.** Yalnız geçiş ve vurgu efektleri kullanılıyor.
Oda dokusunu geri istersen `brand.yaml` → `audio.ambience: true`.

Seslendirme konuşurken efektler otomatik kısılıyor (`audio.duck`).
Çıkış seviyesi ffmpeg `loudnorm` ile Instagram hedefine (-14 LUFS) normalize ediliyor.

---

## Nasıl çalışıyor

```
calendar.yaml
   ↓  scenes.build()      vo → Google TTS → gerçek süre → sahne zamanlaması + altyazı
   ↓  audio.Mixer()       efektler + ortam + ducking → tek wav
   ↓  render.build_html() Jinja şablonu + tema + varyant → tek HTML
   ↓  Playwright          window.seek(t) ile her kare sabitlenir, ekran görüntüsü
   ↓  ffmpeg              kareler + ses → mp4 (loudnorm, yuv420p)
out/gun-NN/
```

Animasyonlar CSS'te **mutlak gecikmeyle** tanımlı. `window.seek(t)` bütün
animasyonları durdurup o ana sabitliyor — yani render gerçek zamandan bağımsız
ve her çalıştırmada birebir aynı sonucu veriyor.

Metin taşarsa şablon sahneyi otomatik küçültüyor (`zoom`), o yüzden uzun
başlıklar kadrajı bozmuyor.

---

## Bilinen sınırlar

- **Altyazı zamanlaması** karakter sayısına göre orantılı dağıtılıyor, kelime
  kelime değil. Pratikte isabetli; tam hassasiyet gerekirse Google TTS
  `v1beta1` + SSML `<mark>` ile gerçek zaman damgasına geçilebilir
  (`src/scenes.py` içinde not düşüldü).
- Ses **mono**. Stereo genişlik gerekirse `audio.py` içinde mikser iki kanala
  çıkarılır.
- Bir video postu ~2-3 dakikada render oluyor (kare kare ekran görüntüsü).
  30 günün tamamı ~50 dakika.
- TTS çıktıları `.cache/tts/` altında saklanıyor; `vo` metnini değiştirmedikçe
  tekrar istek atılmıyor.
