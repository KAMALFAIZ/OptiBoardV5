@echo off
:: FIX_LICENSE.bat — Injecte la cle de licence et le secret de signature dans .env
:: A executer UNE SEULE FOIS sur la machine cliente
:: Necessite les droits Administrateur

setlocal

set "ENV_FILE=%~dp0..\..\backend\.env"
if not exist "%ENV_FILE%" (
    echo ERREUR : .env introuvable : %ENV_FILE%
    exit /b 1
)

set "LIC_KEY=eyJvcmciOiJLQVNPRlQiLCJtaWQiOiIqIiwicGxhbiI6InByZW1pdW0iLCJtYXhfdSI6MTAsIm1heF9kIjo1LCJmZWF0IjpbImFsbCJdLCJleHAiOiIyMDI4LTAzLTI0IiwiaWF0IjoxNzc0NDIzMjA5LCJtb2RlIjoib24tcHJlbWlzZSJ9.982c5f96c0c1b3a5efd202e765b6d99bf3b74ed8027184a836abbd5ea78e1175"
set "LIC_SECRET=F36XJAyo4dHrXMtcDH_i17swtkTw2BxQVx78gPN9vxOyRVkXD7E0DG20roR7hqev"

:: Supprimer les lignes existantes
powershell -Command "(Get-Content '%ENV_FILE%') | Where-Object { $_ -notmatch '^LICENSE_KEY=' -and $_ -notmatch '^LICENSE_SIGNING_SECRET=' } | Set-Content '%ENV_FILE%' -Encoding utf8"

:: Ajouter les nouvelles valeurs
echo LICENSE_KEY=%LIC_KEY%>> "%ENV_FILE%"
echo LICENSE_SIGNING_SECRET=%LIC_SECRET%>> "%ENV_FILE%"

:: Supprimer le cache licence si present
if exist "%~dp0..\..\..\.license_cache" (
    del /f "%~dp0..\..\..\.license_cache"
    echo Cache licence supprime.
)

echo.
echo OK — Licence et secret mis a jour dans %ENV_FILE%
echo Redemarrez le service OptiBoard-Backend pour appliquer.
echo.
pause
