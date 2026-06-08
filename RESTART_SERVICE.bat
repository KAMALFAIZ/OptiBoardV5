@echo off
:: Auto-elevation UAC
>nul 2>&1 "%SYSTEMROOT%\System32\cacls.exe" "%SYSTEMROOT%\System32\config\system"
if '%errorlevel%' NEQ '0' (
    echo Demande d'elevation administrateur...
    goto UACPrompt
) else ( goto gotAdmin )

:UACPrompt
    echo Set UAC = CreateObject^("Shell.Application"^) > "%temp%\getadmin.vbs"
    echo UAC.ShellExecute "%~s0", "", "", "runas", 1 >> "%temp%\getadmin.vbs"
    "%temp%\getadmin.vbs"
    exit /B

:gotAdmin
    if exist "%temp%\getadmin.vbs" ( del "%temp%\getadmin.vbs" )
    pushd "%CD%"
    CD /D "%~dp0"

echo ============================================================
echo   RESTART OptiBoard-Backend Service
echo ============================================================
echo.

echo [1/2] Arret du service...
net stop OptiBoard-Backend
timeout /t 3 /nobreak >nul

echo [2/2] Demarrage du service...
net start OptiBoard-Backend
timeout /t 5 /nobreak >nul

echo.
echo Verification...
sc query OptiBoard-Backend | findstr "STATE"

echo.
echo Service redemarre. Les fichiers .py mis a jour sont actifs.
echo.
pause
