@echo off
REM ======================================================================
REM  OptiBoard - Build Installeur
REM
REM  Pipeline [7 etapes] :
REM    [1/7] Download Python 3.11.9 embedded (cache)
REM    [2/7] NSSM 2.24 (cache ou local)
REM    [3/7] Extract Python embedded -> payload\python\
REM    [4/7] Patch python311._pth (import site + ..\backend)
REM    [5/7] pip install requirements.txt dans Python embedded
REM    [6/7] Copie backend (dist_client) + frontend (dist) -> payload\
REM    [7/7] ISCC.exe -> output\OptiBoard-Setup-1.0.0.exe
REM
REM  Prerequis :
REM    - Inno Setup 6 installe dans "C:\Program Files (x86)\Inno Setup 6\"
REM    - dist_client\ a jour (lancer build_protected.bat)
REM    - frontend\dist\ a jour (lancer npm run build)
REM    - Acces Internet OU nssm.exe fourni dans installer\nssm_local.exe
REM ======================================================================

setlocal EnableExtensions EnableDelayedExpansion

set "INSTALLER_DIR=%~dp0"
set "ROOT=%INSTALLER_DIR%.."
set "BACKEND_SRC=%ROOT%\reporting-commercial\backend\dist_client"
set "FRONTEND_SRC=%ROOT%\reporting-commercial\frontend\dist"
set "PAYLOAD=%INSTALLER_DIR%payload"
set "CACHE=%INSTALLER_DIR%cache"
set "OUTPUT=%INSTALLER_DIR%output"
set PF86=C:\Program Files (x86)
set "ISCC=%PF86%\Inno Setup 6\ISCC.exe"

set "PYTHON_VER=3.11.9"
set "PYTHON_ZIP=python-3.11.9-embed-amd64.zip"
set "PYTHON_URL=https://www.python.org/ftp/python/3.11.9/python-3.11.9-embed-amd64.zip"

set "NSSM_VER=2.24"
set "NSSM_ZIP=nssm-2.24.zip"
set "NSSM_URL=https://nssm.cc/release/nssm-2.24.zip"

set "T_START=%TIME%"
set "BUILD_OK=1"

echo.
echo ======================================================================
echo   OptiBoard - BUILD INSTALLEUR
echo ======================================================================
echo   Installer : %INSTALLER_DIR%
echo   Backend   : %BACKEND_SRC%
echo   Frontend  : %FRONTEND_SRC%
echo   Demarrage : %T_START%
echo ======================================================================
echo.

REM ---- Verification des prerequis ----------------------------------------
if not exist "!ISCC!" set "BUILD_OK=0" & echo [ERREUR] Inno Setup 6 introuvable : !ISCC! & echo Installez depuis https://jrsoftware.org/isinfo.php & goto :build_failed
if not exist "%BACKEND_SRC%" set "BUILD_OK=0" & echo [ERREUR] dist_client introuvable. Lancez build_protected.bat & goto :build_failed
if not exist "%FRONTEND_SRC%" set "BUILD_OK=0" & echo [ERREUR] frontend\dist introuvable. Lancez npm run build & goto :build_failed

REM ---- Creer les repertoires necessaires ---------------------------------
if not exist "%CACHE%"            mkdir "%CACHE%"
if not exist "%PAYLOAD%\python"   mkdir "%PAYLOAD%\python"
if not exist "%PAYLOAD%\backend"  mkdir "%PAYLOAD%\backend"
if not exist "%PAYLOAD%\frontend" mkdir "%PAYLOAD%\frontend"
if not exist "%PAYLOAD%\scripts"  mkdir "%PAYLOAD%\scripts"
if not exist "%OUTPUT%"           mkdir "%OUTPUT%"

REM ======================================================================
REM  [1/7] Download Python 3.11.9 embedded
REM ======================================================================
echo [1/7] Python %PYTHON_VER% embedded...
if exist "%CACHE%\%PYTHON_ZIP%" (
    echo       Cache trouve : %CACHE%\%PYTHON_ZIP%
    goto :step2
)
echo       Telechargement depuis %PYTHON_URL%...
powershell -NoProfile -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; (New-Object Net.WebClient).DownloadFile('%PYTHON_URL%', '%CACHE%\%PYTHON_ZIP%')"
if not exist "%CACHE%\%PYTHON_ZIP%" (
    echo [ERREUR] Echec du telechargement Python
    goto :build_failed
)
echo       Telechargement OK
:step2
echo.

