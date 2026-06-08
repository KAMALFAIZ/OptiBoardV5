; ======================================================================
;  OptiBoard - Script Inno Setup 6
;  Genere : output\OptiBoard-Setup-1.0.0.exe
;
;  Structure installee dans C:\OptiBoard\ :
;    python\     <- Python 3.11 embedded + dependances
;    backend\    <- Code compile (dist_client : .pyd + .pyc)
;    frontend\   <- React app (dist Vite)
;    nssm.exe    <- Service manager Windows
;    .env        <- Template vide (configure via wizard)
;    logs\       <- backend.log + backend.error.log
;    OptiBoard-Launcher.bat
;    install_service.bat / uninstall_service.bat
;    FIX_SERVICE.bat / FIX_ADMIN_CLIENT.ps1
; ======================================================================

#define AppName        "OptiBoard"
#define AppVersion     "1.0.0"
#define AppPublisher   "KAsoft"
#define AppURL         "https://kasoft.ma"
#define AppExeName     "OptiBoard-Launcher.bat"
#define ServiceName    "OptiBoard-Backend"
#define InstallDir     "C:\OptiBoard"

[Setup]
AppId={{E4B2C1A3-7F5D-4E9B-B3C8-2A6F1D8E0C47}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}
AppUpdatesURL={#AppURL}
DefaultDirName={#InstallDir}
DisableDirPage=no
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
OutputDir=output
OutputBaseFilename=OptiBoard-Setup-1.0.0
Compression=lzma2/ultra64
SolidCompression=yes
LZMAUseSeparateProcess=yes
InternalCompressLevel=ultra
PrivilegesRequired=admin
WizardStyle=modern
WizardSmallImageFile=
ShowLanguageDialog=no
LanguageDetectionMethod=locale
UninstallDisplayIcon={app}\nssm.exe
SetupIconFile=
VersionInfoVersion={#AppVersion}
VersionInfoCompany={#AppPublisher}
VersionInfoDescription={#AppName} Installation
VersionInfoProductName={#AppName}
CloseApplications=yes
CloseApplicationsFilter=*.exe
RestartApplications=no
MinVersion=6.1

[Languages]
Name: "french"; MessagesFile: "compiler:Languages\French.isl"

[Messages]
BeveledLabel={#AppName} v{#AppVersion} par {#AppPublisher}

[Tasks]
Name: "desktopicon"; Description: "Creer une icone sur le Bureau"; GroupDescription: "Icones supplementaires"; Flags: unchecked

[Dirs]
Name: "{app}\logs"; Flags: uninsneveruninstall

[Files]
; ---- Python 3.11 embedded -----------------------------------------------
Source: "payload\python\*"; DestDir: "{app}\python"; \
    Flags: ignoreversion recursesubdirs createallsubdirs; \
    Excludes: "*.pdb"

; ---- Backend compile (dist_client) ---------------------------------------
Source: "payload\backend\*"; DestDir: "{app}\backend"; \
    Flags: ignoreversion recursesubdirs createallsubdirs

; ---- Frontend React (Vite dist) -----------------------------------------
Source: "payload\frontend\*"; DestDir: "{app}\frontend"; \
    Flags: ignoreversion recursesubdirs createallsubdirs

; ---- NSSM ----------------------------------------------------------------
Source: "payload\nssm.exe"; DestDir: "{app}"; \
    Flags: ignoreversion

; ---- Scripts utilitaires -------------------------------------------------
Source: "payload\scripts\install_service.bat"; DestDir: "{app}"; \
    Flags: ignoreversion
Source: "payload\scripts\uninstall_service.bat"; DestDir: "{app}"; \
    Flags: ignoreversion
Source: "payload\scripts\OptiBoard-Launcher.bat"; DestDir: "{app}"; \
    Flags: ignoreversion
Source: "payload\scripts\FIX_SERVICE.bat"; DestDir: "{app}"; \
    Flags: ignoreversion
Source: "payload\scripts\FIX_ADMIN_CLIENT.ps1"; DestDir: "{app}"; \
    Flags: ignoreversion

[Icons]
Name: "{group}\OptiBoard"; \
    Filename: "{app}\OptiBoard-Launcher.bat"; \
    Comment: "Lancer OptiBoard"
Name: "{group}\{cm:UninstallProgram,{#AppName}}"; \
    Filename: "{uninstallexe}"
Name: "{commondesktop}\OptiBoard"; \
    Filename: "{app}\OptiBoard-Launcher.bat"; \
    Comment: "Lancer OptiBoard"; \
    Tasks: desktopicon

[Run]
; Installer le service Windows apres la copie des fichiers
Filename: "{cmd}"; \
    Parameters: "/c ""{app}\install_service.bat"" ""{app}"""; \
    WorkingDir: "{app}"; \
    StatusMsg: "Installation du service Windows OptiBoard..."; \
    Flags: runhidden waituntilterminated

; Lancer le navigateur apres installation
Filename: "{app}\OptiBoard-Launcher.bat"; \
    Description: "Lancer OptiBoard maintenant"; \
    Flags: nowait postinstall skipifsilent unchecked

[UninstallRun]
; Arreter et supprimer le service avant desinstallation
Filename: "{cmd}"; \
    Parameters: "/c ""{app}\uninstall_service.bat"" ""{app}"""; \
    WorkingDir: "{app}"; \
    RunOnceId: "StopAndRemoveService"; \
    Flags: runhidden waituntilterminated

[Code]
// Creer le fichier .env vide si absent
procedure CreateEnvIfMissing();
var
  EnvFile: String;
begin
  EnvFile := ExpandConstant('{app}\backend\.env');
  if not FileExists(EnvFile) then
  begin
    // Creer le repertoire backend si absent
    ForceDirectories(ExpandConstant('{app}\backend'));
    SaveStringToFile(EnvFile,
      '# OptiBoard Configuration' + #13#10 +
      '# Ce fichier est configure automatiquement par le wizard de setup.' + #13#10 +
      '# Ne pas modifier manuellement.' + #13#10 +
      '' + #13#10 +
      'DB_SERVER=' + #13#10 +
      'DB_PORT=1433' + #13#10 +
      'DB_NAME=OptiBoard_SaaS' + #13#10 +
      'DB_USER=' + #13#10 +
      'DB_PASSWORD=' + #13#10 +
      'APP_NAME=OptiBoard' + #13#10 +
      'DEBUG=False' + #13#10 +
      'SECRET_KEY=' + #13#10 +
      'LICENSE_KEY=' + #13#10,
      False);
  end;
end;

// Creer le repertoire logs
procedure CreateLogsDir();
begin
  ForceDirectories(ExpandConstant('{app}\logs'));
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    CreateEnvIfMissing();
    CreateLogsDir();
  end;
end;
