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
import matplotlib.dates as mdates
from matplotlib.ticker import FuncFormatter
from collections import deque
import time
import threading
import queue
import argparse
import sys
import os
from typing import Dict, List, Tuple, Optional
import logging
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class RadarDataCollector:
    """Handles SSH connection and data collection from a single host."""
    
    def __init__(self, host: str, username: str, password: str, command: str, host_id: str, tag: str = None, enable_file_logging: bool = False):
        self.host = host
        self.username = username
        self.password = password
        self.command = command
        self.host_id = host_id
        self.tag = tag or host_id  # Use tag if provided, otherwise fall back to host_id
        self.data_queue = queue.Queue()
        self.log_queue = queue.Queue()
        self.status_queue = queue.Queue()  # For tracking presence/distance status
        self.running = False
        self.chip_id = None  # Store detected chip ID
        self.chip_model = None  # Store detected chip model
        self.enable_file_logging = enable_file_logging
        self.log_file = None  # File handle for logging
        self.log_filename = None  # Store the log filename
        
    def create_log_file(self):
        """Create a log file for this host based on IP address and chip ID."""
        if not self.enable_file_logging:
            return
            
        # Clean IP address for filename (replace dots with underscores)
        clean_ip = self.host.replace('.', '_')
        
        # Use chip model and ID if available, otherwise use host info
        if self.chip_model and self.chip_id:
            # Clean chip model for filename (replace slashes and other invalid chars)
            clean_chip_model = self.chip_model.replace('/', '-').replace('\\', '-')
            chip_info = f"{clean_chip_model}_{self.chip_id[:8]}"  # Use first 8 chars of chip ID
        else:
            chip_info = "unknown_chip"
            
        # Create filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_filename = f"radar_data_{clean_ip}_{chip_info}_{timestamp}.csv"
        
        try:
            # Create logs directory if it doesn't exist
            import os
            os.makedirs("logs", exist_ok=True)
            
            # Open log file for writing
            self.log_file = open(f"logs/{self.log_filename}", 'w')
            # Write CSV header with both processed and raw values
            self.log_file.write("timestamp,relative_time,processed_presence,processed_distance,raw_presence,raw_distance,raw_line\n")
            self.log_file.flush()
            logger.info(f"{self.host_id}: Created log file: logs/{self.log_filename}")
        except Exception as e:
            logger.error(f"{self.host_id}: Failed to create log file: {e}")
            self.log_file = None
    
    def write_to_log(self, timestamp: float, presence: int, distance: float, raw_line: str, raw_presence: int = None, raw_distance: float = None):
        """Write data to log file if logging is enabled."""
        if self.log_file and self.enable_file_logging:
            try:
                # Convert timestamp to readable format
                dt = datetime.fromtimestamp(timestamp)
                timestamp_str = dt.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]  # millisecond precision
                relative_time = timestamp - getattr(self, 'start_time', timestamp)
                
                # Escape any commas in raw_line for CSV
                escaped_raw_line = raw_line.replace(',', ';').replace('\n', ' ').replace('\r', ' ')
                
                # Include raw and processed values for comparison
                raw_pres = raw_presence if raw_presence is not None else presence
                raw_dist = raw_distance if raw_distance is not None else distance
                
                # Write CSV row with both raw and processed values
                self.log_file.write(f"{timestamp_str},{relative_time:.3f},{presence},{distance},{raw_pres},{raw_dist},{escaped_raw_line}\n")
                self.log_file.flush()
            except Exception as e:
                logger.error(f"{self.host_id}: Error writing to log file: {e}")
        
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
                    self.start_time = time.time()  # Record start time for relative calculations
                    
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
                                
                                # Check for chip ID information
                                if 'chip id :' in line.lower():
                                    try:
                                        # Extract chip ID and model from line like: "get status chipid 0  chip id : 00000303 BGT60TR13C/BGT60TR13D"
                                        parts = line.split('chip id :')
                                        if len(parts) > 1:
                                            chip_info = parts[1].strip().split()
                                            if len(chip_info) >= 2:
                                                self.chip_id = chip_info[0]
                                                self.chip_model = chip_info[1]
                                                logger.info(f"{self.host_id}: Detected chip {self.chip_model} (ID: {self.chip_id})")
                                                # Create log file now that we have chip information
                                                self.create_log_file()
                                    except Exception as e:
                                        logger.debug(f"{self.host_id}: Error parsing chip ID from '{line}': {e}")
                                
                                try:
                                    parts = line.split()
                                    if len(parts) >= 2:
                                        raw_presence = int(parts[0])
                                        raw_distance = float(parts[1])
                                        timestamp = time.time()
                                        
                                        # If presence is 0, force distance to 0 regardless of what radar reports
                                        processed_presence = raw_presence
                                        processed_distance = raw_distance if raw_presence == 1 else 0.0
                                        
                                        # Write to log file with both raw and processed values
                                        self.write_to_log(timestamp, processed_presence, processed_distance, line, raw_presence, raw_distance)
                                        
                                        # Always update status for log display (with processed values)
                                        self.status_queue.put((timestamp, processed_presence, processed_distance))
                                        
                                        # Only queue data points when presence is detected (for plotting)
                                        if processed_presence == 1:
                                            self.data_queue.put((timestamp, processed_distance))
                                            logger.debug(f"{self.host_id}: Raw={raw_presence},{raw_distance:.3f} -> Processed={processed_presence},{processed_distance:.3f}")
                                        else:
                                            logger.debug(f"{self.host_id}: Raw={raw_presence},{raw_distance:.3f} -> Processed={processed_presence},{processed_distance:.3f} (no plot)")
                                        # Don't queue anything when presence = 0 (no plotting)
                                            
                                except (ValueError, IndexError):
                                    # Skip logging for known initialization/status messages
                                    known_init_messages = [
                                        'using alternate antenna', 'debugging on', 'spi speed',
                                        'using sensitivity setting', 'using range min', 'using range max',
                                        'spi max speed', 'get status chipid', 'slice size',
                                        'assuming', 'setup presence sensing', 'get defaults',
                                        'create done', 'chip id :'
                                    ]
                                    
                                    line_lower = line.lower()
                                    is_known_message = any(msg in line_lower for msg in known_init_messages)
                                    
                                    if not is_known_message:
                                        # Only log parsing errors for lines that might actually be data
                                        logger.debug(f"{self.host_id}: Could not parse data from line: '{line}'")
                    
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
        # Close log file if open
        if self.log_file:
            try:
                self.log_file.close()
                logger.info(f"{self.host_id}: Closed log file: {self.log_filename}")
            except Exception as e:
                logger.error(f"{self.host_id}: Error closing log file: {e}")
            self.log_file = None

