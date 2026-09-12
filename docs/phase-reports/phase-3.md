# Phase 3 raporu — Algılama ve OCR

## Yapılan değişiklikler

- ONNX Runtime için `auto/cpu/cuda` provider seçimi ve konservatif tek-thread
  session ayarları eklendi.
- ROI üzerinde çalışan, `xyxy` ve YOLOv8 çıktılarını destekleyen detector;
  letterbox, confidence filtresi ve NMS ile implemente edildi.
- Detector crop'ları dışında çalışmayan CTC OCR adaptörü ve bağlam duyarlı Türk
  plaka normalizer'ı eklendi.
- Tek sabit worker, kamera/global detection FPS limiti ve latest-frame-wins akışı
  kuruldu. OCR yalnızca geçerli boyuttaki plate crop için çağrılır.
- Sabit boyutlu sayaç/EWMA metrikleri API, health ve Dashboard'a bağlandı.
- Model ayarları System Settings sayfasına; aynı pipeline'ı kullanan kayıtlı video
  modu CLI'a eklendi.

## Oluşturulan başlıca dosyalar

- `backend/src/garage_lpr/inference/`: runtime, factory, manager, state ve metrikler
- `backend/src/garage_lpr/detection/`: ONNX detector, sampler ve pipeline
- `backend/src/garage_lpr/ocr/`: ONNX CTC OCR ve Türk plaka normalizer'ı
- `backend/src/garage_lpr/offline_video.py`: sequential kayıtlı video runner
- `backend/src/garage_lpr/api/routes/metrics.py`: inference metrik endpoint'i
- `models/README.md`: model input/output sözleşmeleri
- Phase 3 backend unit/integration testleri

## Mimari kararlar

- Model framework bağımlılığı ONNX Runtime adapter sınırında tutuldu.
- `auto` sağlayıcı CUDA'yı önceler ve CPU'ya düşer; açık `cuda` seçimi
  karşılanamıyorsa fail-safe hata verir.
- Model dosyası veya tensor sözleşmesi hatalıysa uygulama çalışmaya devam eder,
  fakat inference `CONFIGURATION_REQUIRED` olur ve hiçbir erişim kararı üretmez.
- Bellek büyümesini önlemek için frame backlog, aday geçmişi ve latency örnek
  dizileri tutulmaz.
- Tek-frame OCR sonucu yalnızca adaydır. Temporal doğrulama tamamlanmadan
  authorization veya gate tetiklenmez.

## Doğrulama

- 44 backend testi geçti.
- Ruff ve strict mypy kontrolleri geçti.
- Frontend ESLint ve production build geçti.
- Model ağırlığı dağıtılmadığı için gerçek görüntü doğruluk testi bu fazda
  yapılmadı.

## Bilinen eksikler

- Lisansı ve Türk plaka veri seti performansı doğrulanmış detector/OCR ağırlıkları
  sağlanmalıdır.
- NVIDIA/CUDA ve gerçek RTSP saha donanımı üzerinde latency/soak testi yapılmadı.
- Temporal validation, tracking, authorization ve cooldown Phase 4 kapsamındadır.
- UI tarayıcı tabanlı görsel/regresyon testi henüz otomatik değildir.

## Sonraki faz

Phase 4'te hafif IoU/centroid tracking, zaman pencereli çoklu OCR doğrulaması,
authorization sonucu ve plaka/global cooldown implemente edilecektir. Hiçbir
tek-frame aday gate kararı üretemeyecektir.
