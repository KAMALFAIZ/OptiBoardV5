@echo off
cd /d D:\FinAnnee\reporting-commercial\backend
echo Demarrage du backend en arriere-plan...
start /B pythonw -c "import subprocess; subprocess.run(['python', 'run.py'])" > nul 2>&1
echo Backend demarre sur http://127.0.0.1:8080
echo Logs dans backend.log
