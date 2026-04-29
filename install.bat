@echo off
REM Installer for WoundCompute GUI on Windows.
REM Prerequisite: Miniconda (or Anaconda) installed.
REM Usage: double-click install.bat (or run from Anaconda Prompt).

setlocal

set "ENV_NAME=wound-compute-gui"
set "PY_VERSION=3.9.13"

where conda >nul 2>nul
if errorlevel 1 (
    echo ERROR: conda was not found on your PATH.
    echo.
    echo Please install Miniconda from:
    echo   https://docs.conda.io/en/latest/miniconda.html
    echo.
    echo After installing, run this script from "Anaconda Prompt"
    echo ^(found in your Start menu^), or re-open Command Prompt if you
    echo selected "Add Miniconda to PATH" during installation.
    pause
    exit /b 1
)

call conda env list | findstr /b /c:"%ENV_NAME% " >nul
if errorlevel 1 (
    echo Creating conda environment "%ENV_NAME%" ^(Python %PY_VERSION%^)...
    call conda create --name "%ENV_NAME%" python=%PY_VERSION% -y || goto :error
) else (
    echo Conda environment "%ENV_NAME%" already exists. Reusing it.
)

call conda activate "%ENV_NAME%" || goto :error

echo Upgrading pip, setuptools, wheel...
python -m pip install --upgrade pip setuptools wheel || goto :error

echo Installing WoundCompute GUI and dependencies...
cd /d "%~dp0"
python -m pip install -e . --force-reinstall --no-cache-dir || goto :error

echo.
echo Installation complete.
echo To launch the GUI, double-click run.bat
pause
exit /b 0

:error
echo.
echo Installation failed. See the messages above for details.
pause
exit /b 1
