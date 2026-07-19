@echo off
REM ======================================================================
REM  OptiBoard - Deploiement backend (auto-eleve en admin)
REM  Double-clique ce fichier : il demande l'elevation UAC puis deploie
REM  dist_client vers C:\OptiBoard\backend et redemarre le service.
REM ======================================================================

REM --- Auto-elevation ---
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo Demande d'elevation administrateur...
    powershell -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
    exit /b
)

set "PS1=%~dp0deploy_backend.ps1"
echo Lancement du deploiement : %PS1%
powershell -NoProfile -ExecutionPolicy Bypass -File "%PS1%"
