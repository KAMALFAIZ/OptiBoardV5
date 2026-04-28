@echo off
REM =========================================================
REM Script de lancement des tests OptiBoard
REM Usage : run_tests.bat [backend|frontend|all]
REM =========================================================
setlocal

set OPTION=%1
if "%OPTION%"=="" set OPTION=all

echo.
echo =====================================================
echo   OptiBoard - Suite de Tests Globale
echo =====================================================
echo.

if "%OPTION%"=="backend" goto backend
if "%OPTION%"=="frontend" goto frontend
if "%OPTION%"=="all" goto all

echo Usage: run_tests.bat [backend^|frontend^|all]
exit /b 1

:backend
echo [BACKEND] Lancement des tests Python...
echo.
cd /d "%~dp0backend"
python -m pytest tests/ -v --tb=short ^
  --ignore=tests/test_etl_agents.py ^
  -p no:warnings ^
  2>&1
echo.
echo [BACKEND] Tests terminés.
goto end

:frontend
echo [FRONTEND] Lancement des tests JavaScript...
echo.
cd /d "%~dp0frontend"
call npx vitest run --reporter=verbose 2>&1
echo.
echo [FRONTEND] Tests terminés.
goto end

:all
echo === PHASE 1 : Tests Backend Python ===
echo.
cd /d "%~dp0backend"
python -m pytest tests/ -v --tb=short -p no:warnings 2>&1
set BACKEND_EXIT=%ERRORLEVEL%
echo.

echo === PHASE 2 : Tests Frontend JavaScript ===
echo.
cd /d "%~dp0frontend"
call npx vitest run --reporter=verbose 2>&1
set FRONTEND_EXIT=%ERRORLEVEL%
echo.

echo =====================================================
echo   Résumé
echo =====================================================
if %BACKEND_EXIT%==0 (
    echo   Backend  : SUCCES
) else (
    echo   Backend  : ECHEC [code %BACKEND_EXIT%]
)
if %FRONTEND_EXIT%==0 (
    echo   Frontend : SUCCES
) else (
    echo   Frontend : ECHEC [code %FRONTEND_EXIT%]
)
echo =====================================================

:end
endlocal
