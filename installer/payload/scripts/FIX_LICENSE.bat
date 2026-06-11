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

:: Secrets NON versionnes — saisis a l'execution (ou pre-remplis via variables d'env).
if "%LIC_KEY%"=="" set /p "LIC_KEY=Collez la cle de licence (LICENSE_KEY) : "
if "%LIC_SECRET%"=="" set /p "LIC_SECRET=Collez le secret de signature (LICENSE_SIGNING_SECRET) : "
if "%LIC_KEY%"=="" ( echo ERREUR : cle de licence vide. & pause & exit /b 1 )
if "%LIC_SECRET%"=="" ( echo ERREUR : secret de signature vide. & pause & exit /b 1 )

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
