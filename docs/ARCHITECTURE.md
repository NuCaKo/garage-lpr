# Sistem mimarisi

## Mevcut durum analizi

Proje yeni bir klasörde başlatıldı; korunacak eski kod, şema veya bağımlılık
yoktu. Bu durum teknik borç taşımadan modül sınırlarını baştan tanımlamamıza
olanak sağladı. Başlangıç riskleri; saha donanımının henüz bilinmemesi, örnek
plaka modeli/verisi olmaması ve güvenlik katmanının Phase 7'de planlanmış
olmasıdır. Bu nedenle Phase 1 fiziksel gate komutu sunmaz.

## Hedef veri akışı

```text
Camera Adapter
  → Stream Manager
  → Latest Frame Buffer (bounded)
  → Frame Sampler
  → Plate Detector Adapter
  → Plate Crop
  → OCR Adapter
  → Plate Normalizer
  → Temporal Validator + Lightweight Tracker
  → Authorization Service + Cooldowns
  → Gate Controller Adapter
  → Event Service
```

Her dış sistem bir `Protocol`/soyut adaptör arkasında tutulacaktır. İş kuralları
API route'larına veya UI bileşenlerine konmayacaktır.

## Process modeli

- Tek kamera MVP: bir daemon capture worker, kapasitesi tam olarak 1 olan
  latest-frame buffer, tek inference worker ve tek audit event worker.
- Async event loop yalnızca I/O için; CPU-bound inference ayrı worker'da.
- Reconnect tek lifecycle task'ında ve `1, 2, 5, 10, 30` saniyelik üst sınırlı
  backoff ile yapılır. Her denemede yeni thread oluşturulmaz.
- OCR yalnızca detector crop ürettiğinde çalışır.
- Health ve kaynak metrikleri düşük frekansta örneklenir; UI varsayılan 10 saniye
  aralıkla sorgular.

## Phase 2 kamera çalışma modeli

- `CameraProvider` capture kaynağını, `RTSPCameraProvider` OpenCV/FFmpeg detayını
  ve `CameraManager` worker yaşam döngüsünü birbirinden ayırır.
- Open/read timeout sahadan yapılandırılır. Worker kapanışı timeout içinde
  tamamlanmazsa aynı kamera için ikinci worker başlatılmaz.
- Capture sonucu kopyalanmadan kapasite-1 `LatestFrameBuffer` içine yazılır; tüketici
  gerideyse eski frame sayılarak atılır.
- Tarayıcı RTSP oynatmaz. Kamera sayfası açıkken 2 saniyede bir son frame JPEG'i
  ister; aynı sequence için encoder cache'i tekrar encode işlemini önler.
- ROI, çözünürlük değişimlerine dayanıklı `x/y/width/height` normalize koordinatları
  olarak SQLite'a kaydedilir.
- Kamera kullanıcı adı ayrı tutulur; parola API'de write-only olup yerel dosya
  anahtarıyla şifrelenir. URL içinde credential kabul edilmez ve log metadata'sına
  stream URL/parola yazılmaz.

## Phase 3 inference çalışma modeli

- Uygulama genelinde tek sabit inference worker, aktif kameraların kapasite-1
  tamponundaki en yeni sequence'i okur. Kamera özel detection FPS değeri global
  tavanla sınırlandırılır; eski frame kuyruğu oluşmaz.
- `ProductionPipelineFactory`, ONNX Runtime session oluşturmayı detector/OCR
  adaptörlerinden ayırır. `auto`, CUDA kullanılabiliyorsa CUDA'yı; aksi durumda
  CPU'yu seçer. Açık `cuda` talebi karşılanamıyorsa sistem sessiz fallback yapmaz.
- Detector yalnızca normalize ROI üzerinde çalışır. En yüksek güvenli ve sınırlı
  sayıdaki detection crop edilir; detector sonuç üretmezse OCR çağrılmaz.
- Detector letterbox dönüşümü, NMS ve `xyxy`/`yolo_v8` decoder içerir. OCR yalnızca
  sabit boyutlu plate crop üzerinde CTC greedy decode uygular. Model tensor
  sözleşmesi ayarlarla uyuşmazsa bileşen fail-safe şekilde yüklenmez.
