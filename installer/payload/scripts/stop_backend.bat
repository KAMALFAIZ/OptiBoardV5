@echo off
REM Stoppe le service Windows OptiBoard s'il tourne
sc query OptiBoard-Backend >nul 2>&1
if %errorlevel%==0 (
    echo Arret du service OptiBoard-Backend...
    net stop OptiBoard-Backend
) else (
    echo Le service OptiBoard-Backend n'est pas installe.
    echo Si le backend tourne en mode console, fermez sa fenetre.
)
pause