class RealTimeGrapher:
    """Handles real-time graphing of distance data from multiple hosts."""
    
    def __init__(self, collectors: List[RadarDataCollector], max_points: int = 100):
        self.collectors = collectors
        self.max_points = max_points
        self.time_window = 120  # Show last 2 minutes (120 seconds)
        self.scrollback_mode = False  # When True, shows all data with scrolling
        self.zoom_start = 0  # Start time for zoomed view
        self.zoom_duration = 120  # Duration of zoomed view in seconds
        
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
        # Main chart axes (upper area)
        self.ax = self.fig.add_axes([0.08, 0.36, 0.88, 0.60])
        # Log panel axes (lower area, larger height, placed lower to avoid overlap with legend)
        self.log_ax = self.fig.add_axes([0.08, 0.02, 0.88, 0.30])
        self.log_ax.axis('off')
        # Increase font size for distance viewing (half previous), and nudge one line down
        self.log_text = self.log_ax.text(0.01, 0.90, "", va='top', ha='left', family='monospace', fontsize=22)
        self.max_log_lines = 8  # retained but unused for now; kept for future toggles
        # Per-host latest log line (timestamp, tag, stream, line)
        self.latest_logs = {collector.host_id: None for collector in collectors}
        self.ax.set_xlabel('Time (HH:MM:SS)')
        self.ax.set_ylabel('Distance (meters)')
        self.ax.set_title('Real-time Radar Distance Monitoring (Press S for scrollback mode)')
        self.ax.grid(True, alpha=0.3)
        
        # Set up time formatting for X-axis
        def time_formatter(x, pos):
            # Convert relative seconds to HH:MM:SS format
            total_seconds = int(x)
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            seconds = total_seconds % 60
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        
        self.ax.xaxis.set_major_formatter(FuncFormatter(time_formatter))
        
        # Create lines for each host
        colors = ['blue', 'red', 'green', 'orange', 'purple']
        for i, collector in enumerate(collectors):
            color = colors[i % len(colors)]
            line, = self.ax.plot([], [], color=color, label=f'{collector.tag} (⚡ Connecting...)', linewidth=2)
            self.data[collector.host_id]['line'] = line
        
        self.legend = self.ax.legend(loc='upper right')
        
        # Animation setup
        self.start_time = time.time()
        
        # Connect keyboard events for scrollback control
        self.fig.canvas.mpl_connect('key_press_event', self.on_key_press)
        
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
            data_received = False  # Initialize for each collector
            
            # Process status updates for log display
            while not collector.status_queue.empty():
                try:
                    timestamp, presence, distance = collector.status_queue.get_nowait()
                    data_received = True
                    host_data['last_data_time'] = current_time
                    # Track last presence/distance for log display
                    host_data['last_presence'] = presence
                    host_data['last_distance'] = distance
                except queue.Empty:
                    break
            
            # Process plotting data points (only when presence=1)
            while not collector.data_queue.empty():
                try:
                    timestamp, distance = collector.data_queue.get_nowait()
                    relative_time = timestamp - self.start_time
                    # Add to plot data
                    host_data['times'].append(relative_time)
                    host_data['distances'].append(distance)
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
            
            # Remove old data points (older than time_window) only if not in scrollback mode
            if not self.scrollback_mode:
                cutoff_time = current_relative_time - self.time_window
                while host_data['times'] and host_data['times'][0] < cutoff_time:
                    host_data['times'].popleft()
                    host_data['distances'].popleft()
            
            # Update the line plot
            if host_data['times'] and host_data['distances']:
                host_data['line'].set_data(list(host_data['times']), list(host_data['distances']))
        
        # Set up time window
        if self.scrollback_mode:
            # In scrollback mode, show a window starting from zoom_start
            time_start = self.zoom_start
            time_end = self.zoom_start + self.zoom_duration
            # Ensure we don't go beyond available data
            max_time = current_relative_time
            if time_end > max_time:
                time_end = max_time
                time_start = max(0, time_end - self.zoom_duration)
        else:
            # Normal mode: show last 2 minutes
            time_start = current_relative_time - self.time_window
            time_end = current_relative_time
        
        self.ax.set_xlim(time_start, time_end)
        
        # Auto-scale Y-axis based on current data in view
        all_distances = []
        for host_data in self.data.values():
            if host_data['distances'] and host_data['times']:
                # In scrollback mode, only consider distances within the current time window
                if self.scrollback_mode:
                    visible_distances = []
                    for t, d in zip(host_data['times'], host_data['distances']):
                        if time_start <= t <= time_end:
                            visible_distances.append(d)
                    all_distances.extend(visible_distances)
                else:
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
        
        # Update the log panel with the most recent line from each host
        self.update_log_panel()
        
        return [host_data['line'] for host_data in self.data.values()]
    
    def update_legend(self):
        """Update the legend with current connection status and chip information."""
        labels = []
        for collector in self.collectors:
            host_data = self.data[collector.host_id]
            if host_data['connected']:
                status = "✓ Connected"
            elif host_data['last_data_time'] is not None:
                status = "✗ Disconnected"
            else:
                status = "⚡ Connecting..."
            
            # Add chip information if available
            chip_info = ""
            if collector.chip_model and collector.chip_id:
                chip_info = f" [{collector.chip_model}:{collector.chip_id[:6]}]"
            elif collector.chip_model:
                chip_info = f" [{collector.chip_model}]"
            
            labels.append(f"{collector.tag}{chip_info} ({status})")
        
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
        """Collect latest raw log line per host and render them in the log panel as fixed rows."""
        # Drain new log lines from collectors and retain only the most recent per host
        for collector in self.collectors:
            while not collector.log_queue.empty():
                try:
                    ts, stream, line = collector.log_queue.get_nowait()
                    self.latest_logs[collector.host_id] = (ts - self.start_time, collector.tag, stream, line)
                except queue.Empty:
                    break
        # Render one line per host, in collector order, aligned columns
        rendered = []
        for collector in self.collectors:
            latest = self.latest_logs.get(collector.host_id)
            # Pull last parsed presence/distance if available
            host_data = self.data.get(collector.host_id, {})
            last_presence = host_data.get('last_presence')
            last_distance = host_data.get('last_distance')
            pres_str = '-' if last_presence is None else f"{last_presence:d}"
            dist_str = '---' if last_distance is None else f"{last_distance:0.3f}m"
            if latest is None:
                rel_ts = 0.0
            else:
                rel_ts, tag, stream, raw = latest
            # Render without stream/raw content
            rendered.append(
                f"[{rel_ts:6.1f}s]  {collector.tag:<14}  pres:{pres_str:>1}  dist:{dist_str:>9}"
            )
        self.log_text.set_text("\n".join(rendered))
    
    def on_key_press(self, event):
        """Handle keyboard events for scrollback and zoom control."""
        if event.key == 's':
            # Toggle scrollback mode
            self.scrollback_mode = not self.scrollback_mode
            if self.scrollback_mode:
                current_time = time.time() - self.start_time
                self.zoom_start = max(0, current_time - self.zoom_duration)
                self.ax.set_title('Real-time Radar Distance Monitoring (SCROLLBACK MODE - Press S to toggle, ← → to scroll, + - to zoom)')
                logger.info("Scrollback mode ENABLED - Use arrow keys to scroll, +/- to zoom, S to toggle")
            else:
                self.ax.set_title('Real-time Radar Distance Monitoring')
                logger.info("Scrollback mode DISABLED - Back to real-time view")
        
        elif self.scrollback_mode and event.key == 'left':
            # Scroll backward
            scroll_amount = self.zoom_duration * 0.1  # 10% of current view
            self.zoom_start = max(0, self.zoom_start - scroll_amount)
        
        elif self.scrollback_mode and event.key == 'right':
            # Scroll forward
            scroll_amount = self.zoom_duration * 0.1  # 10% of current view
            current_time = time.time() - self.start_time
            max_start = max(0, current_time - self.zoom_duration)
            self.zoom_start = min(max_start, self.zoom_start + scroll_amount)
        
        elif self.scrollback_mode and (event.key == '+' or event.key == '='):
            # Zoom in (reduce duration)
            old_center = self.zoom_start + self.zoom_duration / 2
            self.zoom_duration = max(10, self.zoom_duration * 0.8)  # Min 10 seconds
            self.zoom_start = max(0, old_center - self.zoom_duration / 2)
        
        elif self.scrollback_mode and event.key == '-':
            # Zoom out (increase duration)
            old_center = self.zoom_start + self.zoom_duration / 2
            self.zoom_duration = min(3600, self.zoom_duration * 1.25)  # Max 1 hour
            self.zoom_start = max(0, old_center - self.zoom_duration / 2)
        
        elif self.scrollback_mode and event.key == 'home':
            # Go to beginning
            self.zoom_start = 0
        
        elif self.scrollback_mode and event.key == 'end':
            # Go to end (current time)
            current_time = time.time() - self.start_time
            self.zoom_start = max(0, current_time - self.zoom_duration)

