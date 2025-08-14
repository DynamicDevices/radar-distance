@echo off
setlocal enableextensions enabledelayedexpansion

REM Change to repo root (two levels up from this script)
cd /d "%~dp0\..\.."

echo === Radar Distance Monitor - Windows (Run from Source) ===

REM Ensure Python and create virtual environment
if not exist .venv (
    echo Creating virtual environment...
    where py >nul 2>nul
    if %ERRORLEVEL%==0 (
        py -3 -m venv .venv
    ) else (
        python -m venv .venv
    )
)

call .venv\Scripts\activate

echo Installing/Updating dependencies...
python -m pip install --upgrade pip >nul
python -m pip install -r requirements.txt

REM Prepare config for the user
if not exist config.py (
    copy /y config\config_example.py config.py >nul
    echo Created default config.py. Please enter your SSH details.
    start notepad config.py
    echo After saving config.py, return to this window.
    pause
)

echo Starting application...
python src\radar_distance_monitor.py

echo.
echo Application exited. Press any key to close.
pause >nul


