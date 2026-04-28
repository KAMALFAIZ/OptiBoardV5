@echo off
REM ======================================================================
REM  OptiBoard - Rebuild complet (Cython + React + Installeur)
REM
REM  Pipeline en 3 etapes :
REM    [1/3] Backend Cython  -> reporting-commercial\backend\dist_client\
REM    [2/3] Frontend Vite   -> reporting-commercial\frontend\dist\
REM    [3/3] Installeur Inno -> installer\output\OptiBoard-Setup-1.0.0.exe
REM
REM  Lancer depuis la racine du repo (D:\kasoft-platform\OptiBoard\...)
REM ======================================================================

setlocal EnableExtensions EnableDelayedExpansion
set "ROOT=%~dp0"
set "BACKEND=%ROOT%reporting-commercial\backend"
set "FRONTEND=%ROOT%reporting-commercial\frontend"
set "INSTALLER=%ROOT%installer"

set "T_START=%TIME%"

echo.
echo ======================================================================
echo   OptiBoard - REBUILD COMPLET
echo ======================================================================
echo   Racine    : %ROOT%
echo   Demarrage : %T_START%
echo ======================================================================
echo.

REM ---------- 1/3 Backend Cython ----------------------------------------
echo [1/3] Compilation backend (Cython)...
echo       %BACKEND%
echo.
pushd "%BACKEND%"
if not exist "build_protected.bat" (
    echo ERREUR: build_protected.bat introuvable dans %BACKEND%
    popd & goto :error
)
call build_protected.bat
if errorlevel 1 (
    echo.
    echo ERREUR: Compilation Cython echouee
    popd & goto :error
)
if not exist "dist_client" (
    echo ERREUR: dist_client\ non genere
    popd & goto :error
)
popd
echo.
echo [1/3] OK - Backend compile dans dist_client\
echo.

REM ---------- 2/3 Frontend React/Vite -----------------------------------
echo [2/3] Build frontend (Vite)...
echo       %FRONTEND%
echo.
pushd "%FRONTEND%"
if not exist "package.json" (
    echo ERREUR: package.json introuvable dans %FRONTEND%
    popd & goto :error
)
if not exist "node_modules" (
    echo       node_modules absent, npm install en cours...
    call npm install --no-audit --no-fund
    if errorlevel 1 (
        echo ERREUR: npm install echoue
        popd & goto :error
    )
)
call npm run build
if errorlevel 1 (
    echo ERREUR: npm run build echoue
    popd & goto :error
)
if not exist "dist" (
    echo ERREUR: dist\ non genere
    popd & goto :error
)
popd
echo.
echo [2/3] OK - Frontend buildle dans dist\
echo.

REM ---------- 3/3 Installeur Inno Setup ---------------------------------
echo [3/3] Build installeur (Inno Setup)...
echo       %INSTALLER%
echo.
pushd "%INSTALLER%"
if not exist "build_installer.bat" (
    echo ERREUR: build_installer.bat introuvable dans %INSTALLER%
    popd & goto :error
)
call build_installer.bat
if errorlevel 1 (
    echo.
    echo ERREUR: Build installeur echoue
    popd & goto :error
)
popd
echo.

REM ---------- Recap final -----------------------------------------------
set "EXE=%INSTALLER%\output\OptiBoard-Setup-1.0.0.exe"
set "T_END=%TIME%"

echo.
echo ======================================================================
echo   REBUILD TERMINE AVEC SUCCES
echo ======================================================================
if exist "%EXE%" (
    for %%I in ("%EXE%") do set "SIZE_BYTES=%%~zI"
    set /a SIZE_MB=!SIZE_BYTES! / 1048576
    echo   Installeur : %EXE%
    echo   Taille     : !SIZE_MB! MB
) else (
    echo   ATTENTION: Installeur introuvable a l'emplacement attendu :
    echo     %EXE%
)
echo   Demarrage  : %T_START%
echo   Fin        : %T_END%
echo ======================================================================
echo.
echo Pour tester l'installeur, executez :
echo    %EXE%
echo.
endlocal
exit /b 0

:error
echo.
echo ======================================================================
echo   REBUILD ECHEC
echo ======================================================================
endlocal
exit /b 1
