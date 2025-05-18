# Ultra Temp Cleaner Pro X

A comprehensive system optimization and cleaning tool with advanced features for finding and removing temporary files, optimizing memory, analyzing disk space, detecting duplicates, and more.

## Key Features

### Core Features
- Multi-threaded scanning for maximum performance
- Smart file detection with regex pattern matching
- Secure file deletion with DoD-compliant overwriting
- Browser cache cleaning for all major browsers
- Duplicate file detection and removal
- System tray integration for background operation
- Scheduled cleaning operations
- Comprehensive statistics and visualizations
- Cross-platform support (Windows, macOS, Linux)

### New Ultra Features
- **AI-Powered Cleaning**: Smart recommendations based on machine learning
- **Memory Optimization**: Advanced system memory management and optimization
- **Disk Space Analyzer**: Visual disk space usage analysis
- **Browser Cache Cleaner**: Deep cleaning for 10+ browsers
- **Registry Cleaner**: Windows registry optimization
- **Startup Manager**: Control and optimize system startup
- **Privacy Cleaner**: Remove browsing history and cookies
- **File Shredder**: Secure deletion beyond recovery
- **System Monitor**: Real-time system resource tracking
- **Advanced Scheduler**: Complex scheduling with conditional triggers

## System Requirements
- Windows 10/11, macOS 10.14+, or Linux
- Python 3.7 or higher
- 2GB RAM minimum (4GB recommended)
- 50MB free disk space

## Installation

1. Clone the repository:
```
git clone https://github.com/yourusername/UltraTempCleaner.git
```

2. Install dependencies:
```
pip install -r requirements.txt
```

3. Run the application:
```
python run.py
```

## Modules Overview

### Main Cleaner
The core module for finding and managing temporary files:
- Smart pattern-based file detection
- Multi-threaded scanning for performance
- File categorization and safety checks
- Detailed statistics tracking

### Browser Cache Cleaner
Detect and clean cache files from all major browsers:
- Google Chrome, Firefox, Edge, Safari, Opera, Brave, and more
- Profile detection for multi-user setups
- Selective cleaning (cache, cookies, history)
- Size estimation before cleaning

### Disk Analyzer
Analyze disk space usage with visualization:
- Identify large files and directories
- Interactive disk space map
- File type distribution analysis
- Age-based file categorization
- One-click cleanup of identified space hogs

### Memory Optimizer
Optimize and monitor system memory:
- System cache clearing
- Process memory optimization
- Real-time memory monitoring
- Smart recommendations for optimization
- Process management for memory-intensive applications

### AI Cleaner
Intelligent cleaning recommendations:
- Machine learning-based file classification
- User behavior analysis
- Feedback-driven improvements
- Safety scoring to prevent important file deletion
- Personalized cleaning recommendations

### System Tray Integration
Run the application in the background:
- Quick access to common functions
- Automatic cleaning on schedule
- Notifications for important events
- Minimize-to-tray functionality
- Low resource usage when minimized

## Usage Examples

### Basic Cleanup
```python
from main import TempFileFinder

# Create finder instance
finder = TempFileFinder()

# Scan temp directories
temp_files = finder.scan_for_temp_files()

# Delete files
for file_info in temp_files:
    finder.delete_file(file_info['path'])
```

### Scheduled Cleaning
```python
from schedule import ScheduledCleaner

# Create scheduler
scheduler = ScheduledCleaner()

# Schedule daily cleanup at 2am
scheduler.add_schedule('daily', '02:00')

# Start scheduler
scheduler.start_scheduler()
```

### Browser Cache Cleaning
```python
from browser_cleaner import browser_cleaner

# Detect browsers
browser_data = browser_cleaner.detect_browsers()

# Clean browser caches
browser_cleaner.clean_browser_cache()
```

### Disk Space Analysis
```python
from disk_analyzer import disk_analyzer

# Get available drives
drives = disk_analyzer.get_available_drives()

# Analyze C: drive
analysis = disk_analyzer.analyze_drive('C:/')

# Get largest files
large_files = analysis['results']['large_files']
```

### Memory Optimization
```python
from memory_optimizer import memory_optimizer

# Get memory info
memory_info = memory_optimizer.get_memory_info()

# Optimize memory
optimization = memory_optimizer.optimize_memory()

# Get process memory usage
processes = memory_optimizer.get_process_memory_usage()
```

## Configuration

The application can be configured through the `config.py` module or the UI settings panel. Key configuration options include:

- Scanning settings (thread count, age filters, etc.)
- Cleaning behavior (backup before delete, secure deletion, etc.)
- Scheduling options (frequency, time, automatic cleaning)
- UI preferences (theme, sidebar visibility, etc.)
- Advanced settings (logging, API access, etc.)

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📧 Contact

For support or feature requests, please create an issue in the repository.

---

*Ultra Temp Cleaner Pro - Keep your system clean and optimized!*