#!/usr/bin/env python3
"""
Real-time radar distance monitoring from multiple SSH hosts.
Connects to two hosts via SSH, runs distance measurement commands,
and displays the results in a real-time graph.
"""

import asyncio
import asyncssh
import matplotlib
matplotlib.use('TkAgg')  # Use TkAgg backend for GUI display
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
        self.log_queue = queue.Queue()
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
                known_hosts=None,  # Accept any host key (use with caution)
                options=asyncssh.SSHClientConnectionOptions(
                    request_pty=True  # Request PTY at connection level
                )
            ) as conn:
                logger.info(f"Successfully connected to {self.host_id}")
                
                # Run the command with proper PTY settings for sudo
                async with conn.create_process(
                    self.command, 
                    request_pty=True,
                    encoding='utf-8',
                    term_type='xterm'
                ) as process:
                    self.running = True
                    
                    logger.info(f"Successfully started command on {self.host_id}")
                    
                    # Create tasks to read both stdout and stderr
                    async def read_stdout():
                        async for line in process.stdout:
                            if not self.running:
                                break
                                
                            line = line.strip()
                            if line:
                                # Forward raw stdout line to per-host log queue
                                try:
                                    self.log_queue.put((time.time(), 'STDOUT', line))
                                except Exception:
                                    pass
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
                    
                    async def read_stderr():
                        async for line in process.stderr:
                            if not self.running:
                                break
                            line = line.strip()
                            if line:
                                logger.error(f"{self.host_id} STDERR: {line}")
                                # Forward raw stderr line to per-host log queue
                                try:
                                    self.log_queue.put((time.time(), 'STDERR', line))
                                except Exception:
                                    pass
                    
                    # Run both readers concurrently
                    await asyncio.gather(read_stdout(), read_stderr(), return_exceptions=True)
                                
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
        self.time_window = 120  # Show last 2 minutes (120 seconds)
        
        # Data storage for each host
        self.data = {}
        for collector in collectors:
            self.data[collector.host_id] = {
                'times': deque(),  # No maxlen - we'll manage time-based cleanup
                'distances': deque(),
                'line': None,
                'connected': False,
                'last_data_time': None,
                'connection_timeout': 10.0  # Consider disconnected after 10 seconds without data
            }
        
        # Set up the plot with an additional text area for recent logs
        self.fig = plt.figure(figsize=(12, 7.5))
        # Main chart axes (top ~75%)
        self.ax = self.fig.add_axes([0.08, 0.28, 0.88, 0.65])
        # Log panel axes (bottom ~20%)
        self.log_ax = self.fig.add_axes([0.08, 0.06, 0.88, 0.18])
        self.log_ax.axis('off')
        self.log_text = self.log_ax.text(0.01, 0.98, "", va='top', ha='left', family='monospace', fontsize=9)
        self.max_log_lines = 8
        # Per-host rolling recent logs
        self.recent_logs = {collector.host_id: deque(maxlen=50) for collector in collectors}
        self.ax.set_xlabel('Time (seconds)')
        self.ax.set_ylabel('Distance (meters)')
        self.ax.set_title('Real-time Radar Distance Monitoring')
        self.ax.grid(True, alpha=0.3)
        
        # Create lines for each host
        colors = ['blue', 'red', 'green', 'orange', 'purple']
        for i, collector in enumerate(collectors):
            color = colors[i % len(colors)]
            line, = self.ax.plot([], [], color=color, label=f'{collector.tag} (Connecting...)', linewidth=2)
            self.data[collector.host_id]['line'] = line
        
        self.legend = self.ax.legend(loc='upper right')
        
        # Animation setup
        self.start_time = time.time()
        
    def update_plot(self, frame):
        """Update the plot with new data."""
        current_time = time.time()
        current_relative_time = current_time - self.start_time
        
        # Track if we need to update legend
        legend_needs_update = False
        
        # Collect new data from all hosts
        for collector in self.collectors:
            host_data = self.data[collector.host_id]
            was_connected = host_data['connected']
            
            # Process all available data points
            data_received = False
            while not collector.data_queue.empty():
                try:
                    timestamp, distance = collector.data_queue.get_nowait()
                    relative_time = timestamp - self.start_time
                    data_received = True
                    host_data['last_data_time'] = current_time
                    
                    if distance is not None:  # Valid distance measurement
                        host_data['times'].append(relative_time)
                        host_data['distances'].append(distance)
                    # Skip None values (no presence detected)
                        
                except queue.Empty:
                    break
            
            # Update connection status based on recent data and timeouts
            if data_received:
                if not host_data['connected']:
                    host_data['connected'] = True
                    legend_needs_update = True
            else:
                # Check for timeout - if no data received recently, mark as disconnected
                if host_data['last_data_time'] is not None:
                    time_since_last_data = current_time - host_data['last_data_time']
                    if time_since_last_data > host_data['connection_timeout']:
                        if host_data['connected']:
                            host_data['connected'] = False
                            legend_needs_update = True
            
            # Remove old data points (older than time_window)
            cutoff_time = current_relative_time - self.time_window
            while host_data['times'] and host_data['times'][0] < cutoff_time:
                host_data['times'].popleft()
                host_data['distances'].popleft()
            
            # Update the line plot
            if host_data['times'] and host_data['distances']:
                host_data['line'].set_data(list(host_data['times']), list(host_data['distances']))
        
        # Set up time window (always show last 2 minutes)
        time_start = current_relative_time - self.time_window
        time_end = current_relative_time
        self.ax.set_xlim(time_start, time_end)
        
        # Auto-scale Y-axis based on current data
        all_distances = []
        for host_data in self.data.values():
            if host_data['distances']:
                all_distances.extend(host_data['distances'])
        
        if all_distances:
            min_dist = min(all_distances)
            max_dist = max(all_distances)
            dist_range = max_dist - min_dist
            dist_margin = max(0.05, dist_range * 0.1)  # At least 5cm margin
            
            self.ax.set_ylim(min_dist - dist_margin, max_dist + dist_margin)
        else:
            # Default range if no data
            self.ax.set_ylim(0, 2)
        
        # Update legend if connection status changed
        if legend_needs_update:
            self.update_legend()
        
        # Update the log panel with the most recent lines from all hosts
        self.update_log_panel()
        
        return [host_data['line'] for host_data in self.data.values()]
    
    def update_legend(self):
        """Update the legend with current connection status."""
        labels = []
        for collector in self.collectors:
            host_data = self.data[collector.host_id]
            if host_data['connected']:
                status = "✓ Connected"
            elif host_data['last_data_time'] is not None:
                status = "✗ Disconnected"
            else:
                status = "⚡ Connecting..."
            labels.append(f"{collector.tag} ({status})")
        
        # Update legend with fixed position
        self.legend.remove()
        self.legend = self.ax.legend([host_data['line'] for host_data in self.data.values()], labels, loc='upper right')
    
    def start(self):
        """Start the real-time plotting."""
        ani = animation.FuncAnimation(
            self.fig, self.update_plot, interval=100, blit=False, cache_frame_data=False
        )
        plt.show()
        return ani

    def update_log_panel(self):
        """Collect recent raw log lines from collectors and render them in the log panel."""
        # Drain new log lines from collectors
        for collector in self.collectors:
            while not collector.log_queue.empty():
                try:
                    ts, stream, line = collector.log_queue.get_nowait()
                    # Keep a compact timestamp relative to start
                    self.recent_logs[collector.host_id].append((ts - self.start_time, collector.tag, stream, line))
                except queue.Empty:
                    break
        # Build combined view: interleave last few entries across hosts, show newest last
        combined = []
        for host_id, entries in self.recent_logs.items():
            combined.extend(entries)
        # Sort by timestamp and take the last N
        combined.sort(key=lambda x: x[0])
        tail = combined[-self.max_log_lines:]
        # Format lines
        rendered = []
        for rel_ts, tag, stream, line in tail:
            prefix = f"[{rel_ts:6.1f}s] {tag} {stream}: "
            rendered.append(prefix + line)
        self.log_text.set_text("\n".join(rendered))

