# Phase 1 raporu

## Yapılan değişiklikler

- Yeni ve bağımsız Git repository oluşturuldu.
- Bootstrap ve runtime config ayrıldı; UI ayarları SQLite'da saklanıyor.
- SQLite WAL, foreign keys, busy timeout ve kısa session lifecycle tanımlandı.
- Zorunlu sekiz tablo için SQLAlchemy model ve Alembic initial migration eklendi.
- JSON rotating log, health aggregation ve versioned temel API eklendi.
- Simulation + maintenance açık gelen güvenli yönetim dashboard'u oluşturuldu.
- Kamera, detector, OCR, gate ve snapshot storage sınırları `Protocol` olarak ayrıldı.
- Graphify tasarım kaydı, güncelleme script'i ve Git hook entegrasyonu eklendi.

## Önemli dosyalar

- `backend/src/garage_lpr/main.py`: process lifecycle ve application composition.
- `backend/src/garage_lpr/config/`: merkezi validated config.
- `backend/src/garage_lpr/database/`: model, session, repository ve migration.
- `backend/src/garage_lpr/*/contracts.py`: değişebilir dış sistem sınırları.
- `frontend/src/App.tsx`: hafif operasyon kabuğu.
- `docs/ARCHITECTURE.md`: hedef runtime ve fail-safe veri akışı.

## Mimari kararlar

- Native Windows kurulumu birinci sınıf; Docker zorunlu değil.
- AI/OpenCV bağımlılıkları Phase 1'e dahil edilmedi.
- Gate trigger endpoint'i authentication gelmeden oluşturulmadı.
- UI health polling 10 saniye; canlı olaylar ileride WebSocket kullanacak.
- Runtime varsayılanı kapıyı açamayacak şekilde simulation + maintenance.

## Bilinen eksikler

- RTSP capture, preview, ROI ve reconnect henüz yok (Phase 2).
- Detector/OCR/model dosyası ve GPU provider seçimi yok (Phase 3).
- Authorization, temporal validation, tracking ve cooldown yok (Phase 4).
- Mock/fiziksel gate implementation yok (Phase 5).
- Kullanıcı modeli mevcut olsa da login/password hashing/auth henüz yok (Phase 7).
- Frontend backend tarafından tek-port production artifact olarak servis edilmiyor.
- Şifreleme anahtarı yönetimi tamamlanmadan credential yazma API'si açılmayacak.

## Doğrulama

- Backend unit/integration: 8 test, %79 toplam kapsam. Çalışan Phase 1 kodu yüksek
  kapsamda; sonraki faz sözleşmeleri implementation olmadığı için ölçümde 0 görünür.
- Ruff lint + format: başarılı.
- Mypy strict: başarılı.
- Frontend TypeScript + ESLint + production build: başarılı.

## Sonraki faz

Phase 2: RTSP adapter ve sadece en yeni frame'i tutan bounded buffer ile başlanacak;
ardından deterministic reconnect testi, connection-test API ve normalize ROI UI
eklenecek.
