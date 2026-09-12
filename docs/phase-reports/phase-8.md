# Phase 8 ara raporu — Dayanıklılık

## Durum

Profiling/stress altyapısı tamamlandı. Gerçek donanımda kesintisiz 72 saat koşu
henüz yapılmadığından Phase 8 kabulü açık tutulmaktadır.

## Yapılan değişiklikler

- Harici PID izleyen, sabit-bellekli `ProcessStabilityMonitor` eklendi.
- Online RSS regression, CPU ortalama/peak ve thread büyüme ölçümleri eklendi.
- Tek atomik JSON raporuyla disk kullanımını sabit tutan writer eklendi.
- Windows service PID keşfi yapan PowerShell ve platform-nötr shell script'i eklendi.
- 100 reconnect, 250 poisoned-gate tekrar, 10.000 latest-frame baskısı, bounded
  event queue pressure ve dört-worker/80-write SQLite contention testleri eklendi.
- On uygulama start/stop döngüsünde managed worker/thread temizliği doğrulandı.

## Kısa doğrulama sonucu

Gerçek Garage LPR process'i üzerinde üç saniyelik idle smoke ölçümünde:

- RSS başlangıç/son: 226.754.560 byte / 226.754.560 byte
- RSS büyümesi ve eğimi: 0 / 0 byte-saat
- Ortalama/peak CPU: %0,17 / %0,20
- Thread başlangıç/son: 9 / 9
- Sonuç: `PASSED`

Bu kısa sonuç yalnızca harness'ın çalıştığını kanıtlar; uzun dönem stabilite kanıtı
değildir.

## Bilinen eksik

Gerçek RTSP kamera, gerçek ONNX modelleri ve seçilen fiziksel gate adaptörüyle 72
saatlik kesintisiz rapor ile operasyonel kontrol listesi henüz üretilmemiştir.

## Fazı kapatma koşulu

`runtime/soak/latest.json` final durumu `PASSED`, event/queue/health kontrolleri
temiz ve yanlış gate OPEN sayısı sıfır olmalıdır.
