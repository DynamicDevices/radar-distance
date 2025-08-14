#!/usr/bin/env python3
"""
Real-time radar distance monitoring from multiple SSH hosts.
Connects to two hosts via SSH, runs distance measurement commands,
and displays the results in a real-time graph.
"""

import asyncio
import asyncssh
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from collections import deque
import time
import threading
import queue
import argparse
import sys
import os
from typing import Dict, List, Tuple, Optional
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class RadarDataCollector:
    """Handles SSH connection and data collection from a single host."""
    
    def __init__(self, host: str, username: str, password: str, command: str, host_id: str, tag: str = None):
        self.host = host
        self.username = username
        self.password = password
        self.command = command
        self.host_id = host_id
        self.tag = tag or host_id  # Use tag if provided, otherwise fall back to host_id
        self.data_queue = queue.Queue()
        self.running = False
        
    async def collect_data(self):
        """Connect to host via SSH and collect radar data."""
        try:
            logger.info(f"Connecting to {self.host_id} at {self.host}")
            
            # Connect to the SSH host
            async with asyncssh.connect(
                self.host,
                username=self.username,
                password=self.password,
                known_hosts=None  # Accept any host key (use with caution)
            ) as conn:
                logger.info(f"Successfully connected to {self.host_id}")
                
                # Run the command and stream output
                async with conn.create_process(self.command) as process:
                    self.running = True
                    
                    async for line in process.stdout:
                        if not self.running:
                            break
                            
                        line = line.strip()
                        if line:
                            try:
                                parts = line.split()
                                if len(parts) >= 2:
                                    presence = int(parts[0])
                                    distance = float(parts[1])
                                    timestamp = time.time()
                                    
                                    # Only queue valid distance measurements
                                    if presence == 1:
                                        self.data_queue.put((timestamp, distance))
                                        logger.debug(f"{self.host_id}: Distance = {distance}m")
                                    else:
                                        # Put None to indicate no presence detected
                                        self.data_queue.put((timestamp, None))
                                        
                            except (ValueError, IndexError) as e:
                                logger.warning(f"{self.host_id}: Error parsing line '{line}': {e}")
                                
        except Exception as e:
            logger.error(f"Error connecting to {self.host_id} ({self.host}): {e}")
            self.running = False
    
    def stop(self):
        """Stop data collection."""
        self.running = False

class RealTimeGrapher:
    """Handles real-time graphing of distance data from multiple hosts."""
    
    def __init__(self, collectors: List[RadarDataCollector], max_points: int = 100):
        self.collectors = collectors
        self.max_points = max_points
        
        # Data storage for each host
        self.data = {}
        for collector in collectors:
            self.data[collector.host_id] = {
                'times': deque(maxlen=max_points),
                'distances': deque(maxlen=max_points),
                'line': None
            }
        
        # Set up the plot
        self.fig, self.ax = plt.subplots(figsize=(12, 6))
        self.ax.set_xlabel('Time (seconds)')
        self.ax.set_ylabel('Distance (meters)')
        self.ax.set_title('Real-time Radar Distance Monitoring')
        self.ax.grid(True, alpha=0.3)
        
        # Create lines for each host
        colors = ['blue', 'red', 'green', 'orange', 'purple']
        for i, collector in enumerate(collectors):
            color = colors[i % len(colors)]
            line, = self.ax.plot([], [], color=color, label=f'{collector.tag}', linewidth=2)
            self.data[collector.host_id]['line'] = line
        
        self.ax.legend()
        
        # Animation setup
        self.start_time = time.time()
        
    def update_plot(self, frame):
        """Update the plot with new data."""
        current_time = time.time()
        
        # Collect new data from all hosts
        for collector in self.collectors:
            host_data = self.data[collector.host_id]
            
            # Process all available data points
            while not collector.data_queue.empty():
                try:
                    timestamp, distance = collector.data_queue.get_nowait()
                    relative_time = timestamp - self.start_time
                    
                    if distance is not None:  # Valid distance measurement
                        host_data['times'].append(relative_time)
                        host_data['distances'].append(distance)
                    # Skip None values (no presence detected)
                        
                except queue.Empty:
                    break
            
            # Update the line plot
            if host_data['times'] and host_data['distances']:
                host_data['line'].set_data(list(host_data['times']), list(host_data['distances']))
        
        # Auto-scale the plot
        if any(self.data[cid]['times'] for cid in self.data):
            all_times = []
            all_distances = []
            
            for host_data in self.data.values():
                if host_data['times'] and host_data['distances']:
                    all_times.extend(host_data['times'])
                    all_distances.extend(host_data['distances'])
            
            if all_times and all_distances:
                time_margin = max(5, (max(all_times) - min(all_times)) * 0.1)
                dist_margin = max(0.1, (max(all_distances) - min(all_distances)) * 0.1)
                
                self.ax.set_xlim(min(all_times) - time_margin, max(all_times) + time_margin)
                self.ax.set_ylim(min(all_distances) - dist_margin, max(all_distances) + dist_margin)
        
        return [host_data['line'] for host_data in self.data.values()]
    
    def start(self):
        """Start the real-time plotting."""
        ani = animation.FuncAnimation(
            self.fig, self.update_plot, interval=100, blit=False, cache_frame_data=False
        )
        plt.show()
        return ani

