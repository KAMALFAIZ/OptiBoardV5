@echo off
echo Arret du backend...
taskkill /F /IM python.exe /FI "WINDOWTITLE eq *run.py*" 2>nul
netstat -ano | findstr :8080 | for /f "tokens=5" %%a in ('more') do taskkill /F /PID %%a 2>nul
echo Backend arrete.
