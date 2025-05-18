import os
import tempfile
import glob
import shutil
from pathlib import Path
import time
import logging
import concurrent.futures
import re
import hashlib
from typing import List, Dict, Any, Callable, Optional, Set, Tuple

# Import new modules
try:
    from config import config_manager
    CONFIG_AVAILABLE = True
except ImportError:
    CONFIG_AVAILABLE = False
    logging.warning("Config module not available. Using default settings.")

try:
    from browser_cleaner import browser_cleaner
    BROWSER_CLEANER_AVAILABLE = True
except ImportError:
    BROWSER_CLEANER_AVAILABLE = False
    logging.warning("Browser cleaner module not available.")

try:
    from disk_analyzer import disk_analyzer
    DISK_ANALYZER_AVAILABLE = True
except ImportError:
    DISK_ANALYZER_AVAILABLE = False
    logging.warning("Disk analyzer module not available.")

try:
    from memory_optimizer import memory_optimizer
    MEMORY_OPTIMIZER_AVAILABLE = True
except ImportError:
    MEMORY_OPTIMIZER_AVAILABLE = False
    logging.warning("Memory optimizer module not available.")

try:
    from ai_cleaner import ai_cleaner
    AI_CLEANER_AVAILABLE = True
except ImportError:
    AI_CLEANER_AVAILABLE = False
    logging.warning("AI cleaner module not available.")

