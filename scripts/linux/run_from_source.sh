#!/bin/bash

# Change to repo root (two levels up from this script)
cd "$(dirname "$0")/../.."

echo "=== Radar Distance Monitor - Linux (Run from Source) ==="

# Ensure Python and create virtual environment
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    if command -v python3 &> /dev/null; then
        python3 -m venv .venv
    elif command -v python &> /dev/null; then
        python -m venv .venv
    else
        echo "Error: Python not found. Please install Python 3.7+ first."
        exit 1
    fi
fi

source .venv/bin/activate

echo "Installing/Updating dependencies..."
python -m pip install --upgrade pip > /dev/null
python -m pip install -r requirements.txt

# Prepare config for the user
if [ ! -f "config.py" ]; then
    cp config/config_example.py config.py
    echo "Created default config.py. Please enter your SSH details."
    
    # Try to open with various editors
    if command -v code &> /dev/null; then
        code config.py
    elif command -v gedit &> /dev/null; then
        gedit config.py &
    elif command -v nano &> /dev/null; then
        nano config.py
    elif command -v vim &> /dev/null; then
        vim config.py
    else
        echo "Please edit config.py with your preferred text editor, then run this script again."
        exit 0
    fi
    
    echo "After saving config.py, press Enter to continue..."
    read -r
fi

echo "Starting application..."
python src/radar_distance_monitor.py
