# Radar Distance Monitor

A Python application that connects to two SSH hosts, runs distance measurement commands, and displays real-time distance data in a graph.

## Quick Start

### Windows (recommended for testers)

Option A: Prebuilt download
- Download `radar-distance-windows.zip` from GitHub (Actions Artifacts or Releases)
- Unzip anywhere, open the folder, and double‑click `start.bat`
- On first run it will create `config.py`. Enter your SSH details, save, then run again

Option B: Run from source
- Double‑click `scripts/windows/run_from_source.bat`
- It creates a local `.venv`, installs dependencies, prepares `config.py`, and launches the app

### Linux (recommended for testers)

Option A: Run from source (one-click)
- Run `./scripts/linux/run_from_source.sh`
- It creates a local `.venv`, installs dependencies, prepares `config.py`, and launches the app

Option B: Manual setup
- Run `./scripts/linux/start.sh` (for packaged executable bundles)

### Linux/macOS (developers)

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Configure your hosts:
   ```bash
   cp config/config_example.py config.py
   # Edit config.py with your SSH details
   ```

3. Run the monitor:
   ```bash
   python3 src/radar_distance_monitor.py
   ```

## Documentation

See the [full documentation](docs/README.md) for detailed installation, configuration, and usage instructions.

## Project Structure

```
radar-distance/
├── src/                     # Source code
│   ├── __init__.py
│   └── radar_distance_monitor.py
├── config/                  # Configuration files
│   └── config_example.py
├── docs/                    # Documentation
│   └── README.md
├── examples/                # Example configurations
├── requirements.txt         # Python dependencies
├── setup.py                # Package setup
├── CHANGELOG.md            # Version history
└── README.md               # This file
```

## License

MIT License - see the full documentation for details.