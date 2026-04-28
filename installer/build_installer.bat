@echo off
REM ======================================================================
REM  OptiBoard - Build installeur .exe (Inno Setup)
REM
REM  Pipeline:
REM    1. Telecharge Python 3.11 embedded + NSSM (avec cache)
REM    2. Decompresse Python embedded + active 'import site'
REM    3. Installe pip + requirements.txt dans le Python embedded
REM    4. Copie backend protege (dist_client) + frontend (dist)
REM    5. Compile OptiBoard.iss -> OptiBoard-Setup-1.0.0.exe
REM ======================================================================

setlocal enabledelayedexpansion
cd /d "%~dp0"

set "PY_VER=3.11.9"
set "PY_EMBED_URL=https://www.python.org/ftp/python/%PY_VER%/python-%PY_VER%-embed-amd64.zip"
set "PY_EMBED_ZIP=cache\python-embed.zip"
set "GET_PIP_URL=https://bootstrap.pypa.io/get-pip.py"
set "GET_PIP=cache\get-pip.py"
set "NSSM_URL=https://nssm.cc/release/nssm-2.24.zip"
set "NSSM_ZIP=cache\nssm.zip"

set "STAGE=payload"
set "PY_DIR=%STAGE%\python"
set "BACKEND_SRC=..\reporting-commercial\backend\dist_client"
set "FRONTEND_SRC=..\reporting-commercial\frontend\dist"
set "BACKEND_DST=%STAGE%\backend"
set "FRONTEND_DST=%STAGE%\frontend"
set "ISCC=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"

echo.
echo ======================================================================
echo   OptiBoard Installer - Build Pipeline
echo ======================================================================
echo.

REM ---------- 1. Download Python embedded ------------------------------
if not exist "%PY_EMBED_ZIP%" (
    echo [1/7] Telechargement Python %PY_VER% embedded...
    powershell -NoProfile -Command "Invoke-WebRequest -Uri '%PY_EMBED_URL%' -OutFile '%PY_EMBED_ZIP%'"
    if errorlevel 1 goto :error
) else (
    echo [1/7] Python embedded deja en cache.
)

if not exist "%GET_PIP%" (
    echo      + Telechargement get-pip.py...
    powershell -NoProfile -Command "Invoke-WebRequest -Uri '%GET_PIP_URL%' -OutFile '%GET_PIP%'"
    if errorlevel 1 goto :error
) else (
    echo      + get-pip.py deja en cache.
)

if not exist "%NSSM_ZIP%" (
    echo [2/7] Telechargement NSSM...
    powershell -NoProfile -Command "Invoke-WebRequest -Uri '%NSSM_URL%' -OutFile '%NSSM_ZIP%'"
    if errorlevel 1 goto :error
) else (
    echo [2/7] NSSM deja en cache.
)

REM ---------- 3. Extract Python embedded --------------------------------
echo [3/7] Preparation du Python embedded...
if exist "%PY_DIR%" rmdir /s /q "%PY_DIR%"
mkdir "%PY_DIR%"
powershell -NoProfile -Command "Expand-Archive -Path '%PY_EMBED_ZIP%' -DestinationPath '%PY_DIR%' -Force"
if errorlevel 1 goto :error

REM Activer 'import site' dans le ._pth (critique pour pip) ET injecter
REM ..\backend pour que 'from app...' fonctionne a l'execution.
REM IMPORTANT: Python embedded IGNORE PYTHONPATH des qu'un ._pth existe.
REM Seules les entrees listees dans ._pth sont sur sys.path. C'est pour
REM cela qu'on doit y ajouter explicitement ..\backend (relatif a python.exe).
echo     Activation import site + injection ..\backend dans python*._pth
powershell -NoProfile -Command "Get-ChildItem '%PY_DIR%\python*._pth' | ForEach-Object { $c = Get-Content $_.FullName -Raw; $c = $c -replace '#import site','import site'; if ($c -notmatch '\.\.\\backend') { $c = $c.TrimEnd() + \"`r`n..\\backend`r`n\" }; Set-Content -Path $_.FullName -Value $c -NoNewline -Encoding ASCII }"
if errorlevel 1 goto :error

REM Verification: afficher le contenu final du ._pth
echo     Contenu ._pth apres patch:
for %%f in ("%PY_DIR%\python*._pth") do type "%%f"

REM ---------- 4. Install pip + deps -------------------------------------
echo [4/7] Installation de pip dans Python embedded...
"%PY_DIR%\python.exe" "%GET_PIP%" --no-warn-script-location
if errorlevel 1 goto :error

echo [4/7] Installation des dependances OptiBoard (cela peut prendre 3-5 min)...
"%PY_DIR%\python.exe" -m pip install --no-warn-script-location --no-cache-dir -r "..\reporting-commercial\backend\requirements.txt"
if errorlevel 1 goto :error

REM Nettoyage pip cache / __pycache__ pour alleger
echo      + Nettoyage __pycache__...
for /d /r "%PY_DIR%" %%d in (__pycache__) do if exist "%%d" rmdir /s /q "%%d" 2>nul

REM ---------- 5. Extract NSSM -------------------------------------------
echo [5/7] Extraction NSSM...
if exist "%STAGE%\nssm.exe" del /q "%STAGE%\nssm.exe"
powershell -NoProfile -Command "Expand-Archive -Path '%NSSM_ZIP%' -DestinationPath 'cache\nssm' -Force"
if errorlevel 1 goto :error
copy /y "cache\nssm\nssm-2.24\win64\nssm.exe" "%STAGE%\nssm.exe" >nul
if errorlevel 1 goto :error

REM ---------- 6. Copy backend + frontend -------------------------------
echo [6/7] Copie du backend protege et du frontend...
if not exist "%BACKEND_SRC%" (
    echo ERREUR: backend non compile. Lancez d'abord:
    echo    cd ..\reporting-commercial\backend ^&^& build_protected.bat
    goto :error
)
if not exist "%FRONTEND_SRC%" (
    echo ERREUR: frontend non build. Lancez d'abord:
    echo    cd ..\reporting-commercial\frontend ^&^& npm run build
    goto :error
)

if exist "%BACKEND_DST%" rmdir /s /q "%BACKEND_DST%"
if exist "%FRONTEND_DST%" rmdir /s /q "%FRONTEND_DST%"

xcopy /e /i /q /y "%BACKEND_SRC%" "%BACKEND_DST%" >nul
if errorlevel 1 goto :error
xcopy /e /i /q /y "%FRONTEND_SRC%" "%FRONTEND_DST%" >nul
if errorlevel 1 goto :error

REM Ne PAS embarquer le .env du dev !
if exist "%BACKEND_DST%\.env" del /q "%BACKEND_DST%\.env"

REM ---------- 7. Compile installer --------------------------------------
echo [7/7] Compilation Inno Setup -^> OptiBoard-Setup-1.0.0.exe
if not exist "%ISCC%" goto :inno_missing

if not exist "output" mkdir output

call "%ISCC%" /Qp "OptiBoard.iss"
if errorlevel 1 goto :error

echo.
echo ======================================================================
echo   BUILD OK
echo   Installeur: %~dp0output\OptiBoard-Setup-1.0.0.exe
echo ======================================================================
exit /b 0

:inno_missing
echo.
echo ERREUR: Inno Setup non trouve.
echo Chemin attendu: ISCC.exe dans "Inno Setup 6"
goto :error

:error
echo.
echo ======================================================================
echo   BUILD ECHEC
echo ======================================================================
exit /b 1
