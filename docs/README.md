# Radar Distance Monitor

A Python application that connects to two SSH hosts, runs distance measurement commands, and displays real-time distance data in a graph.

## Features

- Connect to two hosts simultaneously via SSH
- Parse distance sensor data (presence detection + distance)
- Real-time graphing with matplotlib
- Configurable via command line arguments or config file
- Handles connection errors and data parsing gracefully

## Installation

1. Install Python dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Configuration File (Recommended)

1. Copy the example config:
```bash
cp config_example.py config.py
```

2. Edit `config.py` with your SSH host details, commands, and display names:
   ```python
   HOST1_CONFIG = {
       'host': '192.168.1.100',
       'username': 'pi',
       'password': 'raspberry',
       'command': '/usr/local/bin/radar_sensor',
       'tag': 'Front Door',  # This name will appear on the chart
   }
   
   HOST2_CONFIG = {
       'host': '192.168.1.101',
       'username': 'pi', 
       'password': 'raspberry',
       'command': '/usr/local/bin/radar_sensor',
       'tag': 'Back Door',   # This name will appear on the chart
   }
   ```

3. Run the application:
```bash
python3 radar_distance_monitor.py
```

The application will automatically detect and use `config.py` if it exists.

### Command Line Arguments (Alternative)

If you prefer command line arguments or don't have a config file:

```bash
python3 radar_distance_monitor.py \
    --host1 192.168.1.100 --user1 pi --pass1 raspberry --cmd1 "/usr/local/bin/radar_sensor" --tag1 "Front Door" \
    --host2 192.168.1.101 --user2 pi --pass2 raspberry --cmd2 "/usr/local/bin/radar_sensor" --tag2 "Back Door" \
    --max-points 100
```

### Force Configuration File Usage

To explicitly use the configuration file (useful if you want to override command line args):

```bash
python3 radar_distance_monitor.py --config-file
```

## Data Format

The application expects data in the following format from the SSH commands:

```
1 0.652001
1 0.652001
0 0.000000
1 0.845123
```

- First number: presence flag (1 = detected, 0 = not detected)
- Second number: distance in meters (ignored if presence = 0)

## Graph Display

- Each host appears as a colored line with its configured tag name
- X-axis: Time in seconds since start
- Y-axis: Distance in meters
- Only shows data when presence is detected (flag = 1)
- Legend shows the tag names you configured (e.g., "Front Door", "Back Door")

## Security Notes

- This example uses password authentication for simplicity
- For production use, consider SSH key authentication
- The application accepts any SSH host key (known_hosts=None)

## Troubleshooting

- Check SSH connectivity manually first
- Ensure the radar sensor commands output the expected format
- Check firewall settings if connections fail
- Use `--help` to see all available options
