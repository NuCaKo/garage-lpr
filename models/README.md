# Model sözleşmeleri

Model ağırlıkları lisans, ülke veri seti ve saha doğruluğu doğrulanmadan repository'ye
eklenmez. Sistem model yokken `CONFIGURATION_REQUIRED` durumunda kalır ve pipeline
çalıştırmaz.

## Detector

Varsayılan input `float32 [1,3,640,640]`, renk sırası RGB ve aralık `0..1`'dir.
Ön işleme aspect ratio'yu koruyan letterbox uygular.

Desteklenen output biçimleri:

- `xyxy`: `[1,N,6]` veya `[N,6]`; satır `x1,y1,x2,y2,confidence,class_id`.
- `yolo_v8`: `[1,4+C,N]`; `cx,cy,w,h` ve ardından sınıf skorları.

Koordinatlar model input piksel uzayında olmalıdır. NMS uygulama içinde çalışır.

## OCR

Varsayılan input grayscale `float32 [1,1,48,160]`, aralık `-1..1`'dir. Üç kanal
UI üzerinden seçilebilir. Output `[1,T,C]` CTC logits olmalıdır. Blank sınıfı indeks
0, `ocr_charset` karakterleri indeks 1'den başlar.

Varsayılan dosya adları:

- `models/license_plate_detector.onnx`
- `models/license_plate_ocr.onnx`

## Offline test

```bash
python -m garage_lpr.offline_video \
  --video samples/entrance.mp4 \
  --detector-model models/license_plate_detector.onnx \
  --ocr-model models/license_plate_ocr.onnx \
  --detection-fps 5
```

Runner frame biriktirmez, video timestamp'ine göre örnekler ve gerçek gate katmanına
bağlanmaz.
