@echo off
:: Lance le script PowerShell en mode Administrateur
powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process powershell -ArgumentList '-NoProfile -ExecutionPolicy Bypass -File ""%~dp0setup_ssh_sage.ps1""' -Verb RunAs"
