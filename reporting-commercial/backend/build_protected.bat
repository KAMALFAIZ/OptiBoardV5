@echo off
REM ======================================================================
REM OptiBoard - Build protege (Cython + MSVC)
REM
REM Ce script:
REM   1. Charge l'environnement MSVC via vcvarsall.bat
REM   2. Active DISTUTILS_USE_SDK=1 (bypass detection setuptools)
REM   3. Lance build_protected.py qui compile app/ en .pyd dans dist_client/
REM
REM Les fichiers sources originaux ne sont JAMAIS modifies.
REM ======================================================================

setlocal

echo.
echo ======================================================================
echo   OptiBoard - Protection du code Python (Cython)
echo ======================================================================
echo.

REM --- 1. Localiser vcvarsall.bat -----------------------------------------
set "VCVARS=C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvarsall.bat"
if not exist "%VCVARS%" (
    set "VCVARS=C:\Program Files\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvarsall.bat"
)
if not exist "%VCVARS%" (
    set "VCVARS=C:\Program Files\Microsoft Visual Studio\2022\Enterprise\VC\Auxiliary\Build\vcvarsall.bat"
)
if not exist "%VCVARS%" (
    set "VCVARS=C:\Program Files\Microsoft Visual Studio\2022\Professional\VC\Auxiliary\Build\vcvarsall.bat"
)
if not exist "%VCVARS%" (
    set "VCVARS=C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvarsall.bat"
)

if not exist "%VCVARS%" (
    echo [ERREUR] vcvarsall.bat introuvable.
    echo Installez Microsoft C++ Build Tools:
    echo   https://visualstudio.microsoft.com/visual-cpp-build-tools/
    exit /b 1
)

echo [1/3] Chargement de l'environnement MSVC...
echo       %VCVARS%
call "%VCVARS%" x64 >nul
if errorlevel 1 (
    echo [ERREUR] Echec du chargement de vcvarsall.bat
    exit /b 1
)

REM --- 2. Flags pour setuptools -------------------------------------------
set DISTUTILS_USE_SDK=1
set MSSdk=1

echo [2/3] Environnement MSVC charge (x64).
echo.

REM --- 3. Lancer le build Python ------------------------------------------
echo [3/3] Lancement du build Cython...
echo.

cd /d "%~dp0"
python build_protected.py %*
set BUILD_RC=%ERRORLEVEL%

echo.
if %BUILD_RC% EQU 0 (
    echo ======================================================================
    echo   BUILD OK - Distribution protegee prete dans dist_client\
    echo ======================================================================
) else (
    echo ======================================================================
    echo   BUILD TERMINE AVEC %BUILD_RC% code de sortie
    echo   Verifiez le rapport ci-dessus pour les eventuels echecs.
    echo ======================================================================
)

endlocal & exit /b %BUILD_RC%
