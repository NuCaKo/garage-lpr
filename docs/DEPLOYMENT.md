# Production deployment

## Güvenlik sınırı

Varsayılan servis `127.0.0.1:8080` üzerinde çalışır ve internet gerektirmez. Aynı
Windows bilgisayardaki tarayıcı `http://localhost:8080` adresini kullanır. Servisi
LAN'a açmak gerekiyorsa TLS sağlayan bir reverse proxy kullanın,
`GARAGE_LPR_HOST` değerini bilinçli olarak değiştirin ve
`GARAGE_LPR_SECURE_COOKIES=true` ayarlayın. API'yi doğrudan internete açmayın.

Production tek Uvicorn worker ile çalıştırılmalıdır. Kamera, inference, SQLite ve
ilk-admin kurulum kilidi bu edge process modeline göre tasarlanmıştır; birden fazla
web worker aynı donanım kaynaklarını çoğaltır.

## Windows 10/11 EXE kurulumu — önerilen saha yöntemi

Release için Windows build bilgisayarında:

```powershell
.\installer\build-installer.ps1
```

Üretilen `installer\build\output\GarageLPR-Setup-<version>-x64.exe` dosyasını saha
bilgisayarına taşıyın, SHA-256 dosyasıyla bütünlüğünü kontrol edin ve yönetici olarak
çalıştırın. Hedef bilgisayarda Python veya Node.js gerekmez. Installer:

- uygulamayı `C:\Program Files\Garage LPR` altına kurar,
- kalıcı verileri `C:\ProgramData\GarageLPR` altında tutar,
- `GarageLPR` servisini otomatik başlangıçla kaydeder,
- servis hata verirse sınırlı gecikmelerle yeniden başlatma politikası uygular,
- health check tamamlandıktan sonra `http://localhost:8080` adresini sunar.

Installer varsayılan `simulation_mode=true` ve `maintenance_mode=true` değerlerini
değiştirmez. Model yoksa servis çalışabilir ancak inference fail-safe `DEGRADED`
kalır. Code-signing sertifikası build script'ine `-SignTool` ile verilebilir; hiçbir
sertifika veya parola repository'ye yazılmamalıdır.

## Kaynak koddan Windows service kurulumu — geliştirici alternatifi

Gereksinimler: Python 3.11+, Node.js 20+ ve yönetici PowerShell.

1. `.env.example` dosyasını `.env` olarak kopyalayın ve saha ayarlarını girin.
2. Yönetici PowerShell'de repository kökünde şu komutu çalıştırın:

```powershell
.\scripts\windows-service.ps1 install
```

Script sanal ortamı oluşturur, backend ile `pywin32` bağımlılığını kurar, kilitli
`package-lock.json` üzerinden UI'yi derler, servisi otomatik başlangıçla kaydeder
ve başlatır. Ardından `http://localhost:8080` adresinde ilk admin hesabını oluşturun.

Servis yönetimi:

```powershell
.\scripts\windows-service.ps1 status
.\scripts\windows-service.ps1 restart
.\scripts\windows-service.ps1 stop
.\scripts\windows-service.ps1 remove
```

## Kalıcı veriler ve yedek

EXE kurulumunda:

- SQLite: `C:\ProgramData\GarageLPR\runtime\data\garage_lpr.db`
- Kamera credential anahtarı: `C:\ProgramData\GarageLPR\runtime\data\camera-secrets.key`
- Döndürülen loglar: `C:\ProgramData\GarageLPR\runtime\logs\`
- Olay snapshot'ları: `C:\ProgramData\GarageLPR\runtime\snapshots\`
- Model ağırlıkları: `C:\ProgramData\GarageLPR\models\`
- Bootstrap ayarları: `C:\ProgramData\GarageLPR\.env`

Kaynak kod kurulumunda aynı göreli yollar repository kökü altındadır.

Yedekte SQLite veritabanını ve `camera-secrets.key` dosyasını birlikte koruyun.
Anahtar kaybolursa şifrelenmiş kamera parolaları kurtarılamaz. Aktif veritabanını
dosya kopyasıyla almak yerine uygulamayı durdurun veya SQLite'ın tutarlı backup
mekanizmasını kullanın.

## Güncelleme

Servisi durdurun, uygulama dosyalarını güncelleyin, bağımlılık/UI kurulumunu yeniden
çalıştırın ve servisi başlatın. Uygulama başlangıcında Alembic migration otomatik
uygulanır; yine de güncelleme öncesi tutarlı yedek alın.

## Production kontrolleri

- `GARAGE_LPR_ENVIRONMENT=production`
- `GARAGE_LPR_LOG_LEVEL=INFO`
- Varsayılan `simulation_mode=true` ve `maintenance_mode=true` değerlerini ancak
  kamera/model/gate saha testi tamamlandıktan sonra UI'dan kapatın.
- Gerçek gate'e geçmeden önce Mock controller ve Simulation Mode ile uçtan uca
  erişim eventlerini doğrulayın.
- Windows Event Viewer ve `runtime/logs` altında temiz start/stop kaydı bulunduğunu
  kontrol edin.

## Uzun çalışma doğrulaması

Windows service çalışırken yönetici PowerShell'de aşağıdaki komut PID'yi SCM'den
bulur ve 72 saatlik sabit-bellekli monitorü başlatır:

```powershell
.\scripts\soak-test.ps1 -DurationHours 72
```

EXE kurulumunda Başlat menüsündeki `Garage LPR > 72 Hour Stability Test` kısayolu
veya şu komut kullanılabilir:

```powershell
& 'C:\Program Files\Garage LPR\SoakTest.ps1' -DurationHours 72
```

Son durum `runtime/soak/latest.json` dosyasına atomik olarak yazılır. Process
kapanırsa test başarı sayılmaz; `TARGET_EXITED` üretilir. Kontrollü yük aşamaları
ve ek health/event kontrolleri [STABILITY_TEST.md](STABILITY_TEST.md) içindedir.
