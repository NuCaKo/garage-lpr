# Phase 6 raporu — Operasyon

## Yapılan değişiklikler

- Inference yolunu bloklamayan, kapasitesi sınırlı ve tek worker kullanan audit
  event servisi eklendi.
- Recognition ve access/gate eventleri SQLite repository katmanına bağlandı;
  yalnızca kalıcılaşan eventler bounded WebSocket üzerinden yayınlanıyor.
- Detection event sampling, structured event metadata ve kontrollü DB retry
  davranışı eklendi.
- Dashboard'a CPU, RAM, process RSS, thread sayısı, disk, inference ve gate
  metrikleri; ayrıca ayrı System Health sayfası eklendi.
- Event listesi server-side filtreleme/sayfalama ve en fazla 50 satırlık canlı
  güncelleme ile eklendi.
- Snapshot kaydı varsayılan kapalı olacak şekilde yalnızca önemli sonuçlara
  sınırlandı; atomik dosya yazımı ve gün bazlı retention sağlandı.
- Event tablolarına varsayılan 90 günlük, en fazla günde bir çalışan retention
  eklendi. Snapshot ve event retention merkezi ayarlardan değiştirilebilir.
- Disk doluluk eşikleri health aggregation'a bağlandı; structured log rotation
  ve secret redaction mevcut log altyapısıyla korunuyor.

## Oluşturulan ana dosyalar

- `backend/src/garage_lpr/events/{domain,broker,service,recorder}.py`
- `backend/src/garage_lpr/database/repositories/events.py`
- `backend/src/garage_lpr/storage/{contracts,local,service}.py`
- `backend/src/garage_lpr/health/resources.py`
- `backend/src/garage_lpr/api/routes/{events,metrics}.py`
- `backend/src/garage_lpr/api/schemas/{events,metrics}.py`
- `frontend/src/pages/{Events,SystemHealth}.tsx`
- `backend/tests/{test_events,test_event_recorder,test_snapshot_storage}.py`

## Mimari kararlar

- Audit persistence ayrı bir process/thread havuzu yerine tek bounded worker'da
  tutuldu. Böylece ordering korunurken thread ve RAM büyümesi sınırlandı.
- Canlı event, DB yazımından sonra yayınlanır; UI'da görülen olay audit kaydıyla
  ilişkilidir.
- Plate detection olayları örneklenir, nihai kararlar örneklenmez. Bu seçim hem
  audit doğruluğunu hem düşük disk yazımını korur.
- Kaynak ölçümleri için polling thread'i kurulmadı; UI isteğine bağlı tek ölçüm ve
  çakışmayan recursive timeout kullanıldı.
- Snapshot dosya yolları platform bağımsızdır ve dosya yazımı geçici dosyadan
  atomik replace ile tamamlanır.

## Doğrulama

- Backend: 74 test geçti.
- Ruff: temiz.
- mypy: 102 source file içinde hata yok.
- Frontend ESLint ve production Vite build: başarılı.
- Çalışan servis üzerinde `/health`, `/metrics/resources`, `/events` ve Vite giriş
  sayfası HTTP smoke testleri başarılı.
- Bu geliştirme oturumunda bağlı bir uygulama içi/harici browser bulunmadığı için
  piksel düzeyinde görsel QA çalıştırılamadı. Responsive yapı, erişilebilir durum
  metinleri ve bounded event tablosu statik kontrollerle doğrulandı.

## Bilinen eksikler

- UI henüz authentication/authorization arkasında değildir; güvenilir yerel ağ
  sınırı Phase 7'ye kadar korunmalıdır.
- Snapshot dosyaları Events ekranından servis edilmez. Yetkili snapshot görüntüleme
  endpoint'i authentication ile birlikte Phase 7'de eklenmelidir.
- Gerçek kamera/model/gate ile saha kalibrasyonu ve uzun süreli soak testi Phase 8
  kapsamındadır.
- HTTP, MQTT ve Serial gate adaptörleri saha cihazı seçildikten sonra eklenmelidir.

## Sonraki faz

Phase 7: ilk kurulum sihirbazı, admin hesabı, parola hashing, session/API
authentication, rol bazlı gate yetkisi, CSRF/CORS sertleştirme, Windows native
service kurulumu ve production paketleme.
