#!/usr/bin/env python3
"""
Single host configuration example for radar distance monitoring.
This example shows how to configure monitoring for just one radar sensor.
"""

# Single host configuration using new HOSTS format
HOSTS = [
    {
        'host': '192.168.1.100',        # Replace with your sensor host IP
        'username': 'pi',               # Replace with your username
        'password': 'raspberry',        # Replace with your password
        'command': 'sudo radar_sensor --mode presence',  # Replace with your radar command
        'tag': 'Main Sensor',           # Friendly name for the chart
    },
]

# Graph settings optimized for single sensor monitoring
GRAPH_CONFIG = {
    'max_points': 200,              # Show more history for single sensor
    'update_interval': 100,         # Update every 100ms
    'window_size': (10, 6),         # Suitable window size for single sensor
}

# Logging settings
LOG_LEVEL = 'INFO'  # Show informational messages