async def run_ssh_collectors(collectors: List[RadarDataCollector]):
    """Run all SSH collectors concurrently."""
    tasks = [asyncio.create_task(collector.collect_data()) for collector in collectors]
    try:
        await asyncio.gather(*tasks)
    except KeyboardInterrupt:
        logger.info("Stopping data collection...")
        for collector in collectors:
            collector.stop()

def load_config():
    """Load configuration from config.py file."""
    try:
        # Try to import config.py
        import config
        return config
    except ImportError:
        logger.error("config.py not found. Please copy config_example.py to config.py and modify it.")
        logger.error("You can also use command-line arguments instead.")
        return None

def main():
    """Main function to set up and run the radar distance monitor."""
    parser = argparse.ArgumentParser(description='Real-time radar distance monitoring')
    parser.add_argument('--config-file', action='store_true', 
                       help='Use config.py file instead of command line arguments')
    parser.add_argument('--host1', help='First SSH host')
    parser.add_argument('--user1', help='Username for first host')
    parser.add_argument('--pass1', help='Password for first host')
    parser.add_argument('--cmd1', help='Command to run on first host')
    parser.add_argument('--tag1', help='Display name for first host on chart')
    
    parser.add_argument('--host2', help='Second SSH host')
    parser.add_argument('--user2', help='Username for second host')
    parser.add_argument('--pass2', help='Password for second host')
    parser.add_argument('--cmd2', help='Command to run on second host')
    parser.add_argument('--tag2', help='Display name for second host on chart')
    
    parser.add_argument('--max-points', type=int, default=100, 
                       help='Maximum number of data points to display')
    
    args = parser.parse_args()
    
    # Check if config.py exists and use it by default, or if --config-file is specified
    config_exists = os.path.exists('config.py')
    use_config_file = config_exists or args.config_file
    
    if use_config_file:
        logger.info("Loading configuration from config.py")
        config = load_config()
        if config is None:
            sys.exit(1)
        
        # Set up logging level from config
        if hasattr(config, 'LOG_LEVEL'):
            numeric_level = getattr(logging, config.LOG_LEVEL.upper(), None)
            if isinstance(numeric_level, int):
                logging.getLogger().setLevel(numeric_level)
        
        # Create data collectors from config
        collectors = [
            RadarDataCollector(
                config.HOST1_CONFIG['host'],
                config.HOST1_CONFIG['username'],
                config.HOST1_CONFIG['password'],
                config.HOST1_CONFIG['command'],
                "Host-1",
                config.HOST1_CONFIG.get('tag', 'Host-1')
            ),
            RadarDataCollector(
                config.HOST2_CONFIG['host'],
                config.HOST2_CONFIG['username'],
                config.HOST2_CONFIG['password'],
                config.HOST2_CONFIG['command'],
                "Host-2",
                config.HOST2_CONFIG.get('tag', 'Host-2')
            )
        ]
        
        # Get max points from config
        max_points = getattr(config, 'GRAPH_CONFIG', {}).get('max_points', 100)
        
    else:
        # Use command line arguments
        if not all([args.host1, args.user1, args.pass1, args.cmd1, 
                   args.host2, args.user2, args.pass2, args.cmd2]):
            logger.error("Missing required command line arguments. Use --help for usage or create config.py")
            sys.exit(1)
        
        logger.info("Using command line arguments")
        collectors = [
            RadarDataCollector(args.host1, args.user1, args.pass1, args.cmd1, "Host-1", args.tag1),
            RadarDataCollector(args.host2, args.user2, args.pass2, args.cmd2, "Host-2", args.tag2)
        ]
        max_points = args.max_points
    
    # Create the grapher
    grapher = RealTimeGrapher(collectors, max_points)
    
    # Start SSH data collection in a separate thread
    def run_async_collectors():
        try:
            asyncio.run(run_ssh_collectors(collectors))
        except KeyboardInterrupt:
            pass
    
    ssh_thread = threading.Thread(target=run_async_collectors, daemon=True)
    ssh_thread.start()
    
    # Start real-time plotting (this will block until window is closed)
    try:
        logger.info("Starting real-time graph...")
        ani = grapher.start()
    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
    finally:
        # Stop collectors
        for collector in collectors:
            collector.stop()
        logger.info("Application stopped")

if __name__ == "__main__":
    main()
