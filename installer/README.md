# Garage LPR Windows installer

Bu klasör Windows 10/11 x64 için tek dosyalı kurulum paketi üretir. Kurulan
uygulama Python veya Node.js gerektirmez.

## Üretim

Gereksinimler yalnızca build bilgisayarı içindir:

- Windows 10/11 x64
- Python 3.11 x64
- Node.js 20+
- Inno Setup 6

Yönetici olmayan bir PowerShell'de proje kökünden çalıştırın:

```powershell
.\installer\build-installer.ps1
```

Çıktı:

```text
installer\build\output\GarageLPR-Setup-0.1.0-x64.exe
installer\build\output\GarageLPR-Setup-0.1.0-x64.exe.sha256
```

`-Version` ile sürüm verilebilir. `-SignTool` bir Authenticode imzalama komutu
alır; komuttaki `$f` Inno Setup tarafından imzalanacak dosya yoluyla değiştirilir.

```powershell
.\installer\build-installer.ps1 -Version 0.1.0 `
  -SignTool 'signtool.exe sign /fd SHA256 /tr http://timestamp.digicert.com /td SHA256 /a $f'
```

## Kurulum davranışı

- Uygulama: `C:\Program Files\Garage LPR`
- Kalıcı saha verisi: `C:\ProgramData\GarageLPR`
- Servis: `GarageLPR`, otomatik başlangıç ve kontrollü restart politikası
- UI: `http://localhost:8080`
- Varsayılan durum: simulation ve maintenance açık; fiziksel kapı tetiklenmez.

Güncelleme mevcut servisi kontrollü durdurur ve yeniden kurar. Database, kamera
şifreleme anahtarı, loglar, snapshot'lar, modeller ve `.env` dosyası güncelleme
ve normal uninstall sırasında korunur. Tam veri silme bilinçli olarak installer'a
eklenmemiştir.

## Model dosyaları

Build sırasında `models/` altındaki dosyalar installer'a alınır ve ilk kurulumda
`C:\ProgramData\GarageLPR\models` altına kopyalanır. Var olan saha modellerinin
üzerine yazılmaz. ONNX model dosyaları yoksa installer yine üretilir ancak sistem
fail-safe `DEGRADED` durumda kalır ve gerçek plaka inference başlatmaz.

## Sessiz kurulum

```powershell
.\GarageLPR-Setup-0.1.0-x64.exe /VERYSILENT /SUPPRESSMSGBOXES /NORESTART
```

Kurulum sonrasında `installer\health-check.ps1` eşdeğeri uygulama dizinine
`HealthCheck.ps1` olarak eklenir.

## GitHub Actions ile CI üretimi

Aktif workflow `.github/workflows/windows-installer.yml` konumundadır;
`ci/windows-installer.yml` paketleme klasöründeki kaynak şablondur. GitHub'da
Actions > Build Garage LPR Windows Installer > Run workflow seçildiğinde Windows
runner installer ve checksum artifact'ını üretir. Paketleme tanımı ve bütün build
çıktıları yine `installer/` altında kalır. İmzalama sertifikaları veya parolaları
repository'ye eklemeyin.