async def run_ssh_collectors(collectors: List[RadarDataCollector]):
    """Run all SSH collectors concurrently."""
    logger.info(f"Starting SSH data collection for {len(collectors)} hosts...")
    for i, collector in enumerate(collectors):
        logger.info(f"Host {i+1}: {collector.tag} at {collector.host}")
    
    tasks = [asyncio.create_task(collector.collect_data()) for collector in collectors]
    try:
        await asyncio.gather(*tasks)
    except KeyboardInterrupt:
        logger.info("Stopping data collection...")
        for collector in collectors:
            collector.stop()

def load_config():
    """Load configuration from config.py file."""
    import os
    import sys
    import importlib.util
    
    try:
        # Try to import config.py using importlib
        config_path = os.path.join(os.getcwd(), 'config.py')
        if os.path.exists(config_path):
            spec = importlib.util.spec_from_file_location("config", config_path)
            config = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(config)
            return config
        else:
            raise ImportError("config.py file not found")
    except Exception as e:
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
    parser.add_argument('--test-mode', action='store_true',
                       help='Run in test mode (SSH connections only, no GUI)')
    
    args = parser.parse_args()
    
    # Check if config.py exists and use it by default, or if --config-file is specified
    config_exists = os.path.exists('config.py')
    # Use config file if explicitly requested, or if it exists and no CLI args provided
    cli_args_provided = any([args.host1, args.user1, args.pass1, args.cmd1, 
                           args.host2, args.user2, args.pass2, args.cmd2])
    use_config_file = args.config_file or (config_exists and not cli_args_provided)
    
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
    
    if args.test_mode:
        # Test mode: just run SSH connections without GUI
        logger.info("Running in test mode (SSH connections only)")
        try:
            asyncio.run(run_ssh_collectors(collectors))
        except KeyboardInterrupt:
            logger.info("Test mode interrupted by user")
        finally:
            for collector in collectors:
                collector.stop()
            logger.info("Test mode stopped")
    else:
        # Normal mode with GUI
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
            # Keep the animation alive
            plt.show()
        except KeyboardInterrupt:
            logger.info("Application interrupted by user")
        finally:
            # Stop collectors
            for collector in collectors:
                collector.stop()
            logger.info("Application stopped")

if __name__ == "__main__":
    main()
