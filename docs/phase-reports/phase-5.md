# Phase 5 raporu — Fail-safe gate orchestration

## Yapılan değişiklikler

- `GateController` sözleşmesinin ilk çalışan adaptörü `MockGateController` eklendi.
- Pulse durumu timer veya polling oluşturmadan monotonic deadline ile uygulandı.
- Tek worker ve kapasite-1 komut kuyruğu kullanan `GateManager` eklendi.
- Adapter timeout'unda yeni komutları bloke eden executor poisoning uygulandı.
- Kamera sağlığı, maintenance, simulation ve access-rule kontrollerini tek noktada
  uygulayan `GateOrchestrator` inference akışına bağlandı.
- Kamera özel kuralları fallback kurallardan önce seçen; belirsizlikte açmayan
  access-rule resolver eklendi.
- Gate controller ve access rule CRUD/test API'leri ile yönetim ekranları eklendi.
- Gate başarı, hata/engel ve simulation sayaçları dashboard'a bağlandı.

## Oluşturulan başlıca dosyalar

- `backend/src/garage_lpr/gate/mock.py`
- `backend/src/garage_lpr/gate/manager.py`
- `backend/src/garage_lpr/gate/orchestration.py`
- `backend/src/garage_lpr/gate/orchestration_factory.py`
- `backend/src/garage_lpr/access/rules.py`
- `backend/src/garage_lpr/api/routes/gates.py`
- `backend/src/garage_lpr/api/routes/access_rules.py`
- `frontend/src/pages/GateControllers.tsx`
- `frontend/src/pages/AccessRules.tsx`
- Mock gate, timeout, orchestration ve gate/access-rule API testleri

## Mimari kararlar

- Manuel gate-open endpoint'i eklenmedi. Böylece Phase 7 authentication öncesinde
  ağ üzerinden fiziksel komut yüzeyi oluşmadı.
- Simulation modu rule routing'i test eder fakat controller'a hiçbir metot çağrısı
  göndermez.
- Generic adapter timeout'u için komut başına thread yerine tek daemon worker
  kullanılır. Bloklanan adapter executor'ı poison ederek komut tekrarını engeller
  ve runtime health durumunu `UNAVAILABLE` yapar.
- Phase 5 yalnızca Mock adapter'ı kabul eder. HTTP/MQTT/Serial konfigürasyon
  sözleşmeleri gerçek saha cihazı bilindikten sonra adapter bazında tasarlanacaktır.
- Recognition cooldown'u gate routing'den önce rezerve olmaya devam eder. Gate/rule
  hatasında kısa süreli tekrar denemesini engellemek bilinçli fail-safe tercihtir.

## Doğrulama

- 65 backend testi geçti.
- Ruff ve strict mypy kontrolleri geçti.
- Frontend ESLint ve production build geçti.
- Simulation'ın controller open çağrısını sıfırda tuttuğu doğrulandı.
- Timeout sonrası aynı executor'ın ikinci komutu reddettiği doğrulandı.
- Exact-camera/fallback önceliği ve belirsiz rule durumunun fail-closed olduğu
  doğrulandı.

## Bilinen eksikler

- HTTP, MQTT ve Serial controller adaptörleri henüz yoktur.
- Recognition/access event'lerinin database kalıcılığı ve WebSocket yayını Phase 6
  kapsamındadır; Phase 5 sonuçları structured log ve bounded metrik üretir.
- Controller credential şifreleme akışı fiziksel adapter seçilene kadar
  etkinleştirilmemiştir.
- Gerçek röle cihazıyla timeout, pulse ve elektriksel fail-safe saha testi yoktur.
- UI için otomatik tarayıcı görsel regresyon testi henüz bulunmuyor.

## Sonraki faz

Phase 6'da event service, recognition/access audit kayıtları, WebSocket canlı olay
akışı, snapshot retention ve genişletilmiş operasyon/health dashboard'u
uygulanacaktır.
