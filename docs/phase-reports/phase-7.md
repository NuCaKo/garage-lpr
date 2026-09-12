# Phase 7 raporu — Güvenlik ve deployment

## Yapılan değişiklikler

- Tek kullanımlık ilk-admin setup ve login/logout/me API akışı eklendi.
- Admin parolaları Argon2id ile hashleniyor; persistent session ve CSRF token
  digest'leri için Alembic migration eklendi.
- Bütün operasyon REST API'leri ve canlı event WebSocket'i admin rolüne kapatıldı.
- Unsafe isteklerde CSRF, WebSocket'te session/origin; HTTP'de kontrollü CORS ve
  browser security header kontrolleri eklendi.
- Başarısız login rate limiting ile admin create/login/logout audit eventleri eklendi.
- UI'ye erişilebilir ilk kurulum, login, mevcut kullanıcı ve logout akışı eklendi;
  polling ve WebSocket authentication tamamlanmadan başlamıyor.
- Production modunda Vite build aynı FastAPI origin'inden sunuluyor; docs kapalı.
- Graceful shutdown kullanan Windows SCM service entrypoint'i ve kurulum/yönetim
  PowerShell script'i eklendi.
- Service çalışma dizininden bağımsız, repository-köküne çözülen runtime yolları
  eklendi.

## Ana dosyalar

- `backend/src/garage_lpr/auth/`
- `backend/src/garage_lpr/security/headers.py`
- `backend/src/garage_lpr/api/routes/auth.py`
- `backend/src/garage_lpr/service/windows.py`
- `backend/src/garage_lpr/database/migrations/versions/91c4b8e2f5a7_add_auth_sessions.py`
- `frontend/src/pages/Authentication.tsx`
- `scripts/windows-service.ps1`
- `docs/DEPLOYMENT.md`

## Mimari kararlar

- JWT yerine iptal edilebilir, opaque ve veritabanı tabanlı session seçildi. Ham
  session/CSRF sırları diske yazılmıyor.
- Local edge kullanımında session cookie + double-submit/server-digest CSRF modeli
  seçildi. Login endpoint'i rate limit dışında açık; bütün operasyon yüzeyi admin.
- Tek admin session'ı esas alındı: yeni login önceki session'ı iptal eder. Bu,
  paylaşılan saha hesabında açık kalan eski tarayıcı riskini sınırlar.
- Production'da backend ve UI aynı origin'de çalışır; ayrı Node process tutulmaz.
- Windows service tek process/worker çalıştırır; kontrolsüz process/thread çoğalması
  oluşturmaz.

## Doğrulama

- Backend: 87 test; Ruff ve strict mypy.
- Frontend: ESLint, TypeScript ve Vite production build.
- Auth hash/digest, setup sınırı, CSRF, rate limit, session expiry/logout,
  WebSocket session, CORS, security headers, static production UI ve platform-nötr
  Windows service import testleri.
- Çalışan backend + Vite proxy üzerinde setup endpoint'i `200`, oturumsuz health
  `401` ve beklenen hardening header'larıyla HTTP smoke kontrolü.

## Bilinen eksikler

- Windows service kurulumu bu macOS geliştirme ortamında SCM üzerinde çalıştırılamadı;
  gerçek Windows 10/11 makinede install/restart/reboot testi gereklidir.
- Parola reset ve çoklu admin yönetim UI'si yoktur; MVP tek yerel admin içindir.
- Tam 10 adımlı setup wizard yerine güvenlik açısından zorunlu ilk-admin adımı
  sağlandı; kamera/gate/model adımları mevcut yönetim sayfalarından yapılır.
- TLS uygulamanın içinde sonlandırılmaz; LAN erişiminde reverse proxy saha sorumluluğudur.

## Sonraki faz

Phase 8: CPU/RAM profiling, SQLite contention, reconnect/gate failure soak testleri
ve en az 72 saatlik uzun çalışma doğrulaması.