class TempFileFinder:
    def __init__(self):
        self.temp_patterns = [
            # Basic temp files
            '*.tmp', '~*', '*.cache', '*.log', 'Thumbs.db', '.DS_Store', '*.bak', '*._mp', '*.temp',
            # Browser cache
            'Cache/*', '*.crdownload', '*.part', '*.download',
            # Development
            '*.pyc', '__pycache__', '.pytest_cache', '.coverage', 'node_modules',
            'npm-debug.log*', 'yarn-debug.log*', '*.pid', '*.sock',
            # Office temp files
            '~$*.doc*', '~$*.xls*', '~$*.ppt*', '*.~*',
            # System files
            '*.dmp', '*.crash', '*.dump', '*.stackdump', '*.core',
            'desktop.ini', '*.swp', '*.swo', '*.swn',
            # Build artifacts
            'build/*', 'dist/*', '*.o', '*.obj', '*.class',
            # IDE specific
            '.idea/*', '.vscode/*', '*.iml', '*.suo',
            # Package managers
            'pip-log.txt', 'pip-delete-this-directory.txt',
            # Thumbnails
            '.thumbnails/*', 'thumbs.db', '.thumb',
            # Misc
            '*.old', '*.prv', '*.temp.*', '*.chk'
        ]
        # Compile regex patterns for faster matching
        self.temp_regex_patterns = self._compile_glob_patterns(self.temp_patterns)
        
        self.scanning = False
        self.total_size = 0
        self.file_stats = {
            'by_type': {},
            'by_age': {'recent': 0, 'week': 0, 'month': 0, 'old': 0},
            'by_size': {'small': 0, 'medium': 0, 'large': 0, 'huge': 0}
        }
        self.excluded_dirs = set(['.git', 'node_modules', 'venv', 'env', 'System Volume Information'])
        self.min_file_age = 0  # minimum age in days to consider for deletion
        self.protected_extensions = {'.exe', '.dll', '.sys', '.ini', '.drv', '.com', '.bat', '.msi'}
        self.found_files_count = 0
        
        # For tracking scan progress
        self.scanned_dirs_count = 0
        self.total_dirs_count = 0
        self.scan_start_time = 0
        
        # Thread pool for parallel scanning
        self.max_workers = min(32, os.cpu_count() + 4)

        # Queue for file updates to prevent thread conflicts
        self.file_queue = []
        
        # Setup logging
        logging.basicConfig(filename='temp_file_finder.log', level=logging.DEBUG,
                            format='%(asctime)s - %(levelname)s - %(message)s')

        # For duplicate file detection
        self.content_hashes = {}
        self.duplicate_files = []
        self.duplicate_size = 0

        # Special directories to protect
        self.protected_dirs = []
        
        # File patterns configuration
        self.file_patterns = self._load_file_patterns()
        
        # Load configuration if available
        if CONFIG_AVAILABLE:
            self.min_file_age = config_manager.get("scanning", "default_min_age", 0)
            self.concurrent_threads = config_manager.get("scanning", "thread_count", 4)
            self.protected_dirs = config_manager.get("scanning", "excluded_dirs", [])
            self.excluded_dirs = self.protected_dirs.copy()
        
        # Detection statistics
        self.stats = {
            "by_type": {},
            "by_age": {},
            "by_size": {}
        }

    def _compile_glob_patterns(self, glob_patterns: List[str]) -> List[re.Pattern]:
        """Convert glob patterns to regex patterns for faster matching"""
        regex_patterns = []
        for pattern in glob_patterns:
            # Convert glob pattern to regex pattern
            regex = pattern.replace(".", "\\.").replace("*", ".*").replace("?", ".") 
            regex = f"^{regex}$"
            regex_patterns.append(re.compile(regex, re.IGNORECASE))
        return regex_patterns
    
    def is_temp_file(self, file_path: str) -> bool:
        """Check if a file matches any temp pattern using compiled regex"""
        file_name = os.path.basename(file_path)
        for pattern in self.temp_regex_patterns:
            if pattern.match(file_name):
                return True
        return False

    def get_system_temp_dirs(self) -> List[str]:
        temp_dirs = []
        # Add system temp directory
        temp_dirs.append(tempfile.gettempdir())
        # Add user temp directories if available
        if os.name == 'nt':  # Windows
            temp_dirs.extend([
                os.path.expandvars('%TEMP%'),
                os.path.expandvars('%TMP%'),
                os.path.expandvars('%LOCALAPPDATA%\\Temp'),
                os.path.expandvars('%WINDIR%\\Temp'),
                os.path.expandvars('%USERPROFILE%\\AppData\\Local\\Temp'),
                os.path.expandvars('%PROGRAMDATA%\\Temp'),
                # Add browser cache locations
                os.path.expandvars('%LOCALAPPDATA%\\Google\\Chrome\\User Data\\Default\\Cache'),
                os.path.expandvars('%LOCALAPPDATA%\\Mozilla\\Firefox\\Profiles'),
                os.path.expandvars('%LOCALAPPDATA%\\Microsoft\\Windows\\INetCache')
            ])
        else:  # Unix-like systems
            temp_dirs.extend([
                '/tmp',
                '/var/tmp',
                os.path.expanduser('~/.cache'),
                '/var/cache',
                # Add browser cache locations
                os.path.expanduser('~/.cache/google-chrome'),
                os.path.expanduser('~/.cache/mozilla/firefox'),
                os.path.expanduser('~/.cache/chromium')
            ])
        # Filter out non-existent directories
        temp_dirs = [d for d in temp_dirs if os.path.exists(d)]
        logging.debug(f"System temp directories: {temp_dirs}")
        return list(set(temp_dirs))

    def categorize_file(self, file_info: Dict[str, Any]) -> None:
        # Categorize by extension
        ext = os.path.splitext(file_info['path'])[1].lower()
        if not ext:
            ext = '(no extension)'
        if ext not in self.file_stats['by_type']:
            self.file_stats['by_type'][ext] = 0
        self.file_stats['by_type'][ext] += file_info['size']

        # Categorize by age
        age_days = file_info['age_days']
        if age_days < 7:
            self.file_stats['by_age']['recent'] += file_info['size']
        elif age_days < 30:
            self.file_stats['by_age']['week'] += file_info['size']
        elif age_days < 90:
            self.file_stats['by_age']['month'] += file_info['size']
        else:
            self.file_stats['by_age']['old'] += file_info['size']

        # Categorize by size
        size_mb = file_info['size'] / (1024 * 1024)
        if size_mb < 1:
            self.file_stats['by_size']['small'] += file_info['size']
        elif size_mb < 10:
            self.file_stats['by_size']['medium'] += file_info['size']
        elif size_mb < 100:
            self.file_stats['by_size']['large'] += file_info['size']
        else:
            self.file_stats['by_size']['huge'] += file_info['size']

    def scan_for_temp_files(self, start_path: Optional[str], callback: Optional[Callable] = None) -> List[Dict[str, Any]]:
        """Scan for temporary files with parallel processing"""
        self.reset_stats()
        self.file_queue = []
        self.found_files_count = 0
        self.scan_start_time = time.time()
        
        temp_files = []
        try:
            if start_path is None:
                logging.info("Scanning all drives...")
                if os.name == 'nt':  # Windows
                    try:
                        import win32api
                        drives = win32api.GetLogicalDriveStrings().split('\000')[:-1]
                        # Scan drives in parallel
                        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                            if self.scanning:
                                # Create a list to hold all futures
                                future_to_drive = {
                                    executor.submit(self._scan_directory, drive, callback): drive 
                                    for drive in drives
                                }
                                for future in concurrent.futures.as_completed(future_to_drive):
                                    drive = future_to_drive[future]
                                    try:
                                        drive_temp_files = future.result()
                                        temp_files.extend(drive_temp_files)
                                    except Exception as e:
                                        logging.error(f"Error scanning drive {drive}: {e}")
                    except ImportError:
                        logging.error("win32api module not found. Using alternative method.")
                        # Fallback for Windows without win32api
                        import string
                        from ctypes import windll
                        drives = []
                        bitmask = windll.kernel32.GetLogicalDrives()
                        for letter in string.ascii_uppercase:
                            if bitmask & 1:
                                drives.append(letter + ':\\')
                            bitmask >>= 1
                        # Scan drives in parallel
                        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                            if self.scanning:
                                futures = [executor.submit(self._scan_directory, drive, callback) for drive in drives]
                                for future in concurrent.futures.as_completed(futures):
                                    try:
                                        drive_temp_files = future.result()
                                        temp_files.extend(drive_temp_files)
                                    except Exception as e:
                                        logging.error(f"Error scanning drive: {e}")
                else:  # Unix-like systems
                    temp_files.extend(self._scan_directory('/', callback))
            else:
                # Single directory scan
                temp_files.extend(self._scan_directory(start_path, callback))
                
            # Process any remaining files in the queue
            temp_files.extend(self.file_queue)
            
            # Calculate percentages for statistics
            self._calculate_percentages()
            
            # Log scan completion
            scan_duration = time.time() - self.scan_start_time
            logging.info(f"Scan completed. Found {len(temp_files)} files in {scan_duration:.2f} seconds.")
            logging.info(f"Total size: {self.format_size(self.total_size)}")
            
        except Exception as e:
            logging.error(f"Error during scan: {e}")
        
        return temp_files

    def _calculate_percentages(self) -> None:
        """Calculate percentages for each category in statistics"""
        total = self.total_size
        if total == 0:
            return
            
        # Add percentage to all stat categories
        for category_type in self.file_stats.keys():
            for category, size in self.file_stats[category_type].items():
                # Calculate percentage
                percentage = (size / total) * 100 if total > 0 else 0
                # Store both size and percentage
                self.file_stats[category_type][category] = {
                    'size': size,
                    'size_formatted': self.format_size(size),
                    'percent': percentage
                }

    def _scan_directory(self, start_path: str, callback: Optional[Callable] = None) -> List[Dict[str, Any]]:
        """Scan a single directory recursively for temporary files"""
        temp_files = []
        try:
            # Skip if the directory itself is in the excluded list
            dir_name = os.path.basename(start_path)
            if dir_name in self.excluded_dirs:
                return []
                
            for root, dirs, files in os.walk(start_path, topdown=True):
                if not self.scanning:
                    break
                    
                self.scanned_dirs_count += 1

                # Skip excluded directories
                dirs[:] = [d for d in dirs if d not in self.excluded_dirs]
                
                # Process all files in this directory
                for file_name in files:
                    file_path = os.path.join(root, file_name)
                    
                    # Check against temp patterns directly
                    if self.is_temp_file(file_path):
                        try:
                            file_info = self._get_file_info(file_path)
                            if file_info:
                                temp_files.append(file_info)
                                self.file_queue.append(file_info)
                                self.found_files_count += 1
                                
                                if callback and self.found_files_count % 10 == 0:
                                    callback(file_info)
                        except (PermissionError, FileNotFoundError):
                            continue
        except PermissionError as e:
            logging.error(f"Permission error in directory {start_path}: {e}")
        except Exception as e:
            logging.error(f"Error scanning directory {start_path}: {e}")
            
        return temp_files

    def get_file_age(self, timestamp: float) -> str:
        """Get a human-readable representation of a file's age"""
        age_seconds = time.time() - timestamp
        
        # Less than an hour
        if age_seconds < 3600:
            minutes = age_seconds / 60
            return "Less than an hour" if minutes < 1 else f"{int(minutes)} minutes"
            
        # Less than a day
        if age_seconds < 86400:
            hours = age_seconds / 3600
            return f"{int(hours)} hours"
            
        # Less than a week
        if age_seconds < 604800:
            days = age_seconds / 86400
            return f"{int(days)} days"
            
        # Less than a month
        if age_seconds < 2592000:
            weeks = age_seconds / 604800
            return f"{int(weeks)} weeks"
            
        # Less than a year
        if age_seconds < 31536000:
            months = age_seconds / 2592000
            return f"{int(months)} months"
            
        # Years
        years = age_seconds / 31536000
        return f"{int(years)} years"

    def _get_file_info(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a file"""
        try:
            if not os.path.exists(file_path):
                return None
                
            stats = os.stat(file_path)
            size = stats.st_size
            modified_time = stats.st_mtime
            created_time = stats.st_ctime
            age_days = (time.time() - modified_time) / 86400

            # Skip if file is newer than minimum age
            if age_days < self.min_file_age:
                return None
                
            # Extract file extension
            file_ext = os.path.splitext(file_path)[1].lower() or '(no extension)'
            
            # Check if file is protected
            is_protected = self._is_protected_file(file_path)
            
            file_info = {
                'path': file_path,
                'size': size,
                'size_formatted': self.format_size(size),
                'modified': modified_time,
                'created': created_time,
                'age': self.get_file_age(modified_time),
                'age_days': age_days,
                'type': file_ext,
                'is_locked': self.is_file_locked(file_path),
                'is_protected': is_protected
            }

            self.total_size += size
            self.categorize_file(file_info)
            return file_info
        except (PermissionError, FileNotFoundError):
            return None
        except Exception as e:
            logging.error(f"Error getting file info for {file_path}: {e}")
            return None

    def is_file_locked(self, file_path: str) -> bool:
        """Check if a file is locked by another process"""
        try:
            # Skip check for non-existent files
            if not os.path.exists(file_path):
                return False
                
            with open(file_path, 'rb+') as f:
                return False
        except (IOError, PermissionError):
            return True

    def get_stats_summary(self) -> Dict[str, Any]:
        """Get a summary of file statistics with enhanced percentage information"""
        return {
            'total_size': self.format_size(self.total_size),
            'total_files': self.found_files_count,
            'scan_duration': time.time() - self.scan_start_time,
            'file_stats': self.file_stats
        }

    def set_min_file_age(self, days: int) -> None:
        """Set the minimum age of files to consider for deletion"""
        self.min_file_age = max(0, days)  # Ensure non-negative

    def add_excluded_dir(self, dir_path: str) -> None:
        """Add a directory to the exclusion list"""
        self.excluded_dirs.add(dir_path)
        logging.info(f"Added {dir_path} to excluded directories")

    def remove_excluded_dir(self, dir_path: str) -> None:
        """Remove a directory from the exclusion list"""
        self.excluded_dirs.discard(dir_path)
        logging.info(f"Removed {dir_path} from excluded directories")

    @staticmethod
    def format_size(size: float) -> str:
        """Format file size in a human-readable format"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.2f} {unit}"
            size /= 1024
        return f"{size:.2f} TB"

    def delete_file(self, file_path: str) -> bool:
        """Delete a file with enhanced safety checks"""
        try:
            if not os.path.exists(file_path):
                logging.warning(f"File not found: {file_path}")
                return False
            
            # Extract file extension
            file_ext = os.path.splitext(file_path)[1].lower()
            
            # Protect system files
            if file_ext in self.protected_extensions:
                if os.path.dirname(file_path).lower().startswith(os.environ.get('WINDIR', 'C:\\Windows').lower()):
                    logging.warning(f"Protected system file: {file_path}")
                    return False
            
            # Create backup before deletion if it's an important location
            self._backup_file_if_needed(file_path)
            
            if os.path.isdir(file_path):
                shutil.rmtree(file_path)
            else:
                os.remove(file_path)
            logging.info(f"Successfully deleted: {file_path}")
            return True
        except (PermissionError, FileNotFoundError) as e:
            logging.error(f"Error deleting file {file_path}: {e}")
            return False
        except Exception as e:
            logging.error(f"Unexpected error deleting file {file_path}: {e}")
            return False
            
    def _backup_file_if_needed(self, file_path: str) -> None:
        """Create a backup of important files before deletion"""
        try:
            # Skip backup for very large files
            if os.path.getsize(file_path) > 50 * 1024 * 1024:  # > 50MB
                return
                
            # Determine if this is a critical location
            critical_locations = [
                os.environ.get('WINDIR', 'C:\\Windows').lower(),
                os.environ.get('SYSTEMROOT', 'C:\\Windows').lower(),
                '/etc', 
                '/var/lib'
            ]
            
            is_critical = any(file_path.lower().startswith(loc.lower()) for loc in critical_locations)
            
            if is_critical and os.path.isfile(file_path):
                # Create backup directory if it doesn't exist
                backup_dir = os.path.join(tempfile.gettempdir(), 'temp_cleaner_backups')
                os.makedirs(backup_dir, exist_ok=True)
                
                # Create a backup with timestamp
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                filename = os.path.basename(file_path)
                backup_path = os.path.join(backup_dir, f"{filename}_{timestamp}.bak")
                
                shutil.copy2(file_path, backup_path)
                logging.info(f"Created backup of {file_path} at {backup_path}")
        except Exception as e:
            logging.error(f"Failed to create backup for {file_path}: {e}")

    def reset_stats(self) -> None:
        """Reset all statistics"""
        self.total_size = 0
        self.found_files_count = 0
        self.scanned_dirs_count = 0
        self.file_stats = {
            'by_type': {},
            'by_age': {'recent': 0, 'week': 0, 'month': 0, 'old': 0},
            'by_size': {'small': 0, 'medium': 0, 'large': 0, 'huge': 0}
        }
        self.scan_start_time = 0

    def get_file_age(self, timestamp: float) -> str:
        """Get a human-readable representation of a file's age"""
        age_seconds = time.time() - timestamp
        
        # Less than an hour
        if age_seconds < 3600:
            minutes = age_seconds / 60
            return "Less than an hour" if minutes < 1 else f"{int(minutes)} minutes"
            
        # Less than a day
        if age_seconds < 86400:
            hours = age_seconds / 3600
            return f"{int(hours)} hours"
            
        # Less than a week
        if age_seconds < 604800:
            days = age_seconds / 86400
            return f"{int(days)} days"
            
        # Less than a month
        if age_seconds < 2592000:
            weeks = age_seconds / 604800
            return f"{int(weeks)} weeks"
            
        # Less than a year
        if age_seconds < 31536000:
            months = age_seconds / 2592000
            return f"{int(months)} months"
            
        # Years
        years = age_seconds / 31536000
        return f"{int(years)} years"

    def get_available_drives(self) -> List[str]:
        """Get a list of available drives"""
        if os.name == 'nt':  # Windows
            try:
                import win32api
                drives = win32api.GetLogicalDriveStrings().split('\000')[:-1]
                return drives
            except ImportError:
                # Fallback for Windows without win32api
                import string
                from ctypes import windll
                drives = []
                bitmask = windll.kernel32.GetLogicalDrives()
                for letter in string.ascii_uppercase:
                    if bitmask & 1:
                        drives.append(letter + ':\\')
                    bitmask >>= 1
                return drives
        else:  # Unix-like systems
            return ['/']  # Unix systems have a single root

    def find_duplicate_files(self, files: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Find duplicate files based on content hash
        
        Args:
            files: List of file info dictionaries to check
            
        Returns:
            Dictionary with duplicate file information
        """
        self.content_hashes = {}
        self.duplicate_files = []
        self.duplicate_size = 0
        
        logging.info(f"Checking {len(files)} files for duplicates")
        
        # First pass: calculate hashes for all files
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_file = {executor.submit(self._calculate_file_hash, file): file for file in files}
            
            for future in concurrent.futures.as_completed(future_to_file):
                file = future_to_file[future]
                try:
                    file_hash = future.result()
                    if file_hash:
                        file['content_hash'] = file_hash
                        
                        # Track files with the same hash
                        if file_hash in self.content_hashes:
                            self.content_hashes[file_hash].append(file)
                        else:
                            self.content_hashes[file_hash] = [file]
                except Exception as e:
                    logging.error(f"Error calculating hash for {file['path']}: {e}")
        
        # Second pass: identify duplicates (files with same hash)
        duplicate_groups = []
        for file_hash, files in self.content_hashes.items():
            if len(files) > 1:
                # Sort by modified date (newest first)
                sorted_files = sorted(files, key=lambda x: x['modified'], reverse=True)
                
                # First file is the original, rest are duplicates
                original = sorted_files[0]
                duplicates = sorted_files[1:]
                
                duplicate_size = sum(f['size'] for f in duplicates)
                self.duplicate_size += duplicate_size
                
                duplicate_groups.append({
                    'original': original,
                    'duplicates': duplicates,
                    'hash': file_hash,
                    'count': len(duplicates),
                    'size': duplicate_size,
                    'size_formatted': self.format_size(duplicate_size)
                })
                
                # Add to flat list of duplicates
                self.duplicate_files.extend(duplicates)
        
        # Sort groups by size (largest first)
        duplicate_groups.sort(key=lambda x: x['size'], reverse=True)
        
        result = {
            'groups': duplicate_groups,
            'total_duplicates': len(self.duplicate_files),
            'total_size': self.duplicate_size,
            'total_size_formatted': self.format_size(self.duplicate_size)
        }
        
        logging.info(f"Found {result['total_duplicates']} duplicate files ({result['total_size_formatted']})")
        return result
    
    def _calculate_file_hash(self, file_info: Dict[str, Any]) -> Optional[str]:
        """Calculate MD5 hash of file contents
        
        Args:
            file_info: File information dictionary
            
        Returns:
            MD5 hash of file contents or None if error
        """
        try:
            file_path = file_info['path']
            
            # Skip if file doesn't exist or is too large (>100MB)
            if not os.path.exists(file_path) or file_info['size'] > 100 * 1024 * 1024:
                return None
                
            # Skip if file is locked
            if self.is_file_locked(file_path):
                return None
                
            # Calculate hash
            md5_hash = hashlib.md5()
            
            with open(file_path, 'rb') as f:
                # Read in chunks to handle large files efficiently
                for chunk in iter(lambda: f.read(4096), b''):
                    md5_hash.update(chunk)
                    
            return md5_hash.hexdigest()
            
        except (PermissionError, FileNotFoundError):
            return None
        except Exception as e:
            logging.error(f"Error calculating hash for {file_info['path']}: {e}")
            return None

    def _load_file_patterns(self) -> Dict[str, List[str]]:
        """Load file patterns to identify different types of temp files"""
        return {
            "temp_files": [
                r".*\.tmp$", r".*\.temp$", r".*\.bak$", r".*\.old$", 
                r".*\.swp$", r".*~$", r"Thumbs\.db$", r".*\.crdownload$"
            ],
            "log_files": [
                r".*\.log$", r".*\.log\.\d+$", r".*\.dmp$", r".*\.crash$",
                r".*\.stackdump$", r".*\.mdmp$", r".*\.inprogress$"
            ],
            "cache_files": [
                r".*\.cache$", r".*\.chk$", r".*\.nch$", r".*cache.*\.dat$",
                r".*\.etl$", r".*\.evt$"
            ],
            "browser_files": [
                r"Cache.*", r"cookies\.sqlite.*", r"webappsstore\.sqlite.*",
                r"history\.dat", r"places\.sqlite.*", r".*localstorage$"
            ],
            "system_temp": [
                r".*\.sys$", r"hiberfil\.sys$", r"pagefile\.sys$"
            ]
        }

    def _is_protected_file(self, file_path):
        """Check if a file is protected (should not be deleted)
        
        Args:
            file_path: Path to the file
            
        Returns:
            True if file is protected, False otherwise
        """
        path_lower = file_path.lower()
        
        # Check if path contains any protected directory
        for protected_dir in self.protected_dirs:
            if protected_dir.lower() in path_lower:
                return True
                
        # Check for common system directories
        system_dirs = [
            'windows', 'system32', 'system', 'program files',
            'microsoft', 'systemroot', 'boot'
        ]
        
        if any(system_dir in path_lower for system_dir in system_dirs):
            return True
            
        # Check for extension whitelist (files that should never be deleted)
        protected_extensions = [
            '.exe', '.dll', '.sys', '.com', '.bat', '.msi',
            '.ini', '.inf', '.drv', '.cat', '.reg'
        ]
        
        _, ext = os.path.splitext(file_path)
        if ext.lower() in protected_extensions:
            return True
            
        return False

    def clean_browser_cache(self) -> Dict[str, Any]:
        """Clean browser caches
        
        Returns:
            Dictionary with cleaning results
        """
        if not BROWSER_CLEANER_AVAILABLE:
            return {
                "success": False,
                "error": "Browser cleaner module not available"
            }
            
        try:
            # First detect browsers
            browser_data = browser_cleaner.detect_browsers()
            
            # Clean browser caches
            results = browser_cleaner.clean_browser_cache()
            
            return {
                "success": True,
                "browsers": browser_data,
                "cleaned": results
            }
            
        except Exception as e:
            logging.error(f"Error cleaning browser cache: {e}")
            return {
                "success": False,
                "error": str(e)
            }
            
    def analyze_disk_space(self, drive_path: str, callback: Optional[Callable] = None) -> Dict[str, Any]:
        """Analyze disk space usage
        
        Args:
            drive_path: Path to drive or directory to analyze
            callback: Optional callback function for progress updates
            
        Returns:
            Dictionary with analysis results
        """
        if not DISK_ANALYZER_AVAILABLE:
            return {
                "success": False,
                "error": "Disk analyzer module not available"
            }
            
        try:
            # Use disk analyzer module
            results = disk_analyzer.analyze_drive(drive_path, callback)
            
            return results
            
        except Exception as e:
            logging.error(f"Error analyzing disk space: {e}")
            return {
                "success": False,
                "error": str(e)
            }
            
    def optimize_memory(self) -> Dict[str, Any]:
        """Optimize system memory
        
        Returns:
            Dictionary with optimization results
        """
        if not MEMORY_OPTIMIZER_AVAILABLE:
            return {
                "success": False,
                "error": "Memory optimizer module not available"
            }
            
        try:
            # Use memory optimizer module
            results = memory_optimizer.optimize_memory()
            
            return results
            
        except Exception as e:
            logging.error(f"Error optimizing memory: {e}")
            return {
                "success": False,
                "error": str(e)
            }
            
    def get_ai_recommendations(self, files: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Get AI-powered cleaning recommendations
        
        Args:
            files: List of file information dictionaries
            
        Returns:
            Dictionary with recommendation results
        """
        if not AI_CLEANER_AVAILABLE:
            return {
                "success": False,
                "error": "AI cleaner module not available"
            }
            
        try:
            # Use AI cleaner module
            results = ai_cleaner.predict_deletion_candidates(files)
            
            return results
            
        except Exception as e:
            logging.error(f"Error getting AI recommendations: {e}")
            return {
                "success": False,
                "error": str(e)
            }
            
    def provide_ai_feedback(self, file_path: str, should_delete: bool) -> bool:
        """Provide feedback to AI cleaner to improve recommendations
        
        Args:
            file_path: Path to file
            should_delete: True if file should be deleted, False otherwise
            
        Returns:
            True if feedback was recorded, False otherwise
        """
        if not AI_CLEANER_AVAILABLE:
            return False
            
        try:
            # Provide feedback
            ai_cleaner.provide_feedback(file_path, should_delete)
            return True
            
        except Exception as e:
            logging.error(f"Error providing AI feedback: {e}")
            return False
