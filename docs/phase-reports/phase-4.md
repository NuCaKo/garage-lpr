# Phase 4 raporu — Güvenli karar

## Yapılan değişiklikler

- Bounded IoU tracker ile kamera bazlı kısa ömürlü track kimlikleri eklendi.
- Confidence, format, tekrar sayısı ve zaman penceresini birlikte kullanan temporal
  plate validator implemente edildi.
- Araç aktifliği, tarih, haftanın günü, saat aralığı ve gece yarısını aşan
  programları değerlendiren authorization service eklendi.
- Atomik plaka/global cooldown manager ve maintenance engeli eklendi.
- Recognition orchestration inference worker'a bağlandı; aynı track yalnızca bir
  karar üretiyor.
- Yetkili araç repository, CRUD API ve hafif yönetim ekranı eklendi.
- Dashboard'a aktif track, bekleyen doğrulama, son yetki ve cooldown sayaçları
  bağlandı.

## Oluşturulan başlıca dosyalar

- `backend/src/garage_lpr/recognition/tracker.py`
- `backend/src/garage_lpr/recognition/temporal.py`
- `backend/src/garage_lpr/recognition/service.py`
- `backend/src/garage_lpr/access/authorization.py`
- `backend/src/garage_lpr/access/cooldown.py`
- `backend/src/garage_lpr/database/repositories/vehicles.py`
- `backend/src/garage_lpr/api/routes/vehicles.py`
- `frontend/src/pages/Vehicles.tsx`
- Phase 4 tracker, temporal, authorization, cooldown, recognition ve API testleri

## Mimari kararlar

- Ağır appearance tracker yerine kısa garaj geçişleri için IoU tracker kullanıldı.
- Temporal state track'e bağlandı; global OCR geçmişi veya benzerlik tablosu
  tutulmadı.
- DB yalnızca temporal doğrulamadan sonra sorgulanır; başarısız DB sorgusu
  fail-safe `UNAUTHORIZED` sonucu üretir.
- Authorized sonuç fiziksel komut değil, yalnızca `AUTHORIZED_PENDING_GATE`
  niyetidir. Gate adapter henüz çağrılamaz.
- Cooldown karar anında rezerve edilir. Gelecekte gate hatasında dahi kısa süreli
  tekrar komutunu engellemesi fail-safe tercihidir.

## Doğrulama

- 55 backend testi geçti.
- Ruff ve strict mypy kontrolleri geçti.
- Frontend ESLint ve production build geçti.

## Bilinen eksikler

- Kamera, araç ve gate controller eşleştiren `access_rules` Phase 5'te aktif
  kullanılacaktır; mevcut MVP authorization listesi site genelidir.
- Mock/fiziksel gate çağrısı ve simulation event'i Phase 5 kapsamındadır.
- Recognition/access event kalıcılığı ve WebSocket yayını Phase 6 kapsamındadır.
- Gerçek kamera trafiğinde IoU/confidence/window kalibrasyonu henüz yapılmadı.
- UI için otomatik tarayıcı görsel regresyon testi bulunmuyor.

## Sonraki faz

Phase 5'te `GateController` sözleşmesi, zorunlu `MockGateController`, simulation
guard, access-rule binding ve timeout'lu gate orchestration uygulanacaktır. Tek
fiziksel open yolu bu orchestration servisi olacaktır.
