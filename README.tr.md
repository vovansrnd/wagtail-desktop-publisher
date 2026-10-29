# wagtail-desktop-publisher

**Kimliği doğrulanmış API istekleriyle masaüstünden Wagtail’e Markdown makaleleri ve yerel görseller yayımlar. CLI ve masaüstü arayüzü sunar, yerel Markdown kaynaklarını korur ve değişmeyen içeriği hash ile atlar.**

[English](README.md) · [Русский](README.ru.md) · [Deutsch](README.de.md) · [Español](README.es.md) · [Français](README.fr.md) · [Italiano](README.it.md) · [Português (Brasil)](README.pt-BR.md) · [Nederlands](README.nl.md) · [Polski](README.pl.md) · [Türkçe](README.tr.md) · [简体中文](README.zh-CN.md) · [日本語](README.ja.md) · [한국어](README.ko.md)

## Temel özellikler

- Markdown ve YAML frontmatter’dan taslak oluşturma/güncelleme veya sayfa yayımlama.
- Yerel görselleri yükleme ve içerik olarak aynı dosyaları yeniden kullanma.
- Wagtail sayfa kimliklerini, eşitleme durumunu ve meta verileri frontmatter’da tutma.
- Betikler/SSH için CLI ve etkileşimli yazım için GUI.

## Gereksinimler ve uyumluluk

- Bildirilen bağımlılıklar: `requests >= 2.28; python-frontmatter >= 1.0; markdown >= 3.5; customtkinter >= 5.2`.
- Python, Django ve Wagtail uyumluluğu birlikte kontrol edilmelidir. Paketin asgari bağımlılığı tüm sürümlerin desteklendiğini kanıtlamaz.

Masaüstü istemcisi `requests`, `python-frontmatter`, `markdown` ve `customtkinter` kullanır; yayın yapan bilgisayara Wagtail kurulması gerekmez. Sunucu, Wagtail API v3 üzerinden kimlik doğrulamalı yazmayı desteklemelidir. Özgün belgeler Wagtail 7.0+ ve 8.0 ile testten bahseder; gelecekteki sürümler garanti edilmez.

## Kurulum

Paketi Wagtail projenizle aynı sanal ortama yükleyin:

```bash
pip install wagtail-desktop-publisher
```

Diğer proje bağımlılıklarını koruyarak uygulamaları bu sırayla ekleyin:


## İlk yapılandırma

Başlangıç için en küçük örnek aşağıdadır. Model adlarını, API alanlarını ve URL’leri yapılandırmanıza uyarlayın.

```bash
wagtail-publisher init --url https://example.com/api/v3 --token YOUR_TOKEN --site example.com
wagtail-publisher publish articles/2026/example/index.md --parent 42
# Add --publish to publish immediately; test with a draft first.
wagtail-publisher status articles/
```

Frontmatter genellikle `title`, sabit bir `slug`, `excerpt`, `date` ve isteğe bağlı `year`, `tags` ile kategori kimliklerini içerir. Kullanılabilir alanlar sayfa modelinin API şemasına bağlıdır. `/api/v3/publisher-images/` standart Wagtail’de bulunmayan özel bir endpoint’tir; sunucuda kaydedin veya güvenli bir alternatif endpoint yapılandırın.




## Önemli ayarlar ve davranış

Bu dizindeki İngilizce README, tüm seçenek tablolarını ve genişletilmiş örnekleri içeren temel başvuru belgesidir. Bu çeviri pratik kurulumu ve temel güvenlik uyarılarını kapsar; gelişmiş ayarları değiştirmeden önce İngilizce başvuruya bakın.

Tam ayar listesi için [İngilizce README](README.md) dosyasına bakın.

### Önemli notlar

Hedef site API v3 ve `/api/v3/publisher-images/` yolunu sunmalıdır; bu yükleme uç noktası her Wagtail kurulumunda varsayılan olarak yoktur. En az yetkili token kullanın ve toplu eşitlemeyi kopya üzerinde sınayın.

## Güvenlik ve işletim

- Bağımlılıkları güncel tutun. Kullanıcı HTML’si için belirlenen temizleme/görüntüleme yolunu kullanın; kaydedilmiş yorumları veya forum gönderilerini koşulsuz `|safe` ile göstermeyin.
- Geçişleri ve izinleri normal, kısıtlı, moderatör ve yönetici hesaplarıyla kontrol edin.
- Çoklu site kurulumlarında yapılandırılmış her alan adını ve bilinmeyen bir hostu sınayın. Site bulunamazsa sorgu tüm sitelerdeki kayıtları kapsayacak şekilde genişlememelidir.
- API tokenlarını, SMTP kimlik bilgilerini ve özel URL’leri gizli kabul edin. Bunları Git’e eklemeyin veya herkese açık hata raporlarında paylaşmayın.
- Geçişler, toplu taşıma, içe aktarma veya ilk toplu yayın öncesinde veritabanını ve medya dosyalarını yedekleyin. Önce staging ortamında deneyin.

## Önerilen kombinasyonlar

- Yükleme uç noktası bu modeli kullanıyorsa `wagtail-image-directories`, `year/slug` düzeni için en iyi tamamlayıcıdır.
- Markdown yayını için Prose seçicisi gerekli değildir.

## Doğrulama kontrol listesi

- [ ] Aday sürümü staging ortamına kurun; Python, Django, Wagtail ve veritabanı sürümlerini kaydedin.
- [ ] `python manage.py check` ve paket geçişlerini çalıştırın.
- [ ] Ana akışı normal ve kısıtlı hesapla sınayın.
- [ ] Kayıtları, erişimi, önbelleği, yedeklemeyi ve geri yüklemeyi kontrol edin.

Arşiv statik sözdizimi ve paketleme kontrollerini geçer; ancak bu ortamda tam Django/Wagtail çalışma zamanı entegrasyonu test edilmedi. Aşağıdaki listeyi tüm sürümlerin test edildiğinin kanıtı değil, yayın öncesi zorunlu kontrol olarak görün.

## Sorun giderme

Akış çalışmıyorsa uygulama ayarlarını, geçişleri, URL sırasını, kullanıcı izinlerini ve Django kayıtlarını kontrol edin. Paket sürümünü ve örneği İngilizce README ile karşılaştırın.

## Lisans ve destek

MIT. Bu denetimde herkese açık depo adresi doğrulanamadı. GitHub URL’sini tahmin etmeyin; PyPI proje bağlantılarını kontrol edin.

