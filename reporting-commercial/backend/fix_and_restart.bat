@echo off
echo ===== CORRECTION DES SOURCES DE DONNEES =====
echo.

REM Aller dans le dossier backend
cd /d D:\FinAnnee\reporting-commercial\backend

REM Arreter tous les processus Python sur le port 8081
echo Arret du serveur backend...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8081') do taskkill /F /PID %%a 2>nul

REM Attendre un peu
timeout /t 2 /nobreak >nul

REM Executer le script de reset des sources
echo.
echo Reinitialisation des sources de donnees...
call venv\Scripts\python.exe reset_datasources.py

REM Redemarrer le serveur
echo.
echo Demarrage du serveur backend...
start "Backend Server" cmd /c "venv\Scripts\python.exe run.py"

echo.
echo ===== TERMINE =====
echo Le serveur backend demarre sur http://localhost:8081
echo Attendez quelques secondes puis rafraichissez la page.
pause
