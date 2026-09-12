# Garage LPR stability test

Bu prosedür Phase 8'in gerçek saha kabul testidir. Kısa unit/stress testleri 72
saatlik sonucu ikame etmez.

## Ön koşullar

- Production UI build ve Windows service kurulmuş olmalı.
- Gerçek saha modeli yüklenmiş, ROI ve detection FPS ayarlanmış olmalı.
- Önce Mock gate + Simulation Mode ile uçtan uca event akışı doğrulanmalı.
- Başlangıçta `maintenance_mode=true` tutulmalı; gerçek gate yalnızca ayrıca
  planlanan kontrollü aralıkta etkinleştirilmeli.
- Test başlangıç saati, uygulama sürümü, model hash'i ve saha konfigürasyonu kayıt
  altına alınmalı.

## Çalıştırma

Yönetici PowerShell:

```powershell
.\scripts\soak-test.ps1 -DurationHours 72
```

Linux/macOS geliştirme ortamında hedef PID açıkça verilir:

```bash
./scripts/soak-test.sh PID 72
```

Monitor varsayılan olarak 60 saniyede bir örnek alır, ilk 10 dakikayı warmup sayar
ve yalnızca `runtime/soak/latest.json` dosyasını atomik olarak değiştirir. Bellekte
örnek dizisi veya diskte büyüyen örnek logu tutmaz.

## 72 saatlik kontrollü senaryo

1. Saat 0–8: kamera bağlı, trafik yok/az; idle baseline.
2. Saat 8–32: normal kamera akışı ve gerçekçi araç trafiği; Simulation Mode açık.
3. Saat 32–40: kontrollü kamera ağ kesintileri ve geri dönüşleri; capped reconnect
   ve tek camera worker doğrulanır.
4. Saat 40–64: gündüz/gece, yetkili/yetkisiz ve hatalı OCR örnekleri; yanlış OPEN
   üretilmediği eventlerden kontrol edilir.
5. Saat 64–72: Mock gate unavailable/timeout senaryosu ve servis graceful restart
   testi. Restart ayrı soak koşusu başlatır; önceki PID'nin `TARGET_EXITED` sonucu
   kaybolmamalıdır.

Restart zorunlu değilse tek kesintisiz 72 saat koşu tercih edilir. Restart testini
ayrı kısa koşuda yapmak, ana 72 saatlik PID raporunun kesintisiz kalmasını sağlar.

## Otomatik kabul eşikleri

Warmup sonrasındaki ölçümler için varsayılanlar:

- Son RSS − baseline RSS: en fazla 128 MiB
- Lineer RSS eğimi: en fazla 4 MiB/saat
- Peak thread − baseline thread: en fazla 2
- Hedef process bütün koşu boyunca mevcut olmalı

Eşik aşılırsa final `status=FAILED`; process kapanırsa `TARGET_EXITED`; izin
kaybolursa `TARGET_UNAVAILABLE`; kullanıcı durdurursa `INTERRUPTED` yazılır.

## Operasyonel kabul kontrolü

Process raporuna ek olarak test sonunda şunlar kaydedilmelidir:

- Event worker `dropped=0` ve `failed=0` (planlı pressure testi hariç)
- Frame queue backlog yok; latest-frame replaced sayısı yük altında artabilir
- Detection FPS yapılandırılmış tavanı aşmıyor
- Kamera reconnect sonrasında tek worker ile `CONNECTED` oluyor
- Gate timeout sonrasında gerçek OPEN tekrarlanmıyor
- Unauthorized/low-confidence/maintenance durumlarında OPEN yok
- Log rotation ve snapshot retention sınırları korunuyor
- SQLite integrity check temiz ve beklenmeyen lock hatası yok

Faz ancak otomatik rapor `PASSED` ve operasyonel kontrol listesi temiz olduğunda
tamamlandı olarak işaretlenmelidir.
