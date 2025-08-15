@echo off
setlocal enableextensions enabledelayedexpansion

REM Start script for packaged .exe bundle
cd /d "%~dp0"

if not exist config.py (
    if exist config_example.py (
        copy /y config_example.py config.py >nul
        echo Created default config.py. Please enter your SSH details.
        start notepad config.py
        echo After saving config.py, return to this window.
        pause
    ) else (
        echo Missing config.py and config_example.py. Please provide a config.py next to this script.
        pause
        exit /b 1
    )
)

echo Starting Radar Distance Monitor...
RadarDistanceMonitor.exe


