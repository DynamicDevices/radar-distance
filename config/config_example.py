#!/usr/bin/env python3
"""
Example configuration file for radar distance monitoring.
Copy this file to config.py and modify the values for your setup.

Two configuration formats are supported:

1. New HOSTS format (recommended) - supports any number of hosts:
   Use the HOSTS list below for flexible configuration.

2. Legacy format (backward compatible) - supports exactly 1 or 2 hosts:
   Use HOST1_CONFIG and HOST2_CONFIG (commented out below).

Choose ONE format - do not use both at the same time.
"""

# ============================================================================
# NEW FORMAT (Recommended): HOSTS list - supports 1 to many hosts
# ============================================================================

HOSTS = [
    {
        'host': '192.168.0.58',  # IP address or hostname
        'username': 'fio',       # SSH username
        'password': 'fio',       # SSH password (consider using SSH keys instead)
        'command': 'sudo RADAR_DEBUG=1 seamless_dev_spi spi.mode="presence"',  # Command to run on the host
        'tag': 'Sentai',         # Display name for this host on the chart
    },
    {
        'host': '192.168.0.96',  # IP address or hostname
        'username': 'rpi',       # SSH username
        'password': 'infineon',  # SSH password (consider using SSH keys instead)
        'command': 'sudo RADAR_DEBUG=1 RADAR_SPI_SPEED=12000000 ./seamless_dev_spi spi.mode="presence"',  # Command to run on the host
        'tag': 'Raspberry Pi',   # Display name for this host on the chart
    },
    # Add more hosts as needed:
    # {
    #     'host': '192.168.0.100',
    #     'username': 'sensor',
    #     'password': 'password123',
    #     'command': 'sensor_command',
    #     'tag': 'Sensor 3',
    # },
]

# ============================================================================
# LEGACY FORMAT (Backward Compatible): Individual host configs
# ============================================================================
# Comment out the HOSTS list above and uncomment the configs below to use legacy format

# # SSH connection settings for Host 1
# HOST1_CONFIG = {
#     'host': '192.168.0.58',  # IP address or hostname
#     'username': 'fio',         # SSH username
#     'password': 'fio',  # SSH password (consider using SSH keys instead)
#     'command': 'sudo RADAR_DEBUG=1 seamless_dev_spi spi.mode="presence"',  # Command to run on the host
#     'tag': 'Sentai',      # Display name for this host on the chart
# }

# # SSH connection settings for Host 2 (optional - can be omitted for single host)
# HOST2_CONFIG = {
#     'host': '192.168.0.96',  # IP address or hostname
#     'username': 'rpi',         # SSH username
#     'password': 'infineon',  # SSH password (consider using SSH keys instead)
#     'command': 'sudo RADAR_DEBUG=1 RADAR_SPI_SPEED=12000000 ./seamless_dev_spi spi.mode="presence"',  # Command to run on the host
#     'tag': 'Raspberry Pi',       # Display name for this host on the chart
# }

# Graph settings
GRAPH_CONFIG = {
    'max_points': 100,        # Maximum number of data points to display
    'update_interval': 100,   # Graph update interval in milliseconds
    'window_size': (12, 6),   # Graph window size (width, height)
}

# Logging settings
LOG_LEVEL = 'INFO'  # DEBUG, INFO, WARNING, ERROR
