# Uygulama fazları

## Phase 1 — Foundation (tamamlandı)

Repository, architecture, merkezi config, SQLite/Alembic, temel API ve temel UI.

## Phase 2 — Kamera (tamamlandı)

RTSP adapter, kapasite-1 latest-frame buffer, capture FPS limiti,
reconnect/backoff, connection test, on-demand canlı preview ve normalize ROI
editörü tamamlandı. Donanım olmadan deterministic reconnect testi eklendi;
kayıtlı video pipeline'ı detector ile birlikte Phase 3'te bağlanacaktır.

## Phase 3 — Algılama ve OCR (tamamlandı)

ONNX Runtime provider seçimi, hafif plate detector, crop-only OCR, Türk plakası
normalizasyonu, latency ve throughput metrikleri tamamlandı. Aynı pipeline'ı
kullanan sequential offline video modu ve model tensor sözleşmesi doğrulamaları
eklendi. Gerçek saha modeli/verisiyle doğruluk kalibrasyonu Phase 8 öncesinde
ayrıca yapılacaktır.

## Phase 4 — Karar (tamamlandı)

Temporal validation, hafif IoU/centroid tracker, authorization service ve plaka /
global cooldown tamamlandı. Yetkili araç CRUD API/UI eklendi. Tek-frame sonucu
hiçbir zaman erişim kararı üretmez; maintenance açıkken gate-ready karar oluşmaz.
Kamera–gate `access_rules` bağlama işi Gate adapter ile birlikte Phase 5'e bırakıldı.

## Phase 5 — Gate (tamamlandı)

Timer oluşturmayan MockGateController, tek bounded command worker, timeout sonrası
fail-safe poisoning, camera/maintenance/simulation guard, exact-camera/fallback
access-rule çözümleme ve gate/rule yapılandırma UI tamamlandı. Manuel open API
özellikle eklenmedi. HTTP, MQTT ve serial adapter'lar saha gereksinimine göre ayrı
eklenir.

## Phase 6 — Operasyon (tamamlandı)

Event service, WebSocket, dashboard metrikleri, health aggregation, snapshot
retention ve log operasyonları tamamlandı. Audit yazımı inference yolunu bloklamayan
tek bounded worker üzerinden yürür; yalnızca kalıcılaşan eventler canlı yayınlanır.
Event ve snapshot retention UI'dan yönetilir, kaynak ölçümleri yalnızca düşük
frekanslı API okumasında örneklenir.

## Phase 7 — Güvenlik ve deployment (tamamlandı)

İlk admin kurulum akışı, Argon2id password hashing, veritabanı tabanlı opaque
oturum, admin authorization, login rate limit, CSRF/CORS/WebSocket origin
sertleştirme, production UI sunumu ve native Windows service kurulumu tamamlandı.
Windows 10/11 üzerinde gerçek servis kurulumu saha makinesinde ayrıca
doğrulanacaktır.

## Phase 8 — Dayanıklılık (uygulama tamamlandı, 72 saat koşusu bekliyor)

CPU/RAM profiling, queue/latency ölçümü, reconnect soak test, gate failure test,
database contention testi ve en az 72 saatlik uzun çalışma doğrulaması. Sabit
bellekli process monitorü ile deterministik reconnect, gate poison, bounded queue,
latest-frame pressure, lifecycle restart ve SQLite WAL contention testleri hazırdır.
Faz, gerçek kamera/model/gate konfigürasyonunda 72 saatlik rapor `PASSED` olmadan
tamamlandı sayılmayacaktır.
