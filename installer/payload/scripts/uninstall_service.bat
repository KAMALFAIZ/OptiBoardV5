@echo off
REM Supprime proprement le service Windows OptiBoard
set "APP_DIR=%~dp0"
set "NSSM=%APP_DIR%nssm.exe"
set "SVC=OptiBoard-Backend"

sc query %SVC% >nul 2>&1
if %errorlevel%==0 (
    "%NSSM%" stop %SVC% >nul 2>&1
    "%NSSM%" remove %SVC% confirm >nul 2>&1
)
exit /b 0