- Türk plaka normalizer'ı ayraçları temizler, il kodu ve harf/rakam segmentlerini
  doğrular. `O/0`, `I/1`, `S/5`, `B/8` düzeltmeleri yalnızca segment bağlamında
  yapılır; sonuç henüz erişim kararı değildir.
- Metrikler örnek listesi tutmaz; sayaç ve EWMA ile detection FPS, detector/OCR
  latency, detection/OCR çağrıları ve son aday plaka tutulur. UI mevcut 10 saniyelik
  health sorgusunda metrikleri beraber alır.
- Model bulunmadığında servis kapanmaz: detector/OCR `CONFIGURATION_REQUIRED`,
  sistem `DEGRADED` olur. Pipeline çalışma hatasında worker durur ve rastgele tekrar
  deneme döngüsüne girmez.
- Kayıtlı video runner aynı pipeline ve sampler'ı sequential çalıştırır; frame
  biriktirmez ve gate katmanına bağlı değildir.

## Phase 4 karar çalışma modeli

- Her kamera frame'indeki plate box'ları appearance modeli olmadan hafif IoU
  eşleştirmesiyle kısa ömürlü track kimliklerine bağlanır. Track sayısı ve idle
  süresi konfigürasyonla sınırlıdır; eski track/validator state'i temizlenir.
- Her track kendi `TemporalPlateValidator` örneğine sahiptir. Yalnızca geçerli
  formattaki ve minimum OCR confidence üzerindeki aynı normalize plaka,
  yapılandırılmış zaman penceresinde gerekli tekrar sayısına ulaştığında doğrulanır.
- Doğrulanan track bir kez karar üretir. Aynı araç görüntüde kalırken tekrar DB
  sorgusu veya gate-ready kararı üretilmez.
- Authorization sorgusu yalnızca temporal doğrulamadan sonra açılan kısa ömürlü
  SQLAlchemy session ile yapılır. Araç bulunamaması, disabled, tarih aralığı ve
  haftalık/saatlik pencere sırasıyla tanımlı `AuthorizationStatus` üretir.
- Gece yarısını aşan erişim pencerelerinde erken sabah bölümü başlangıç gününün
  kuralına aittir. Saat dilimi IANA adıyla merkezî ayardan alınır.
- Authorized karar, maintenance kapalıysa atomik plaka/global cooldown rezervasyonu
  yapar ve `AUTHORIZED_PENDING_GATE` üretir. Maintenance açıkken veya cooldown
  devredeyken fiziksel gate için uygun sonuç çıkmaz.
- Cooldown plaka sözlüğü, tracker state'i, temporal observations ve metrikler sabit
  üst sınırlar altında tutulur. Frame/OCR geçmişi biriktirilmez.
- Phase 4 hiçbir `GateController.open()` çağrısı yapmaz. Simulation guard, gate
  health ve gerçek pulse orchestration Phase 5'in tek karar tüketicisinde
  uygulanacaktır.

## Phase 5 gate çalışma modeli

- `GateOrchestrator`, yalnızca `AUTHORIZED_PENDING_GATE` kararlarını tüketir.
  Maintenance durumunu ikinci kez kontrol eder; karar anında kameranın halen
  `CONNECTED` olmaması halinde komut üretmez.
- Aktif `AccessRule`, doğrulanmış `vehicle_id` ile `camera_id` değerini aktif bir
  gate controller'a bağlar. Kamera özel kural varsa fallback kuralın önüne geçer;
  aynı öncelikte birden fazla kural fail-safe `ACCESS_RULE_AMBIGUOUS` üretir.
- Simulation açıkken access rule çözülür ancak controller health/open metotları
  çağrılmaz; sonuç `SIMULATED_GATE_OPEN` olarak structured log ve bounded metriğe
  yazılır.
- Tüm gerçek open çağrıları kapasitesi 1 olan tek daemon worker'dan geçer. Komut
  timeout olursa executor poison edilir ve controller runtime açıkça resetlenene
  veya process yeniden başlatılana kadar yeni OPEN kabul etmez. Gate health bu
  durumda `UNAVAILABLE` olur; bloklanan adaptör için yeni thread oluşturulmaz.
- `MockGateController`, pulse bitişini monotonic deadline ile hesaplar. Pulse için
  timer, polling veya ek thread oluşturmaz.
- `GateManager` yalnızca en az bir aktif controller bulunduğunda command worker
  tutar. Health sorguları dashboard'un düşük frekanslı health döngüsüyle sınırlıdır.
