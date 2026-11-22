# Otomatik Instagram yayını — kurulum

Her gün belirlediğin saatte o günün story'si ve postu kendiliğinden paylaşılır.
Bilgisayarın açık olmasına gerek yok; iş GitHub'ın sunucularında dönüyor.

## Neden dosyalar bir yerde "yayında" olmak zorunda

Instagram'a dosya yükleyemiyorsun. Bunun yerine Instagram'a bir **internet adresi**
veriyorsun, o adresteki videoyu Meta'nın sunucusu kendisi indiriyor.

Bilgisayarındaki `C:\Projects\...\post.mp4` dosyasının internet adresi yok —
Meta'nın sunucusu oraya ulaşamaz. Dükkândaki bilgisayar da işe yaramaz: sabit bir
adres, alan adı ve sertifika kurmak, modemi dışarı açmak gerekir; bu hem zahmetli
hem güvenlik açısından gereksiz bir risk.

Çözüm: videolar zaten GitHub'da duracak (iş akışı orada çalışıyor), GitHub da her
dosyaya herkese açık bir adres veriyor. Ek servis, ek ücret yok.

> Bunun bedeli: depo **herkese açık** olacak. İçindeki videolar zaten Instagram'da
> yayımlanacak, sorun değil. Ama yayınlanmamış günlerin metinleri de görünür olur.
> İstemezsen söyle, medyayı ayrı bir depoya alıp üretim tarafını gizli tutarız.

---

> **Durum:** bu kurulum 22 Kasım 2026'da tamamlandı. Depo
> [tahacelik21/sifa-instagram](https://github.com/tahacelik21/sifa-instagram),
> yayın 1 Aralık 2026'da başlıyor. Aşağısı baştan kurmak ya da hatırlamak için.

## 1. Instagram hesabı

Hesap **profesyonel** olmalı (İşletme ya da Kreatör):
Instagram → Ayarlar → Hesap türü ve araçlar → Profesyonel hesaba geç.

Facebook Sayfası bağlamaya gerek yok.

## 2. Meta uygulaması ve token

1. [developers.facebook.com/apps](https://developers.facebook.com/apps) → **Create app**
2. Kullanım amacı: **Other** → tür: **Business**
3. Ürünlerden **Instagram** → **Set up**
4. Sol menüden **API setup with Unified login**
5. **Business portfolio** bağla (yoksa orada oluşturulur, ücretsiz)
6. **1. Configure your app** → **Create new configuration**
   - Login variation: **General**
   - Business assets: Instagram hesabını seç
   - İzinler: `instagram_basic` ve `instagram_content_publish` yeter
7. **App roles → Roles** → Instagram hesabına **Instagram Tester** rolü ver.
   Davet Instagram tarafından kabul edilir:
   Instagram → Ayarlar → Website permissions → Tester invites
8. **2. Generate access tokens** → Instagram hesabını ekle → token üret
   - Çıkan token → `IG_TOKEN`
   - Aynı ekrandaki **Instagram user ID** → `IG_USER_ID`

Bu kurulumda token **sistem kullanıcı token'ı (SUAT)**; süresi dolmuyor, yenilemek
gerekmiyor. Uygulama **Development** modunda kalabilir — tester rolü verilmiş kendi
hesabına yayın yapmak için App Review gerekmiyor.

## 3. GitHub deposu

```bash
git init
git add .
git commit -m "Şifa Yayınevi içerik üretimi + Instagram yayını"
```

GitHub'da **public** bir depo aç (örn. `sifa-instagram`), sonra:

```bash
git remote add origin https://github.com/tahacelik21/sifa-instagram.git
git push -u origin main
```

`.env` dosyası `.gitignore`'da — Google TTS anahtarı depoya **girmez**, öyle kalsın.

## 4. Secrets

Depo → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**:

| Ad | Değer |
|---|---|
| `IG_USER_ID` | 2. adımdaki Instagram user ID |
| `IG_TOKEN` | 2. adımdaki token |
| `MEDIA_BASE` | `https://raw.githubusercontent.com/tahacelik21/sifa-instagram/main/out` |

## 5. Başlangıç tarihi

`content/yayin.yaml`:

```yaml
baslangic: 2026-12-01
```

Bu tarihte `gun-01`, ertesi gün `gun-02` paylaşılır.

Saatler `.github/workflows/yayin.yml` içinde, **UTC** olarak:

```yaml
- cron: "0 9 * * *"     # 12:00 TR — story
- cron: "0 16 * * *"    # 19:00 TR — post
```

Türkiye saati = UTC + 3. Saati değiştireceksen 3 çıkarıp yaz.

## 6. Deneme

Depo → **Actions** → **Instagram yayını** → **Run workflow**:
`deneme` işaretli kalsın, `gun` = 1, `slot` = post.

Hiçbir şey paylaşmaz; dosyaların adreslerini kontrol eder, boyutlarını ve
açıklama uzunluğunu yazar. Hepsi "açık" diyorsa sistem hazır.

Gerçekten paylaşmak için aynı ekranda `deneme` işaretini kaldır.

Yerelde de çalışır:

```bash
python -m src.publish --slot post --gun 1 --deneme
```

---

## Yeni içerik eklerken

```bash
python -m src.build --days 31-40
git add out content
git commit -m "31-40. günler"
git push
```

Push ettiğin an yayın sırasına girer.

---

## Bilinen sınırlar

- **Story'de açıklama yok.** Instagram API'si story'ye metin, bağlantı, anket ya da
  konum çıkartması koymaya izin vermiyor. Videonun içindeki yazılar görünür.
- **Video postlar Reels olarak gidiyor.** API'de akış videosu için başka yol yok.
  Videolarımız 1:1; akışta 1:1 görünür, Reels sekmesinde kenarları boşluklu durur.
  İstersen post videolarını 4:5'e çeviririz, akışta daha çok yer kaplar.
- Günde en fazla 50 paylaşım (Meta'nın belgelerinde 100 rakamı da geçiyor, net değil).
  Günde 2 paylaşım yaptığımız için sınır uzak.
- Takvim 30. günde biter; iş akışı o gün "takvim bitti" yazıp durur, hata vermez.
- Depo her ay ~300 MB büyüyor. Bir yıl sonra geçmişi temizlemek ya da medyayı
  ayrı bir depoya taşımak gerekebilir; o noktaya gelince hallederiz.
- GitHub, 60 gün boyunca hiç hareket görmeyen depolarda zamanlanmış işleri
  durduruyor. Ayda bir içerik push ettiğin sürece sorun olmaz; uzun ara verirsen
  Actions sekmesinden iş akışını tekrar etkinleştirmen gerekebilir.
- Instagram paylaşımı reddederse iş akışı kırmızı yanar ve sebebi log'a yazar.
  GitHub bunu e-posta ile bildirir.
