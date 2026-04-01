@echo off
cd /d D:\FinAnnee\reporting-commercial\backend
echo Demarrage du backend en arriere-plan avec logs...
start /B python run.py > backend.log 2>&1
echo Backend demarre sur http://127.0.0.1:8080
echo Logs dans: D:\FinAnnee\reporting-commercial\backend\backend.log
