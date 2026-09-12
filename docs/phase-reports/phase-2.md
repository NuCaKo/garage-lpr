# Phase 2 raporu

## Yapılan değişiklikler

- RTSP/OpenCV provider, open/read timeout ve çözünürlük isteği eklendi.
- Tek worker/kamera yaşam döngüsü ile kontrollü reconnect ve üst sınırlı
  `1, 2, 5, 10, 30` saniye backoff uygulandı.
- Kapasite-1, kopyasız latest-frame-wins tamponu eklendi; atılan eski frame'ler
  ölçülebilir durumda.
- Kamera CRUD, bağlantı testi ve cache'li son-frame JPEG preview API'leri eklendi.
- Kamera parolaları write-only yapıldı ve yerel Fernet anahtarıyla şifrelendi.
- Kamera listesi, tüm saha ayarları, 10 saniyelik durum yenilemesi, connection-test
  sonucu ve mouse/klavye uyumlu normalize ROI editörü eklendi.
- Kamera health bileşeni gerçek runtime state üzerinden hesaplanmaya başladı.

## Önemli dosyalar

- `backend/src/garage_lpr/camera/manager.py`: sınırlı worker ve frame tamponu sahibi.
- `backend/src/garage_lpr/camera/rtsp.py`: OpenCV/FFmpeg RTSP adaptörü.
- `backend/src/garage_lpr/camera/stream.py`: reconnect ve capture FPS yaşam döngüsü.
- `backend/src/garage_lpr/api/routes/cameras.py`: kamera yönetim, test ve preview API'si.
- `frontend/src/pages/Cameras.tsx`: saha yapılandırma ekranı.
- `frontend/src/components/RoiEditor.tsx`: normalize ROI ve düşük frekanslı preview.

## Mimari kararlar

- MVP aynı anda bir aktif kamera ile sınırlıdır; veri modeli çoklu kamera için
  hazırdır ve sınır bootstrap config ile artırılabilir.
- Worker kendi içinde yeni thread üretmez. Kapanmayan worker varken replacement
  başlatılmaz; böylece bağlantı arızalarında thread çoğalması önlenir.
- Tarayıcı preview'su devamlı transcoding değildir. Yalnızca kamera sayfası açıkken
  0.5 FPS JPEG snapshot kullanır ve aynı frame'i yeniden encode etmez.
- Stream URL'sinde credential kabul edilmez. Şifre çözme yalnızca runtime provider
  config'i oluşturulurken yapılır; log ve API response sınırına taşınmaz.
- Detector/OCR pipeline'ı bu faza çekilmedi; Phase 2 yalnızca güvenilir frame
  sağlama sorumluluğunu üstlenir.

## Bilinen eksikler

- Fiziksel RTSP kamera ile Windows 10/11 saha testi ve uzun reconnect soak testi
  henüz yapılmadı.
- Bu oturumda bağlı tarayıcı olmadığı için piksel tabanlı görsel QA yapılamadı;
  TypeScript, ESLint ve production build doğrulamaları başarılıdır.
- Preview MJPEG/HLS değildir; operasyonel ayar ekranı için düşük frekanslı JPEG'dir.
- Kayıtlı video offline pipeline ve frame sampler detector ile Phase 3'te gelir.
- ONVIF, USB ve HTTP camera adapter'ları sonraki ihtiyaçlara bırakıldı.
- API authentication Phase 7 kapsamındadır; uygulama bu aşamada yalnızca güvenilen
  yerel makine/ağ üzerinde çalıştırılmalıdır.

## Doğrulama

- Backend: Ruff başarılı, mypy strict başarılı, 18 test başarılı.
- Reconnect, backoff, latest-frame-wins, secret encryption, RTSP credential encoding,
  ROI validation, kamera CRUD ve connection-test API davranışları test edildi.
- Frontend: TypeScript check, ESLint ve Vite production build başarılı.

## Sonraki faz

Phase 3: ONNX Runtime execution-provider seçimi, hafif plaka detector adapter'ı,
detection FPS frame sampler, sadece plate crop üzerinde OCR, Türk plakası
normalizasyonu ve inference/OCR latency metrikleri.
