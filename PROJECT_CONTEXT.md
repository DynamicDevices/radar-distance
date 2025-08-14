# Radar Distance Monitor - Project Context

## Project Overview
A Python application that connects to two SSH hosts running radar sensors, collects real-time distance measurement data, and displays it in a live graph using matplotlib.

## Current Status
- **Dependencies**: Installed and verified (asyncssh, matplotlib, numpy)
- **Configuration**: Set up with two radar hosts (Sentai and Raspberry Pi)
- **Last Modified**: Modified config files with updated command paths

## Project Structure
```
radar-distance/
├── src/
│   ├── __init__.py
│   └── radar_distance_monitor.py       # Main application
├── config/
│   └── config_example.py               # Example configuration
├── docs/
│   └── README.md                       # Detailed documentation
├── examples/                           # Example configurations
├── config.py                          # Active configuration (not in git)
├── requirements.txt                    # Python dependencies
├── setup.py                           # Package setup
├── CHANGELOG.md                        # Version history
└── README.md                          # Quick start guide
```

## Configuration Details

### Current Host Setup
**Host 1 - Sentai (192.168.0.58)**
- Username: `fio`
- Password: `fio`
- Command: `sudo RADAR_DEBUG=1 seamless_dev_spi spi.mode="presence"`
- Display Tag: `Sentai`

**Host 2 - Raspberry Pi (192.168.0.96)**
- Username: `rpi`
- Password: `infineon`
- Command: `sudo RADAR_DEBUG=1 RADAR_SPI_SPEED=12000000 /home/rpi/Desktop/spi-lib/build/seamless_dev_spi spi.mode="presence"`
- Display Tag: `Raspberry Pi`

### Data Format Expected
```
1 0.652001    # presence=1, distance=0.652001m
1 0.652001    # presence=1, distance=0.652001m
0 0.000000    # presence=0, no detection
1 0.845123    # presence=1, distance=0.845123m
```

## Key Features
- **Dual SSH Connections**: Connects to two hosts simultaneously
- **Real-time Graphing**: Live matplotlib visualization with 2-minute time window
- **Presence Detection**: Only graphs data when presence flag = 1
- **Error Handling**: Graceful connection error handling and data parsing
- **Flexible Configuration**: Config file or command-line arguments
- **Test Mode**: SSH-only testing without GUI (`--test-mode`)

## Usage Commands

### Run with Config File (Recommended)
```bash
python3 src/radar_distance_monitor.py
```

### Test SSH Connections Only
```bash
python3 src/radar_distance_monitor.py --test-mode
```

### Command Line Arguments (Alternative)
```bash
python3 src/radar_distance_monitor.py \
    --host1 192.168.0.58 --user1 fio --pass1 fio \
    --cmd1 "sudo RADAR_DEBUG=1 seamless_dev_spi spi.mode=\"presence\"" \
    --tag1 "Sentai" \
    --host2 192.168.0.96 --user2 rpi --pass2 infineon \
    --cmd2 "sudo RADAR_DEBUG=1 RADAR_SPI_SPEED=12000000 /home/rpi/Desktop/spi-lib/build/seamless_dev_spi spi.mode=\"presence\"" \
    --tag2 "Raspberry Pi"
```

## Dependencies
- `asyncssh>=2.13.0` - SSH connections
- `matplotlib>=3.7.0` - Real-time graphing
- `numpy>=1.24.0` - Data processing

## Security Notes
- Uses password authentication (consider SSH keys for production)
- Accepts any SSH host key (`known_hosts=None`)
- Stores passwords in plain text config (consider environment variables)

## Development Notes
- Uses TkAgg backend for matplotlib GUI
- Async/await pattern for SSH connections
- Threading for concurrent SSH data collection and GUI
- Queue-based data passing between SSH threads and graph
- Time-based data cleanup (2-minute rolling window)

## Recent Changes
- Updated Raspberry Pi command path to full absolute path
- Configured for Sentai and RPi radar sensors
- Ready for testing with current network setup

## Next Steps
1. Test SSH connections to verify host accessibility
2. Run in test mode to validate data collection
3. Launch full GUI application for real-time monitoring
4. Consider implementing SSH key authentication
5. Add data logging/export functionality if needed

## Troubleshooting
- Verify SSH connectivity: `ssh fio@192.168.0.58` and `ssh rpi@192.168.0.96`
- Check radar sensor commands work manually on each host
- Ensure network connectivity to both hosts
- Check firewall settings if connections fail
- Use DEBUG log level for detailed troubleshooting