async def run_ssh_collectors(collectors: List[RadarDataCollector], test_duration: int = None):
    """Run all SSH collectors concurrently."""
    logger.info(f"Starting SSH data collection for {len(collectors)} hosts...")
    for i, collector in enumerate(collectors):
        logger.info(f"Host {i+1}: {collector.tag} at {collector.host}")
    
    tasks = [asyncio.create_task(collector.collect_data()) for collector in collectors]
    try:
        if test_duration:
            # Wait for either all tasks to complete or test duration to expire
            await asyncio.wait_for(asyncio.gather(*tasks), timeout=test_duration)
        else:
            await asyncio.gather(*tasks)
    except asyncio.TimeoutError:
        logger.info(f"Test duration of {test_duration} seconds completed")
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
    
    # Multi-host arguments
    parser.add_argument('--host', action='append', help='SSH host (can be specified multiple times)')
    parser.add_argument('--user', action='append', help='Username (must match number of hosts)')
    parser.add_argument('--password', action='append', help='Password (must match number of hosts)')
    parser.add_argument('--command', action='append', help='Command to run (must match number of hosts)')
    parser.add_argument('--tag', action='append', help='Display name for host on chart (optional)')
    
    parser.add_argument('--max-points', type=int, default=100, 
                       help='Maximum number of data points to display')
    parser.add_argument('--enable-file-logging', action='store_true',
                       help='Enable logging radar data to individual CSV files per host')
    parser.add_argument('--test-mode', action='store_true',
                       help='Run in test mode (SSH connections only, no GUI)')
    parser.add_argument('--test-duration', type=int, default=60,
                       help='Duration in seconds for test mode (default: 60 seconds)')
    
    args = parser.parse_args()
    
    # Check if config.py exists and use it by default, or if --config-file is specified
    config_exists = os.path.exists('config.py')
    # Use config file if explicitly requested, or if it exists and no CLI args provided
    cli_args_provided = any([args.host, args.user, args.password, args.command])
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
        collectors = []
        
        # Check for HOSTS configuration
        if hasattr(config, 'HOSTS') and config.HOSTS:
            # Get file logging setting from config
            enable_file_logging = getattr(config, 'ENABLE_FILE_LOGGING', False)
            
            for i, host_config in enumerate(config.HOSTS):
                host_id = f"Host-{i+1}"
                collectors.append(RadarDataCollector(
                    host_config['host'],
                    host_config['username'],
                    host_config['password'],
                    host_config['command'],
                    host_id,
                    host_config.get('tag', host_id),
                    enable_file_logging
                ))
        else:
            logger.error("No hosts configured. Please add HOSTS list to your config.py")
            sys.exit(1)
        
        logger.info(f"Configured {len(collectors)} host(s) for monitoring")
        
        # Get max points from config
        max_points = getattr(config, 'GRAPH_CONFIG', {}).get('max_points', 100)
        
    else:
        # Use command line arguments
        logger.info("Using command line arguments")
        collectors = []
        
        # Validate command line arguments
        if not args.host:
            logger.error("No hosts specified with --host argument")
            sys.exit(1)
        
        # Validate that arrays have consistent lengths
        num_hosts = len(args.host)
        if args.user and len(args.user) != num_hosts:
            logger.error(f"Number of usernames ({len(args.user)}) must match number of hosts ({num_hosts})")
            sys.exit(1)
        if args.password and len(args.password) != num_hosts:
            logger.error(f"Number of passwords ({len(args.password)}) must match number of hosts ({num_hosts})")
            sys.exit(1)
        if args.command and len(args.command) != num_hosts:
            logger.error(f"Number of commands ({len(args.command)}) must match number of hosts ({num_hosts})")
            sys.exit(1)
        if args.tag and len(args.tag) != num_hosts:
            logger.error(f"Number of tags ({len(args.tag)}) must match number of hosts ({num_hosts})")
            sys.exit(1)
        
        # Ensure we have required fields
        if not args.user or not args.password or not args.command:
            logger.error("Must specify --user, --password, and --command for each host")
            sys.exit(1)
        
        # Create collectors
        for i in range(num_hosts):
            host_id = f"Host-{i+1}"
            tag = args.tag[i] if args.tag else host_id
            collectors.append(RadarDataCollector(
                args.host[i],
                args.user[i],
                args.password[i],
                args.command[i],
                host_id,
                tag,
                args.enable_file_logging
            ))
        
        logger.info(f"Configured {len(collectors)} host(s) for monitoring")
        max_points = args.max_points
    
    if args.test_mode:
        # Test mode: just run SSH connections without GUI for specified duration
        logger.info(f"Running in test mode for {args.test_duration} seconds (SSH connections only)")
        try:
            asyncio.run(run_ssh_collectors(collectors, test_duration=args.test_duration))
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
            logger.info("TIP: Press 'S' to enable scrollback mode for detailed analysis")
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
