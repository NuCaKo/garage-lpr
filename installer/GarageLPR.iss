#ifndef AppVersion
  #define AppVersion "0.1.0"
#endif

#define AppName "Garage LPR"
#define ServiceName "GarageLPR"
#define AppPublisher "Garage LPR"

[Setup]
AppId={{8C7B8B4A-2AB2-4F91-8E29-1DF690A30C88}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={autopf}\Garage LPR
DefaultGroupName=Garage LPR
DisableProgramGroupPage=yes
PrivilegesRequired=admin
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0.17763
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
OutputBaseFilename=GarageLPR-Setup-{#AppVersion}-x64
SetupLogging=yes
RestartIfNeededByRun=no
CloseApplications=no
UninstallDisplayName={#AppName}
#ifdef EnableSigning
SignTool=garagelpr
SignedUninstaller=yes
#endif

[Files]
Source: "build\dist\GarageLPRService\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "build\dist\GarageLPRSoak.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "health-check.ps1"; DestDir: "{app}"; DestName: "HealthCheck.ps1"; Flags: ignoreversion
Source: "soak-test.ps1"; DestDir: "{app}"; DestName: "SoakTest.ps1"; Flags: ignoreversion
Source: ".env.production"; DestDir: "{commonappdata}\GarageLPR"; DestName: ".env"; Flags: onlyifdoesntexist uninsneveruninstall
Source: "build\model-payload\*"; DestDir: "{commonappdata}\GarageLPR\models"; Flags: onlyifdoesntexist recursesubdirs createallsubdirs uninsneveruninstall

[Dirs]
Name: "{commonappdata}\GarageLPR"; Flags: uninsneveruninstall
Name: "{commonappdata}\GarageLPR\runtime\data"; Flags: uninsneveruninstall
Name: "{commonappdata}\GarageLPR\runtime\logs"; Flags: uninsneveruninstall
Name: "{commonappdata}\GarageLPR\runtime\snapshots"; Flags: uninsneveruninstall
Name: "{commonappdata}\GarageLPR\runtime\soak"; Flags: uninsneveruninstall
Name: "{commonappdata}\GarageLPR\models"; Flags: uninsneveruninstall

[Icons]
Name: "{group}\Garage LPR"; Filename: "http://localhost:8080"
Name: "{group}\Health Check"; Filename: "powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{app}\HealthCheck.ps1"""; WorkingDir: "{app}"
Name: "{group}\72 Hour Stability Test"; Filename: "powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{app}\SoakTest.ps1"""; WorkingDir: "{app}"
Name: "{group}\Uninstall Garage LPR"; Filename: "{uninstallexe}"

[Run]
Filename: "{app}\GarageLPRService.exe"; Parameters: "--startup auto install"; StatusMsg: "Garage LPR service is being installed..."; Flags: runhidden
Filename: "{sys}\sc.exe"; Parameters: "failure {#ServiceName} reset= 86400 actions= restart/5000/restart/15000/restart/60000"; StatusMsg: "Service recovery policy is being configured..."; Flags: runhidden
Filename: "{sys}\sc.exe"; Parameters: "failureflag {#ServiceName} 1"; Flags: runhidden
Filename: "{app}\GarageLPRService.exe"; Parameters: "start"; StatusMsg: "Garage LPR service is starting..."; Flags: runhidden
Filename: "powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{app}\HealthCheck.ps1"""; StatusMsg: "Garage LPR is being verified..."; Flags: runhidden
Filename: "http://localhost:8080"; Description: "Open Garage LPR administration"; Flags: postinstall shellexec skipifsilent nowait

[UninstallRun]
Filename: "{app}\GarageLPRService.exe"; Parameters: "stop"; Flags: runhidden skipifdoesntexist; RunOnceId: "StopGarageLPR"
Filename: "{app}\GarageLPRService.exe"; Parameters: "remove"; Flags: runhidden skipifdoesntexist; RunOnceId: "DeleteGarageLPR"

[Code]
function ServiceExists(): Boolean;
var
  ExitCode: Integer;
begin
  Result := Exec(ExpandConstant('{sys}\sc.exe'), 'query {#ServiceName}', '',
    SW_HIDE, ewWaitUntilTerminated, ExitCode) and (ExitCode = 0);
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  ExitCode: Integer;
  ExistingService: String;
begin
  Result := '';
  if not ServiceExists() then
    exit;

  ExistingService := ExpandConstant('{app}\GarageLPRService.exe');
  if FileExists(ExistingService) then
    Exec(ExistingService, 'stop', '', SW_HIDE, ewWaitUntilTerminated, ExitCode)
  else
    Exec(ExpandConstant('{sys}\sc.exe'), 'stop {#ServiceName}', '',
      SW_HIDE, ewWaitUntilTerminated, ExitCode);
  Sleep(1000);
  if (not Exec(ExpandConstant('{sys}\sc.exe'), 'delete {#ServiceName}', '',
    SW_HIDE, ewWaitUntilTerminated, ExitCode)) or (ExitCode <> 0) then
    Result := 'Existing Garage LPR service could not be removed.';
end;
