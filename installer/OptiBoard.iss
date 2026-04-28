; ======================================================================
;  OptiBoard - Installeur Windows (Python embedded + Cython)
;
;  Architecture installee:
;   C:\OptiBoard\
;     python\          <- Python 3.11 embedded (avec deps)
;     backend\         <- Code Cython (.pyd) + .pyc
;     frontend\        <- React build (Vite dist/)
;     nssm.exe                <- Service manager
;     .env                    <- Config SQL Server / Licence
;     OptiBoard-Launcher.bat  <- Lanceur intelligent (double-clic)
;
;  Service Windows: OptiBoard-Backend
;    python\python.exe backend\run_service.py
; ======================================================================

#define AppName        "OptiBoard"
#define AppVersion     "1.0.0"
#define AppPublisher   "KaSoft Maroc"
#define AppURL         "https://kasoft.ma"
#define ServiceName    "OptiBoard-Backend"
#define BackendPort    "8084"

[Setup]
AppId={{B8F7E6D5-4C3A-4B2E-9A1D-OPTIBOARD01}}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}
AppUpdatesURL={#AppURL}
DefaultDirName=C:\OptiBoard
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
OutputDir=output
OutputBaseFilename=OptiBoard-Setup-{#AppVersion}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayName={#AppName} {#AppVersion}
SetupLogging=yes
DisableDirPage=no
DisableReadyPage=no
CloseApplications=yes
RestartApplications=no
ShowLanguageDialog=no

[Languages]
Name: "french"; MessagesFile: "compiler:Languages\French.isl"

[Tasks]
Name: "desktopicon";  Description: "Creer un raccourci sur le bureau";                        GroupDescription: "Icones:"
Name: "startservice"; Description: "Installer comme service Windows (demarrage automatique)"; GroupDescription: "Service Windows:"

[InstallDelete]
; Nettoyer l'ancien backend avant mise a jour
Type: filesandordirs; Name: "{app}\backend"
Type: filesandordirs; Name: "{app}\frontend"
Type: filesandordirs; Name: "{app}\python"

[Files]
; Python 3.11 embedded (avec pip + toutes les dependances)
Source: "payload\python\*"; DestDir: "{app}\python"; Flags: ignoreversion recursesubdirs createallsubdirs

; Backend Cython compile (.pyd + .pyc)
Source: "payload\backend\*"; DestDir: "{app}\backend"; Flags: ignoreversion recursesubdirs createallsubdirs

; Frontend React compile (Vite dist/)
Source: "payload\frontend\*"; DestDir: "{app}\frontend"; Flags: ignoreversion recursesubdirs createallsubdirs

; NSSM pour service Windows
Source: "payload\nssm.exe"; DestDir: "{app}"; Flags: ignoreversion

; Template de configuration
Source: "payload\scripts\env.template"; DestDir: "{app}"; Flags: ignoreversion

; Scripts utilitaires
Source: "payload\scripts\install_service.bat";   DestDir: "{app}"; Flags: ignoreversion
Source: "payload\scripts\uninstall_service.bat"; DestDir: "{app}"; Flags: ignoreversion
Source: "payload\scripts\OptiBoard-Launcher.bat"; DestDir: "{app}"; Flags: ignoreversion
Source: "payload\scripts\start_backend.bat";      DestDir: "{app}"; Flags: ignoreversion
Source: "payload\scripts\stop_backend.bat";       DestDir: "{app}"; Flags: ignoreversion
Source: "payload\scripts\debug_optiboard.bat";    DestDir: "{app}"; Flags: ignoreversion

[Dirs]
Name: "{app}\logs";  Permissions: users-modify
Name: "{app}\data";  Permissions: users-modify

[Icons]
Name: "{group}\{#AppName}";              Filename: "{app}\OptiBoard-Launcher.bat"; WorkingDir: "{app}"; Comment: "Lancer OptiBoard"
Name: "{group}\Configurer {#AppName}";   Filename: "notepad.exe";              Parameters: "{app}\.env";  Comment: "Editer la configuration"
Name: "{group}\Logs {#AppName}";         Filename: "{app}\logs"
Name: "{group}\Desinstaller {#AppName}"; Filename: "{uninstallexe}"
Name: "{commondesktop}\{#AppName}";      Filename: "{app}\OptiBoard-Launcher.bat"; WorkingDir: "{app}"; Comment: "Lancer OptiBoard"; Tasks: desktopicon

[Run]
; 1. Creer le .env depuis le template s'il n'existe pas encore
Filename: "{cmd}"; Parameters: "/c if not exist ""{app}\.env"" copy /y ""{app}\env.template"" ""{app}\.env"""; Flags: runhidden

; 2. Installer le service Windows (si option cochee)
Filename: "{app}\install_service.bat"; \
    Parameters: "{app}"; \
    Flags: runhidden waituntilterminated; \
    Tasks: startservice; \
    StatusMsg: "Installation du service Windows OptiBoard..."

; 4. Ouvrir le navigateur apres installation
Filename: "{cmd}"; \
    Parameters: "/c timeout /t 8 /nobreak >nul & start http://127.0.0.1:{#BackendPort}"; \
    Description: "Ouvrir {#AppName} dans le navigateur"; \
    Flags: nowait postinstall skipifsilent

[UninstallRun]
Filename: "{app}\uninstall_service.bat"; Flags: runhidden waituntilterminated; RunOnceId: "StopOptiBoard"

[UninstallDelete]
Type: filesandordirs; Name: "{app}\logs"
Type: filesandordirs; Name: "{app}\data"

[Code]
procedure StopRunningOptiBoard;
var ResultCode: Integer;
begin
  Exec(ExpandConstant('{cmd}'), '/c sc stop OptiBoard-Backend >nul 2>&1', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  Exec(ExpandConstant('{cmd}'), '/c taskkill /F /IM python.exe /FI "WINDOWTITLE eq OptiBoard*" >nul 2>&1', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  Sleep(2000);
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
begin
  StopRunningOptiBoard;
  Result := '';
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usUninstall then
    StopRunningOptiBoard;
end;