REM ======================================================================
REM  [2/7] NSSM 2.24 (cache / telechargement / local)
REM ======================================================================
echo [2/7] NSSM %NSSM_VER%...

REM Si deja dans le cache -> OK
if exist "%CACHE%\nssm.exe" (
    echo       nssm.exe en cache
    goto :step3
)

REM Si fourni localement (installer\nssm_local.exe)
if exist "%INSTALLER_DIR%nssm_local.exe" (
    echo       Copie depuis nssm_local.exe...
    copy /y "%INSTALLER_DIR%nssm_local.exe" "%CACHE%\nssm.exe" >nul
    goto :step3
)

REM Tenter le telechargement du ZIP
if not exist "%CACHE%\%NSSM_ZIP%" (
    echo       Telechargement depuis %NSSM_URL%...
    powershell -NoProfile -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; try { (New-Object Net.WebClient).DownloadFile('%NSSM_URL%', '%CACHE%\%NSSM_ZIP%') } catch { Write-Warning $_.Exception.Message }"
)

if exist "%CACHE%\%NSSM_ZIP%" (
    echo       Extraction nssm.exe depuis ZIP...
    set "NSSM_EXTRACT=%CACHE%\nssm_extract"
    if not exist "!NSSM_EXTRACT!" mkdir "!NSSM_EXTRACT!"
    powershell -NoProfile -Command "Expand-Archive -Path '%CACHE%\%NSSM_ZIP%' -DestinationPath '%CACHE%\nssm_extract' -Force"
    if exist "%CACHE%\nssm_extract\nssm-%NSSM_VER%\win64\nssm.exe" (
        copy /y "%CACHE%\nssm_extract\nssm-%NSSM_VER%\win64\nssm.exe" "%CACHE%\nssm.exe" >nul
        goto :step3
    )
)

echo [ERREUR] nssm.exe introuvable.
echo   Options :
echo     1. Placez nssm.exe dans : %INSTALLER_DIR%nssm_local.exe
echo     2. Verifiez votre acces Internet (nssm.cc)
goto :build_failed

:step3
echo       nssm.exe OK
echo.

REM ======================================================================
REM  [3/7] Extraire Python embedded -> payload\python\
REM ======================================================================
echo [3/7] Extraction Python embedded...
if exist "%PAYLOAD%\python\python.exe" (
    echo       Nettoyage prealable de payload\python\...
    rmdir /s /q "%PAYLOAD%\python"
    mkdir "%PAYLOAD%\python"
)
powershell -NoProfile -Command "Expand-Archive -Path '%CACHE%\%PYTHON_ZIP%' -DestinationPath '%PAYLOAD%\python' -Force"
if not exist "%PAYLOAD%\python\python.exe" (
    echo [ERREUR] Extraction Python echouee
    goto :build_failed
)
echo       python.exe extrait dans payload\python\
echo.

REM ======================================================================
REM  [4/7] Patcher python311._pth
REM ======================================================================
echo [4/7] Patch python311._pth...
set "PTH_FILE=%PAYLOAD%\python\python311._pth"
if not exist "%PTH_FILE%" (
    echo [ERREUR] python311._pth introuvable dans payload\python\
    goto :build_failed
)

copy /y "%PTH_FILE%" "%PTH_FILE%.orig" >nul
(
    echo python311.zip
    echo .
    echo ..\backend
    echo.
    echo import site
) > "%PTH_FILE%"

echo       Contenu de python311._pth :
type "%PTH_FILE%"
echo.

REM ======================================================================
REM  [5/7] pip install requirements.txt dans Python embedded
REM ======================================================================
echo [5/7] Installation des dependances Python...
set "EMBEDDED_PY=%PAYLOAD%\python\python.exe"
set "REQS=%BACKEND_SRC%\requirements.txt"

if not exist "%REQS%" (
    echo [ERREUR] requirements.txt introuvable : %REQS%
    goto :build_failed
)

