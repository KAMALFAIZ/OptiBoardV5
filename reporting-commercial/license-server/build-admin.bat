@echo off
echo ==========================================
echo   Build Admin Panel
echo ==========================================
echo.

cd admin-panel

echo [1/2] Installation des dependances...
call npm install

echo.
echo [2/2] Build de production...
call npm run build

echo.
echo Build termine ! Le panel admin sera servi automatiquement par le serveur.
echo Demarrez le serveur avec: python main.py
echo.
pause
