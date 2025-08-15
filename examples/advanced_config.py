#!/usr/bin/env python3
"""
Advanced configuration example for radar distance monitoring.
This example shows advanced settings for production monitoring setup with multiple sensors.
"""

# Multiple hosts configuration using new HOSTS format
HOSTS = [
    {
        'host': '192.168.10.100',       # Production sensor IP
        'username': 'sensor_monitor',   # Dedicated monitoring user
        'password': 'SecurePassword123', # Strong password
        'command': '/opt/radar/bin/distance_sensor --json --continuous',
        'tag': 'Production Line A',     # Descriptive name
    },
    {
        'host': '192.168.10.101',       # Backup sensor IP
        'username': 'sensor_monitor',   # Same monitoring user
        'password': 'SecurePassword123', # Same strong password
        'command': '/opt/radar/bin/distance_sensor --json --continuous',
        'tag': 'Production Line B',     # Descriptive name
    },
    {
        'host': '192.168.10.102',       # Additional sensor
        'username': 'sensor_monitor',   # Same monitoring user
        'password': 'SecurePassword123', # Same strong password
        'command': '/opt/radar/bin/distance_sensor --json --continuous',
        'tag': 'Quality Control',       # Descriptive name
    },
    {
        'host': '192.168.10.103',       # Additional sensor
        'username': 'sensor_monitor',   # Same monitoring user
        'password': 'SecurePassword123', # Same strong password
        'command': '/opt/radar/bin/distance_sensor --json --continuous',
        'tag': 'Package Detection',     # Descriptive name
    },
]

# Advanced graph settings for production monitoring
GRAPH_CONFIG = {
    'max_points': 500,              # Keep more history for analysis
    'update_interval': 50,          # Fast updates for real-time monitoring
    'window_size': (16, 8),         # Large window for detailed view
}

# Production logging settings
LOG_LEVEL = 'INFO'  # Detailed logging for production monitoring
