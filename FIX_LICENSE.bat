@echo off
:: FIX_LICENSE.bat — Injecte la cle de licence dans C:\OptiBoard\backend\.env
:: Copier ce fichier dans C:\OptiBoard\ sur la machine cliente et executer en tant qu'Administrateur

setlocal

:: Detecter le dossier d'installation
set "INSTALL_DIR=%~dp0"
if "%INSTALL_DIR:~-1%"=="\" set "INSTALL_DIR=%INSTALL_DIR:~0,-1%"

set "ENV_FILE=%INSTALL_DIR%\backend\.env"
set "CACHE_FILE=%INSTALL_DIR%\.license_cache"

if not exist "%ENV_FILE%" (
    echo ERREUR : .env introuvable : %ENV_FILE%
    echo Verifiez que OptiBoard est installe dans %INSTALL_DIR%
    pause
    exit /b 1
)

set "LIC_KEY=eyJvcmciOiJLQVNPRlQiLCJtaWQiOiIqIiwicGxhbiI6InByZW1pdW0iLCJtYXhfdSI6MTAsIm1heF9kIjo1LCJmZWF0IjpbImFsbCJdLCJleHAiOiIyMDI4LTAzLTI0IiwiaWF0IjoxNzc0NDIzMjA5LCJtb2RlIjoib24tcHJlbWlzZSJ9.982c5f96c0c1b3a5efd202e765b6d99bf3b74ed8027184a836abbd5ea78e1175"
set "LIC_SECRET=F36XJAyo4dHrXMtcDH_i17swtkTw2BxQVx78gPN9vxOyRVkXD7E0DG20roR7hqev"

echo Mise a jour de la licence dans : %ENV_FILE%

:: Supprimer les lignes existantes (LICENSE_KEY et LICENSE_SIGNING_SECRET)
powershell -Command "(Get-Content '%ENV_FILE%') | Where-Object { $_ -notmatch '^LICENSE_KEY=' -and $_ -notmatch '^LICENSE_SIGNING_SECRET=' } | Set-Content '%ENV_FILE%' -Encoding utf8"

:: Ajouter les nouvelles valeurs
echo LICENSE_KEY=%LIC_KEY%>> "%ENV_FILE%"
echo LICENSE_SIGNING_SECRET=%LIC_SECRET%>> "%ENV_FILE%"

:: Supprimer le cache licence si present
if exist "%CACHE_FILE%" (
    del /f "%CACHE_FILE%"
    echo Cache licence supprime : %CACHE_FILE%
)

echo.
echo ===========================================================
echo  LICENCE MISE A JOUR
echo  Organisation : KASOFT
echo  Plan         : Premium
echo  Expire le    : 24/03/2028
echo ===========================================================
echo.
echo Redemarrage du service OptiBoard-Backend...
net stop OptiBoard-Backend >nul 2>&1
timeout /t 2 /nobreak >nul
net start OptiBoard-Backend >nul 2>&1
if %errorlevel%==0 (
    echo Service redémarre avec succes.
) else (
    echo ATTENTION : Le service n a pas pu etre redémarre automatiquement.
    echo Redemarrez manuellement via : Services Windows ou nssm restart OptiBoard-Backend
)
echo.
pause