- Yönetim API'si gate/controller ve access-rule CRUD ile bağlantı testi sunar;
  authentication tamamlanmadan manuel OPEN endpoint'i sunulmaz.

## Phase 6 operasyon çalışma modeli

- `OperationalEventRecorder`, detection/recognition/access/gate sonuçlarını domain
  eventlerine dönüştürür. Yüksek hacimli `plate_detected` olayı kamera başına
  yapılandırılabilir minimum aralıkla örneklenir; her frame diske yazılmaz.
- `EventService`, kapasitesi sabit kuyruk ve tek daemon audit worker kullanır.
  Inference yolu event kuyruğunu beklemez; kuyruk doluysa olay kontrollü biçimde
  düşürülür ve health durumu bunu görünür kılar. SQLite geçici hataları sınırlı
  retry ile ele alınır.
- Event önce `recognition_events` tablosuna, erişim/gate auditleri ayrıca
  `access_events` tablosuna aynı transaction içinde yazılır. Yalnızca başarıyla
  kalıcılaşan olay bounded WebSocket broker'a gönderilir; yavaş istemcide eski
  canlı mesaj atılarak güncel olay korunur.
- Event retention varsayılan 90 gündür ve audit worker içinde en fazla günde bir
  çalışır. Snapshot retention varsayılan 30 gündür; snapshot kaydı varsayılan
  kapalıdır ve yalnızca nihai erişim kararları/recognition hataları JPEG üretir.
- Structured JSON loglar boyut ve dosya sayısı sınırlarıyla döndürülür. Secret ve
  credential alanları log metadata'sında maskelenir.
- `ResourceMonitor` arka plan thread'i veya sürekli örnek listesi tutmaz. CPU, RAM,
  process RSS/thread sayısı ve disk değerleri UI'ın 5–300 saniyelik isteği sırasında
  ölçülür. Dashboard isteği bitmeden yeni polling başlatmaz.
- Health aggregation API, database, camera, detector, OCR, gate, event worker,
  snapshot storage ve disk durumlarını `HEALTHY/DEGRADED/UNHEALTHY` olarak birleştirir.
  Disk %90 kullanımda veya 5 GiB altında `DEGRADED`; %98 veya 1 GiB altında
  `UNHEALTHY` olur.
- Events ekranı server-side filtre ve sayfalama kullanır; DOM'da en fazla 50 canlı
  kayıt tutar. WebSocket yeniden bağlantısı `1, 2, 5, 10, 30` saniye backoff ile
  tek bağlantı üzerinden yapılır.

## Phase 7 güvenlik ve deployment modeli

- İlk çalıştırmada yalnızca kullanıcı tablosu boşsa admin kurulabilir. Kurulum
  işlemi tek process içinde kilitlidir; production deployment tek Uvicorn worker
  çalıştırır. Sonraki setup istekleri fail-closed `409` üretir.
- Parolalar Argon2id ile hashlenir ve plaintext hiçbir zaman saklanmaz/loglanmaz.
  Bilinmeyen kullanıcı girişinde dummy hash doğrulaması, başarısız denemelerde
  boyutu sınırlı process-local rate limiter kullanılır.
- Rastgele session/CSRF değerlerinin yalnızca SHA-256 digest'leri SQLite'ta tutulur.
  Session cookie `HttpOnly` ve `SameSite=Strict`; bütün state-changing operasyon
  API'leri double-submit CSRF değerini sunucu digest'iyle birlikte doğrular.
- Operasyon REST endpoint'leri ve canlı event WebSocket'i admin rolü gerektirir.
  WebSocket ayrıca izin verilen `Origin` listesini kontrol eder. Login ve logout
  sonuçları audit event olarak kaydedilir; token/parola metadata'ya girmez.
- Browser yanıtlarında clickjacking, MIME sniffing, referrer ve permissions
  başlıkları bulunur. Production UI'da sınırlı Content-Security-Policy uygulanır;
  auth yanıtları `Cache-Control: no-store` taşır.
- Production modunda FastAPI derlenmiş Vite dosyalarını aynı origin'den sunar ve
  API belgelerini kapatır. Bu, CORS yüzeyini ve ikinci web server ihtiyacını azaltır.
