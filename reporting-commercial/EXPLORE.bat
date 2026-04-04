@echo off
chcp 65001 >nul
title OptiBoard - Demarrage Complet
color 0A

echo.
echo  ╔══════════════════════════════════════════╗
echo  ║   OptiBoard - Reporting Commercial       ║
echo  ║   KAsoft                                 ║
echo  ╚══════════════════════════════════════════╝
echo.

REM ── Arreter les anciens processus ──
echo  [1/4] Nettoyage des anciens processus...
taskkill /F /IM node.exe 2>nul
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8080.*LISTENING" 2^>nul') do (
    taskkill /F /PID %%a 2>nul
)
timeout /t 2 /nobreak >nul
echo        OK
echo.

REM ── Demarrer le Backend ──
echo  [2/4] Demarrage du Backend (port 8080)...
cd /d "D:\FinAnnee\reporting-commercial\backend"
start "OptiBoard Backend" /min cmd /k "cd /d D:\FinAnnee\reporting-commercial\backend && call venv\Scripts\activate.bat 2>nul && python run.py"
echo        Backend lance.
echo.

REM ── Attendre le backend ──
echo  [3/4] Attente du backend...
timeout /t 5 /nobreak >nul
echo        OK
echo.

REM ── Demarrer le Frontend ──
echo  [4/4] Demarrage du Frontend (port 3003)...
cd /d "D:\FinAnnee\reporting-commercial\frontend"
start "OptiBoard Frontend" /min cmd /k "cd /d D:\FinAnnee\reporting-commercial\frontend && npm run dev"
timeout /t 3 /nobreak >nul
echo        Frontend lance.
echo.

echo  ╔══════════════════════════════════════════╗
echo  ║   Serveurs demarres avec succes !         ║
echo  ║                                           ║
echo  ║   Backend:  http://localhost:8080          ║
echo  ║   Frontend: http://localhost:3003          ║
echo  ║   API Docs: http://localhost:8080/api/docs ║
echo  ╚══════════════════════════════════════════╝
echo.

echo  Ouverture du navigateur...
timeout /t 2 /nobreak >nul
start http://localhost:3003

echo.
echo  Appuyez sur une touche pour fermer cette fenetre...
pause >nul
