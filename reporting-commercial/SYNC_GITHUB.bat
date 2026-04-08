@echo off
REM ============================================================
REM  SYNC_GITHUB.bat
REM  Export BD OptiBoard_SaaS + Commit + Push GitHub
REM  Double-cliquer pour lancer
REM ============================================================

cd /d "D:\kasoft-platform\OptiBoard\reporting-commercial"

echo.
echo ============================================================
echo   Synchronisation OptiBoard → GitHub
echo ============================================================
echo.

REM ── 1. Export base de données ────────────────────────────────
echo [1/4] Export de la base de donnees OptiBoard_SaaS...
echo.

call backend\venv\Scripts\activate.bat 2>nul

python backend\sql\export_db.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ERREUR : Export base de donnees echoue !
    echo Verifiez la connexion SQL Server.
    pause
    exit /b 1
)

echo.

REM ── 2. Vérifier Git ──────────────────────────────────────────
echo [2/4] Verification Git...
git --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ERREUR : Git n'est pas installe ou pas dans le PATH.
    echo Telechargez Git depuis https://git-scm.com
    pause
    exit /b 1
)

REM ── 3. Ajouter les fichiers modifiés ─────────────────────────
echo [3/4] Preparation du commit...
echo.

REM Fichiers de code (backend + frontend)
git add backend\app\routes\*.py
git add backend\app\services\*.py
git add backend\app\database_unified.py
git add backend\app\config.py
git add backend\sql\exports\*.sql
git add backend\sql\*.sql
git add frontend\src\pages\*.jsx
git add frontend\src\components\**\*.jsx
git add frontend\src\services\api.js

REM Ne PAS versionner les fichiers sensibles
git reset HEAD backend\.env 2>nul
git reset HEAD backend\venv\ 2>nul
git reset HEAD **\__pycache__\ 2>nul

REM Afficher ce qui va être commité
echo.
echo Fichiers modifies :
git status --short
echo.

REM ── 4. Commit + Push ─────────────────────────────────────────
echo [4/4] Commit et Push vers GitHub...
echo.

REM Message de commit automatique avec date/heure
set TIMESTAMP=%date:~6,4%-%date:~3,2%-%date:~0,2% %time:~0,5%
set MSG=sync: export BD + code [%TIMESTAMP%]

git commit -m "%MSG%"

if %ERRORLEVEL% EQU 0 (
    echo.
    echo Push vers GitHub...
    git push origin main
    if %ERRORLEVEL% EQU 0 (
        echo.
        echo ============================================================
        echo   Synchronisation terminee avec succes !
        echo   Commit : %MSG%
        echo ============================================================
    ) else (
        echo.
        echo ERREUR Push : verifiez votre connexion et vos droits GitHub.
        echo Essayez : git push origin main --verbose
    )
) else (
    echo.
    echo Aucune modification a commiter.
    echo La base de donnees et le code sont deja a jour sur GitHub.
)

echo.
pause
