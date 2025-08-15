#!/usr/bin/env python3
"""
Simple configuration example for radar distance monitoring.
This example shows a basic setup for monitoring a single radar sensor.
"""

# Single host configuration using new HOSTS format
HOSTS = [
    {
        'host': 'sensor1.local',        # Replace with your sensor host
        'username': 'admin',            # Replace with your username
        'password': 'your_password',    # Replace with your password
        'command': 'radar_distance',    # Replace with your radar command
        'tag': 'Front Entrance',        # Friendly name for the chart
    },
]

# For multiple hosts, just add more entries:
# HOSTS = [
#     {
#         'host': 'sensor1.local',
#         'username': 'admin',
#         'password': 'your_password',
#         'command': 'radar_distance',
#         'tag': 'Front Entrance',
#     },
#     {
#         'host': 'sensor2.local',
#         'username': 'admin',
#         'password': 'your_password',
#         'command': 'radar_distance',
#         'tag': 'Back Entrance',
#     },
# ]

# Graph settings
GRAPH_CONFIG = {
    'max_points': 50,               # Show last 50 data points
    'update_interval': 200,         # Update every 200ms
    'window_size': (10, 5),         # Smaller window size
}

# Logging settings
LOG_LEVEL = 'WARNING'  # Only show warnings and errors
