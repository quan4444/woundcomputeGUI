@echo off
REM Launches the WoundCompute GUI on Windows.
REM Prerequisite: install.bat has been run successfully.
REM Usage: double-click run.bat (or run from Anaconda Prompt).

setlocal

set "ENV_NAME=wound-compute-gui"

where conda >nul 2>nul
if errorlevel 1 (
    echo ERROR: conda was not found on your PATH.
    echo Please install Miniconda and run install.bat first.
    pause
    exit /b 1
)

call conda env list | findstr /b /c:"%ENV_NAME% " >nul
if errorlevel 1 (
    echo ERROR: conda environment "%ENV_NAME%" does not exist.
    echo Please run install.bat first.
    pause
    exit /b 1
)

call conda activate "%ENV_NAME%" || (
    echo ERROR: failed to activate environment "%ENV_NAME%".
    pause
    exit /b 1
)

cd /d "%~dp0"
python run_wound_compute_gui.py
