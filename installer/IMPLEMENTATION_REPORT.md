# Windows installer implementation report

## Yapılan değişiklikler

- PyInstaller one-folder Windows service paketi
- Bağımsız `GarageLPRSoak.exe`
- Tek dosyalı Inno Setup kurulum paketi
- Program Files / ProgramData kaynak ve kalıcı veri ayrımı
- Otomatik servis kurulumu, health check ve restart politikası
- Güncellemede servis stop/remove/install akışı
- Kalıcı veriyi uninstall sırasında koruma
- Opsiyonel Authenticode imzalama ve SHA-256 çıktı
- Windows build script'i ve isteğe bağlı GitHub Actions şablonu

## Mimari kararlar

PyInstaller `onefile` servis başlangıcında her seferinde geçici extraction yaptığı
için servis paketi `onedir` tutulmuştur. Inno Setup bu dizini tek bir setup EXE'sine
sıkıştırır. Böylece saha kullanıcısı yine tek dosya görürken servis başlangıcı daha
deterministik kalır.

Salt-okunur uygulama kaynakları `Program Files`, yazılabilir ve yedeklenmesi gereken
veriler `ProgramData` altındadır. Installer normal uninstall sırasında saha verisini
silmez.

## Bilinen eksikler

- Windows EXE bu macOS geliştirme ortamında derlenemez veya Windows SCM üzerinde
  çalıştırılamaz.
- Installer üretimi ve install/upgrade/uninstall smoke testi Windows 10/11 x64
  runner üzerinde yapılmalıdır.
- Üretim Authenticode sertifikası proje kapsamına dahil değildir.
- Repository gerçek ONNX model ağırlıklarını içermez.
