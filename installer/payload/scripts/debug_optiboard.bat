@echo off
title OptiBoard - Diagnostic
cd /d "%~dp0"
echo.
echo ============================================
echo   OptiBoard - Lancement Diagnostic
echo   Dossier: %~dp0
echo ============================================
echo.

REM Verifier le .env
if exist ".env" (
    echo [OK] Fichier .env trouve
    type .env
) else (
    echo [ERREUR] Fichier .env MANQUANT - copie depuis template...
    if exist "env.template" (
        copy env.template .env
        echo [OK] .env cree depuis template
    ) else (
        echo [ERREUR] env.template aussi manquant!
    )
)

echo.
echo ============================================
echo   Demarrage OptiBoard.exe (logs ci-dessous)
echo ============================================
echo.

REM Lancer et capturer les logs
OptiBoard.exe > logs\debug_output.txt 2>&1

echo.
echo ============================================
echo   OptiBoard s'est arrete. Logs:
echo ============================================
type logs\debug_output.txt

echo.
echo Appuyez sur une touche pour fermer...
pause > nul
