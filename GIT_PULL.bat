@echo off
chcp 65001 >nul
title OptiBoard - Git Pull

set "REPO_DIR=%~dp0"
if "%REPO_DIR:~-1%"=="\" set "REPO_DIR=%REPO_DIR:~0,-1%"
set "REMOTE_URL=https://github.com/KAMALFAIZ/OptiBoardV5.git"

echo.
echo  ================================
echo   OptiBoard - Git Pull
echo  ================================
echo.
echo  [*] Repertoire : %REPO_DIR%
echo.

cd /d "%REPO_DIR%"

if not exist ".git" (
    echo  [!] Depot git non trouve. Initialisation du clone...
    echo.
    git init
    if %ERRORLEVEL% neq 0 ( echo  [ERREUR] git init a echoue. & pause & exit /b 1 )
    git remote add origin %REMOTE_URL%
    git fetch origin
    if %ERRORLEVEL% neq 0 ( echo  [ERREUR] Impossible de joindre le depot distant. & pause & exit /b 1 )
    git reset --hard origin/main
    if %ERRORLEVEL% neq 0 ( echo  [ERREUR] Reset a echoue. & pause & exit /b 1 )
    echo.
    echo  [OK] Clone initial termine avec succes !
    echo.
    git log --oneline -3
    echo.
    pause
    exit /b 0
)

echo  [*] Branche courante :
git branch --show-current
echo.

echo  [*] Recuperation des modifications...
echo.
git pull origin main
echo.

if %ERRORLEVEL% == 0 (
    echo  [OK] Pull termine avec succes !
) else (
    echo  [ERREUR] Le pull a echoue. Code : %ERRORLEVEL%
)

echo.
echo  Derniers commits :
git log --oneline -3
echo.
pause
