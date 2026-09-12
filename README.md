# Garage LPR

Yerel ağda, internet bağımlılığı olmadan çalışan plaka tanıma ve kontrollü garaj
erişim sistemi. Temel hedef: **Configure once → run continuously**.

Bu repository Phase 1–7 temelini ve Phase 8 dayanıklılık harness'ını içerir:
merkezi yapılandırma, SQLite/Alembic,
RTSP capture, kapasite-1 son-frame tamponu, yapılandırılabilir ONNX detector,
crop-only OCR, Türk plakası normalizasyonu, bounded IoU tracking, çoklu-frame
temporal doğrulama, araç yetkilendirme, plaka/global cooldown, access-rule routing
ve fail-safe Mock gate orchestration; ayrıca kalıcı audit eventleri, bounded canlı
WebSocket akışı, düşük frekanslı kaynak/health metrikleri ve disk retention içerir.
İlk çalıştırma admin kurulumu, Argon2id parola hashleme, sunucu taraflı oturum,
CSRF/admin koruması ve native Windows service kurulumu da dahildir.
Repository model ağırlıklarını içermez; sözleşmeler [models/README.md](models/README.md)
içinde tanımlıdır. Windows installer build'i sırasında `models/` altına sağlanan
ONNX dosyaları kurulum paketine eklenebilir. HTTP/MQTT/Serial fiziksel kapı
adaptörleri henüz etkin değildir.

## Windows installer

Saha bilgisayarında Python veya Node.js kurmadan kullanılabilen tek dosyalı Windows
installer üretimi `installer/` altında tutulur:

```powershell
.\installer\build-installer.ps1
```

Üretilen `GarageLPR-Setup-<version>-x64.exe`, uygulamayı Windows servisi olarak
kurar ve `http://localhost:8080` adresini hazırlar. Ayrıntılar ve imzalama seçeneği
için [installer belgesine](installer/README.md) bakın.

## Hızlı başlangıç

Gereksinimler: Python 3.11+, Node.js 20+.

```bash
python -m venv .venv
# Windows: .venv\Scripts\Activate.ps1
# Linux/macOS: source .venv/bin/activate
python -m pip install -e "./backend[dev]"
alembic -c backend/alembic.ini upgrade head
python -m garage_lpr
```

Ayrı bir terminalde:

```bash
npm --prefix frontend install
npm --prefix frontend run dev
```

- API: <http://127.0.0.1:8080>
- API belgesi: <http://127.0.0.1:8080/docs>
- UI: <http://127.0.0.1:5173>

İlk açılışta UI tek kullanımlık admin hesabı oluşturma ekranını gösterir. Parola
en az 12 karakter olmalıdır. Kurulum tamamlandıktan sonra bütün operasyon API'leri
admin oturumu gerektirir.

Windows için [scripts/dev.ps1](scripts/dev.ps1), Unix sistemler için
[scripts/dev.sh](scripts/dev.sh) kullanılabilir.
Production ve Windows service kurulumu için [deployment belgesine](docs/DEPLOYMENT.md)
bakın.

Uzun çalışma testinde servis process'ini sabit bellekte izlemek için:

```powershell
.\scripts\soak-test.ps1 -DurationHours 72
```

Kabul kriterleri ve kontrollü saha senaryosu [stability test
belgesinde](docs/STABILITY_TEST.md) tanımlıdır.

## Belgeler

- [Mimari](docs/ARCHITECTURE.md)
- [Teknoloji kararı](docs/adr/0001-foundation-stack.md)
- [Faz planı](docs/PHASES.md)
- [Phase 1 raporu](docs/phase-reports/phase-1.md)
- [Phase 2 raporu](docs/phase-reports/phase-2.md)
- [Phase 3 raporu](docs/phase-reports/phase-3.md)
- [Phase 4 raporu](docs/phase-reports/phase-4.md)
- [Phase 5 raporu](docs/phase-reports/phase-5.md)
- [Phase 6 raporu](docs/phase-reports/phase-6.md)
- [Phase 7 raporu](docs/phase-reports/phase-7.md)
- [Deployment](docs/DEPLOYMENT.md)
- [Windows EXE installer](installer/README.md)
- [Stability ve 72 saat soak testi](docs/STABILITY_TEST.md)
- [Phase 8 ara raporu](docs/phase-reports/phase-8.md)
- [Model sözleşmeleri ve offline test](models/README.md)

## Güvenlik durumu

Mevcut API manuel gate-open endpoint'i içermez. Otomatik OPEN yalnızca temporal
doğrulama, authorization, cooldown, bağlı access rule, bağlı kamera sağlığı,
maintenance ve simulation kontrollerinden geçen tek orchestration servisinden
çıkabilir. Phase 5 yalnızca yerel Mock adaptörü etkinleştirir. Varsayılan runtime
ayarı simulation ve maintenance modlarını açık tutar. Kamera parolaları API
yanıtlarına dönmez ve yerel Fernet anahtarıyla şifrelenmiş olarak saklanır. Admin
parolası Argon2id ile, oturum ve CSRF değerleri yalnızca SHA-256 digest olarak
saklanır. Oturum cookie'si HttpOnly/SameSite=Strict, state değiştiren API çağrıları
CSRF korumalıdır. Varsayılan servis yalnızca `127.0.0.1` üzerinde dinler; başka
cihazlara açılacaksa TLS terminasyonu ve `GARAGE_LPR_SECURE_COOKIES=true` zorunlu
saha ayarı olarak ele alınmalıdır.