if not exist "%CACHE%\get-pip.py" (
    echo       Telechargement get-pip.py...
    powershell -NoProfile -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; (New-Object Net.WebClient).DownloadFile('https://bootstrap.pypa.io/get-pip.py', '%CACHE%\get-pip.py')"
)

if not exist "%PAYLOAD%\python\Scripts\pip.exe" (
    echo       Installation de pip...
    "%EMBEDDED_PY%" "%CACHE%\get-pip.py" --no-warn-script-location
    if errorlevel 1 (
        echo [ERREUR] Installation pip echouee
        goto :build_failed
    )
)

echo       pip install requirements.txt...
"%PAYLOAD%\python\Scripts\pip.exe" install --no-warn-script-location -r "%REQS%" --target "%PAYLOAD%\python\Lib\site-packages"
if errorlevel 1 (
    echo [ERREUR] pip install requirements.txt echoue
    goto :build_failed
)
echo       Dependances installees OK
echo.

REM ======================================================================
REM  [6/7] Copie backend + frontend + scripts -> payload\
REM ======================================================================
echo [6/7] Copie des fichiers sources...

echo       Backend dist_client -> payload\backend\
if exist "%PAYLOAD%\backend" rmdir /s /q "%PAYLOAD%\backend"
mkdir "%PAYLOAD%\backend"
xcopy /e /i /q /y "%BACKEND_SRC%" "%PAYLOAD%\backend"
if errorlevel 1 (
    echo [ERREUR] Copie backend echouee
    goto :build_failed
)

echo       Frontend dist -> payload\frontend\
if exist "%PAYLOAD%\frontend" rmdir /s /q "%PAYLOAD%\frontend"
mkdir "%PAYLOAD%\frontend"
xcopy /e /i /q /y "%FRONTEND_SRC%" "%PAYLOAD%\frontend"
if errorlevel 1 (
    echo [ERREUR] Copie frontend echouee
    goto :build_failed
)

echo       Scripts -> payload\scripts\
copy /y "%INSTALLER_DIR%payload\scripts\install_service.bat"    "%PAYLOAD%\scripts\" >nul
copy /y "%INSTALLER_DIR%payload\scripts\uninstall_service.bat"  "%PAYLOAD%\scripts\" >nul
copy /y "%INSTALLER_DIR%payload\scripts\OptiBoard-Launcher.bat" "%PAYLOAD%\scripts\" >nul
copy /y "%INSTALLER_DIR%payload\scripts\FIX_SERVICE.bat"        "%PAYLOAD%\scripts\" >nul
copy /y "%INSTALLER_DIR%payload\scripts\FIX_ADMIN_CLIENT.ps1"   "%PAYLOAD%\scripts\" >nul

echo       NSSM -> payload\nssm.exe
copy /y "%CACHE%\nssm.exe" "%PAYLOAD%\nssm.exe" >nul
if not exist "%PAYLOAD%\nssm.exe" (
    echo [ERREUR] nssm.exe absent du payload
    goto :build_failed
)
echo.

REM ======================================================================
REM  [7/7] ISCC.exe -> output\OptiBoard-Setup-1.0.0.exe
REM ======================================================================
echo [7/7] Compilation Inno Setup...
"!ISCC!" "%INSTALLER_DIR%OptiBoard.iss"
if errorlevel 1 (
    echo [ERREUR] Inno Setup ISCC.exe a echoue
    goto :build_failed
)

REM ---- Recap final -------------------------------------------------------
set "EXE=%OUTPUT%\OptiBoard-Setup-1.0.0.exe"
set "T_END=%TIME%"

echo.
echo ======================================================================
echo   BUILD INSTALLEUR TERMINE
echo ======================================================================
if exist "%EXE%" (
    for %%I in ("%EXE%") do set "SIZE_BYTES=%%~zI"
    set /a SIZE_MB=!SIZE_BYTES! / 1048576
    echo   Installeur : %EXE%
    echo   Taille     : !SIZE_MB! MB
) else (
    echo   ATTENTION: %EXE% introuvable
)
echo   Demarrage  : %T_START%
echo   Fin        : %T_END%
echo ======================================================================
echo.
endlocal
exit /b 0

:build_failed
echo.
echo ======================================================================
echo   BUILD INSTALLEUR ECHEC
echo ======================================================================
endlocal
exit /b 1
