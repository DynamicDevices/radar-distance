# Changelog

All notable changes to the Radar Distance Monitor project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2024-12-19

### Added
- Initial release of Radar Distance Monitor
- Real-time SSH connection to two hosts for distance measurement
- Live matplotlib graphing with dual data streams
- Configuration file support with automatic detection
- Command-line argument support as alternative to config files
- Custom tag names for hosts displayed on chart legend
- Data parsing for presence detection and distance measurement
- Automatic graph scaling and real-time updates
- Threaded data collection with async SSH connections
- Error handling for SSH connection failures and malformed data
- Configurable graph settings (max points, update interval)
- Logging support with configurable levels
- Example configuration with documentation

### Features
- **SSH Data Collection**: Connects to two hosts simultaneously via SSH
- **Real-time Graphing**: Updates graph every 100ms with new distance data
- **Custom Host Tags**: Configure meaningful names for chart legend (e.g., "Front Door", "Back Door")
- **Flexible Configuration**: Support for both config files and command-line arguments
- **Data Validation**: Handles presence flags and ignores invalid distance readings
- **Auto-scaling**: Dynamic graph scaling based on incoming data
- **Error Resilience**: Graceful handling of connection errors and data parsing issues

### Dependencies
- asyncssh >= 2.13.0 - For SSH connections
- matplotlib >= 3.7.0 - For real-time graphing
- numpy >= 1.24.0 - For data handling

### Documentation
- Complete README with installation and usage instructions
- Example configuration files
- Command-line help and usage examples
- Project structure documentation
