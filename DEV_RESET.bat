@echo off
chcp 65001 >nul
title OptiBoard - Reinitialisation Dev

set "ROOT=D:\kasoft-platform\OptiBoard"
set "FRONTEND=%ROOT%\reporting-commercial\frontend"

echo.
echo  ==========================================
echo       OptiBoard - Reinitialisation
echo  ==========================================
echo.

REM -- 1. Tuer Node/Vite ------------------------------------------------------
echo [1/4] Arret des processus Node/Vite...
taskkill /IM "node.exe" /F >nul 2>&1
echo      OK.

REM -- 2. Vider le cache Vite -------------------------------------------------
echo [2/4] Suppression du cache Vite...
if exist "%FRONTEND%\node_modules\.vite" (
    rd /s /q "%FRONTEND%\node_modules\.vite"
    echo      Cache Vite supprime.
) else (
    echo      Pas de cache Vite.
)

REM -- 3. Verifier node_modules -----------------------------------------------
echo [3/4] Verification des dependances npm...
if not exist "%FRONTEND%\node_modules" (
    echo      node_modules absent - npm install en cours...
    pushd "%FRONTEND%"
    npm install
    popd
) else (
    echo      node_modules OK.
)

REM -- 4. Info localStorage ---------------------------------------------------
echo [4/4] Pour reset complet de l'affichage :
echo      Ouvrir DevTools (F12) - Application - Local Storage
echo      Supprimer les cles ag-grid-* puis Ctrl+Shift+R

echo.
echo  Reinitialisation terminee. Lancez DEV_START.bat.
echo.
pause
