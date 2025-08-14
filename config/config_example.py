#!/usr/bin/env python3
"""
Example configuration file for radar distance monitoring.
Copy this file to config.py and modify the values for your setup.
"""

# SSH connection settings for Host 1
HOST1_CONFIG = {
    'host': '192.168.1.100',  # IP address or hostname
    'username': 'pi',         # SSH username
    'password': 'raspberry',  # SSH password (consider using SSH keys instead)
    'command': '/usr/local/bin/radar_sensor',  # Command to run on the host
    'tag': 'Front Door',      # Display name for this host on the chart
}

# SSH connection settings for Host 2
HOST2_CONFIG = {
    'host': '192.168.1.101',  # IP address or hostname
    'username': 'pi',         # SSH username
    'password': 'raspberry',  # SSH password (consider using SSH keys instead)
    'command': '/usr/local/bin/radar_sensor',  # Command to run on the host
    'tag': 'Back Door',       # Display name for this host on the chart
}

# Graph settings
GRAPH_CONFIG = {
    'max_points': 100,        # Maximum number of data points to display
    'update_interval': 100,   # Graph update interval in milliseconds
    'window_size': (12, 6),   # Graph window size (width, height)
}

# Logging settings
LOG_LEVEL = 'INFO'  # DEBUG, INFO, WARNING, ERROR
