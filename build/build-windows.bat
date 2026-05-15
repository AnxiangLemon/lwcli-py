@echo off
setlocal EnableExtensions

REM LWAPI console - Windows pack (double-click this file)
REM Do NOT double-click build-windows.ps1

cd /d "%~dp0.."
if errorlevel 1 (
    echo ERROR: cannot cd to project root.
    pause
    exit /b 1
)

echo ========================================
echo   LWAPI console - Windows build
echo   Project: %CD%
echo ========================================
echo.

where python >nul 2>&1
if errorlevel 1 (
    where py >nul 2>&1
    if errorlevel 1 (
        echo ERROR: python not found. Install Python 3.9+ and add to PATH.
        pause
        exit /b 1
    )
    set "PY=py -3"
) else (
    set "PY=python"
)

echo Using: %PY%
%PY% --version
if errorlevel 1 (
    echo ERROR: python cannot run.
    pause
    exit /b 1
)

%PY% -c "import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)"
if errorlevel 1 (
    echo ERROR: Python 3.9+ required.
    pause
    exit /b 1
)

if not exist "venv\Scripts\python.exe" (
    echo Creating venv ...
    %PY% -m venv venv
    if errorlevel 1 (
        echo ERROR: failed to create venv.
        pause
        exit /b 1
    )
)

call "venv\Scripts\activate.bat"
if errorlevel 1 (
    echo ERROR: failed to activate venv.
    pause
    exit /b 1
)

echo Installing dependencies ...
python -m pip install -U pip
if errorlevel 1 goto :failed
python -m pip install -r requirements.txt -r build\requirements-build.txt
if errorlevel 1 goto :failed

echo Running PyInstaller ...
python -m PyInstaller build\lwapi-console.spec --noconfirm --clean
if errorlevel 1 goto :failed

echo Packaging dist zip ...
python build\package_dist.py
if errorlevel 1 goto :failed

echo.
echo DONE. Output: dist\lwapi-console-*.zip
echo.
pause
exit /b 0

:failed
echo.
echo BUILD FAILED. See errors above.
echo.
pause
exit /b 1