- Windows service adaptörü tek Uvicorn worker başlatır ve SCM stop sinyalini
  uygulamanın graceful shutdown yoluna iletir. Tüm göreli runtime yolları process
  çalışma dizininden bağımsız çözülür: kaynak kurulumunda repository kökü, EXE
  kurulumunda yazılabilir `ProgramData\GarageLPR` kullanılır.

## Windows installer modeli

- PyInstaller servis uygulamasını `onedir` olarak üretir; servis başlangıcında
  geçici dizine tekrar tekrar extraction yapılmaz. Inno Setup bu dizini saha
  kullanıcısına verilen tek setup EXE'sine sıkıştırır.
- Paketlenmiş frontend ve migration kaynakları salt-okunur bundle kökünden bulunur.
  Database, credential anahtarı, log, snapshot, soak raporu ve saha modelleri
  `ProgramData\GarageLPR` altında kalır.
- Göreli model yolu önce yazılabilir saha model dizininde aranır; bulunamazsa bundle
  kaynağına düşer. Model yokluğu gate-open üretmez, inference durumunu degraded yapar.
- Installer upgrade öncesinde eski servisi durdurup kaydını kaldırır; yeni binary'yi
  kurduktan sonra otomatik başlangıç ve sınırlı service recovery politikası uygular.
- Normal uninstall kalıcı saha verilerini bilinçli olarak silmez. Böylece yanlışlıkla
  uninstall database veya kamera credential anahtarını geri döndürülemez biçimde
  kaybetmez.

## Phase 8 dayanıklılık doğrulama modeli

- Soak monitor uygulamanın içine yeni background thread eklemez; ayrı process'ten
  hedef PID'nin RSS, CPU ve thread sayılarını yapılandırılabilir düşük frekansta
  örnekler.
- Örnek geçmişi RAM'de tutulmaz. RSS eğimi online scalar regression, CPU değeri
  toplam/sayaç ve peak değerleri scalar alanlarla hesaplanır; 72 saatte monitor
  belleği örnek sayısıyla büyümez.
- Rapor her örnekte tek JSON dosyasına atomik replace ile yazılır. JSONL veya sınırsız
  snapshot üretmediğinden disk kullanımı zamanla büyümez; kesintide son durum korunur.
- Varsayılan 10 dakika warmup model/runtime allocation'larını baseline dışında
  bırakır. Kabul tavanları 128 MiB son RSS büyümesi, 4 MiB/saat RSS eğimi ve iki
  ek thread'dir; saha donanımına göre daha sıkı değer verilebilir.
- Reconnect soak aynı `CameraStreamLoop` üzerinde 100 ardışık hatayı ve 30 saniyede
  capped backoff'u doğrular. Gate failure soak ilk timeout'tan sonra executor'ın
  poisoned kaldığını ve 250 tekrarda ikinci OPEN çalıştırmadığını sınar.
- Latest-frame pressure 10.000 üretimde yalnızca son frame'in kaldığını; event queue
  pressure kapasite aşımında bloklamadan drop metriği ürettiğini doğrular.
- SQLite contention testi dört sabit worker ile WAL/busy-timeout altında kısa session
  transaction'larını sınar. Lifecycle testi on restart döngüsünden sonra yönetilen
  camera/inference/event/gate thread'lerinin kalmadığını kontrol eder.

## Fail-safe sınırı

Gate açma tek bir orchestration servisinden geçer. Doğrulanmamış
OCR, sağlıksız kamera/gate, maintenance, simulation, zaman kuralı veya cooldown
durumları adapter'a gerçek `open` çağrısı ulaşmadan kararı keser. İstisnaların
varsayılan sonucu kapalı kalmaktır.

## Kalıcılık

SQLite; WAL, foreign key ve busy timeout ayarlarıyla tek cihaz deployment için
seçilmiştir. API transaction'ları kısa tutulur. Repository sınırı PostgreSQL'e
geçişi business logic'ten ayırır. Şema değişiklikleri Alembic migration ile
yapılır; runtime ayarları JSON olarak `system_settings` tablosunda saklanır.

## Çoklu sistem genişlemesi

Tablolar ve servisler tekil global kamera/gate varsaymaz. `camera_id`,
`gate_controller_id` ve erişim kuralı ilişkileri gelecekte bir site içindeki
giriş/çıkış topolojisini destekleyecek şekilde ayrı kayıtlardır. MVP operasyon
servisi önce tek kamera + tek gate ile sınanacaktır.
