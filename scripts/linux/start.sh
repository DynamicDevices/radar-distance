#!/bin/bash

# Start script for packaged executable bundle
cd "$(dirname "$0")"

if [ ! -f "config.py" ]; then
    if [ -f "config_example.py" ]; then
        cp config_example.py config.py
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
    else
        echo "Missing config.py and config_example.py. Please provide a config.py next to this script."
        exit 1
    fi
fi

echo "Starting Radar Distance Monitor..."
./RadarDistanceMonitor

echo
echo "Application exited. Press Enter to close."
read -r
