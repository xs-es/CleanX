#!/usr/bin/env python3
"""
Disk Space Analyzer Module for Ultra Temp Cleaner Pro
----------------------------------------------------
Analyzes disk space usage to identify large files and folders
"""

import os
import platform
import time
import json
import logging
import threading
import queue
from typing import Dict, List, Tuple, Any, Optional, Set, Callable
from pathlib import Path
import concurrent.futures

# Try to import platform-specific modules
if platform.system() == "Windows":
    try:
        import win32api
        import win32file
        WINDOWS_MODULES_AVAILABLE = True
    except ImportError:
        WINDOWS_MODULES_AVAILABLE = False
else:
    WINDOWS_MODULES_AVAILABLE = False

# Import local modules
from config import config_manager

class DiskAnalyzer:
    """Disk space analyzer for finding large files and analyzing usage patterns"""
    
    def __init__(self, max_threads: int = 4):
        """Initialize disk analyzer
        
        Args:
            max_threads: Maximum number of threads to use for scanning
        """
        self.scanning = False
        self.paused = False
        self.max_threads = max_threads
        self.queue = queue.Queue()
        self.results = {}
        self.excluded_dirs = set()
        self.excluded_patterns = set()
        self.total_size = 0
        self.files_count = 0
        self.dirs_count = 0
        self.scan_start_time = 0
        self.large_files = []
        self.large_dirs = []
        self.file_types = {}
        self.age_categories = {}
        self.callback = None
        
        # Load excluded directories from config
        self._load_excluded_dirs()
    
    def _load_excluded_dirs(self):
        """Load excluded directories from config"""
        excluded_dirs = config_manager.get("scanning", "excluded_dirs", [])
        self.excluded_dirs = set(excluded_dirs)
        
        # Add common system directories to exclude
        system = platform.system()
        if system == "Windows":
            self.excluded_dirs.update([
                "C:\\Windows\\System32",
                "C:\\Windows\\SysWOW64",
                "C:\\Windows\\WinSxS",
                "C:\\System Volume Information",
                "C:\\$Recycle.Bin"
            ])
        elif system == "Darwin":  # macOS
            self.excluded_dirs.update([
                "/System",
                "/Library/Caches",
                "/private/var/db"
            ])
        else:  # Linux
            self.excluded_dirs.update([
                "/proc",
                "/sys",
                "/dev",
                "/run",
                "/tmp"
            ])
        
        # Add patterns to exclude
        self.excluded_patterns = {
            ".git", "node_modules", "__pycache__", ".venv",
            "venv", ".env", ".vs", ".idea", ".vscode"
        }
    
    def add_excluded_dir(self, directory: str):
        """Add a directory to exclude from scanning
        
        Args:
            directory: Directory path to exclude
        """
        self.excluded_dirs.add(directory)
    
    def remove_excluded_dir(self, directory: str):
        """Remove a directory from the exclusion list
        
        Args:
            directory: Directory path to remove from exclusions
        """
        if directory in self.excluded_dirs:
            self.excluded_dirs.remove(directory)
    
    def get_available_drives(self) -> List[Dict[str, Any]]:
        """Get list of available drives with space information
        
        Returns:
            List of drive dictionaries with path, label, total and free space
        """
        drives = []
        system = platform.system()
        
        if system == "Windows":
            if WINDOWS_MODULES_AVAILABLE:
                # Use win32api to get drive information
                drive_letters = win32api.GetLogicalDriveStrings().split('\000')[:-1]
                
                for drive in drive_letters:
                    try:
                        # Get drive type (e.g. removable, fixed, network)
                        drive_type = win32file.GetDriveType(drive)
                        
                        # Skip unavailable drives
                        if drive_type == 1:  # DRIVE_NO_ROOT_DIR
                            continue
                        
                        # Get volume information
                        vol_name, vol_serial, max_comp_len, fs_flags, fs_name = win32api.GetVolumeInformation(drive)
                        
                        # Get disk space information
                        sectors_per_cluster, bytes_per_sector, free_clusters, total_clusters = win32file.GetDiskFreeSpace(drive)
                        bytes_per_cluster = sectors_per_cluster * bytes_per_sector
                        
                        # Calculate total and free space
                        total_bytes = total_clusters * bytes_per_cluster
                        free_bytes = free_clusters * bytes_per_cluster
                        
                        # Format drive label nicely
                        drive_label = vol_name if vol_name else f"Local Disk ({drive[0]}:)"
                        
                        drives.append({
                            "path": drive,
                            "label": drive_label,
                            "type": self._get_drive_type_name(drive_type),
                            "filesystem": fs_name,
                            "total_bytes": total_bytes,
                            "free_bytes": free_bytes,
                            "used_bytes": total_bytes - free_bytes,
                            "total_formatted": self._format_size(total_bytes),
                            "free_formatted": self._format_size(free_bytes),
                            "used_formatted": self._format_size(total_bytes - free_bytes),
                            "percent_used": int((total_bytes - free_bytes) / total_bytes * 100) if total_bytes > 0 else 0
                        })
                    except Exception as e:
                        logging.error(f"Error getting information for drive {drive}: {e}")
            else:
                # Fallback for Windows without win32api
                for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
                    drive = f"{letter}:\\"
                    if os.path.exists(drive):
                        try:
                            # Get drive space information
                            total_bytes, free_bytes = self._get_drive_space(drive)
                            
                            drives.append({
                                "path": drive,
                                "label": f"Drive ({letter}:)",
                                "type": "Unknown",
                                "filesystem": "Unknown",
                                "total_bytes": total_bytes,
                                "free_bytes": free_bytes,
                                "used_bytes": total_bytes - free_bytes,
                                "total_formatted": self._format_size(total_bytes),
                                "free_formatted": self._format_size(free_bytes),
                                "used_formatted": self._format_size(total_bytes - free_bytes),
                                "percent_used": int((total_bytes - free_bytes) / total_bytes * 100) if total_bytes > 0 else 0
                            })
                        except:
                            pass
        else:
            # Unix-based systems (macOS, Linux)
            try:
                import shutil
                
                # Get mount points
                with os.popen("mount") as pipe:
                    mount_output = pipe.read()
                
                # Process mount points
                mount_points = []
                
                if system == "Darwin":  # macOS
                    # Focus on common macOS locations
                    mount_points = ["/", "/Users", "/Volumes"]
                    
                    # Add any additional mounted volumes
                    for line in mount_output.splitlines():
                        if "/Volumes/" in line:
                            parts = line.split()
                            mount_point = None
                            for part in parts:
                                if part.startswith("/Volumes/"):
                                    mount_point = part
                                    break
                            
                            if mount_point and os.path.exists(mount_point) and mount_point not in mount_points:
                                mount_points.append(mount_point)
                else:  # Linux
                    # Common Linux mount points
                    mount_points = ["/", "/home"]
                    
                    # Add media and mnt directories
                    for media_dir in ["/media", "/mnt"]:
                        if os.path.exists(media_dir):
                            for subdir in os.listdir(media_dir):
                                full_path = os.path.join(media_dir, subdir)
                                if os.path.ismount(full_path) and full_path not in mount_points:
                                    mount_points.append(full_path)
                
                # Get information for each mount point
                for mount_point in mount_points:
                    try:
                        if os.path.exists(mount_point):
                            total_bytes, free_bytes = self._get_drive_space(mount_point)
                            
                            # Get drive label
                            drive_label = os.path.basename(mount_point) if os.path.basename(mount_point) else mount_point
                            
                            # Get filesystem type
                            fs_type = "Unknown"
                            for line in mount_output.splitlines():
                                if mount_point in line:
                                    parts = line.split()
                                    if "type" in line:
                                        type_index = parts.index("type")
                                        if type_index + 1 < len(parts):
                                            fs_type = parts[type_index + 1].split(",")[0]
                                    break
                            
                            drives.append({
                                "path": mount_point,
                                "label": drive_label,
                                "type": "Fixed" if mount_point in ["/", "/home", "/Users"] else "Removable",
                                "filesystem": fs_type,
                                "total_bytes": total_bytes,
                                "free_bytes": free_bytes,
                                "used_bytes": total_bytes - free_bytes,
                                "total_formatted": self._format_size(total_bytes),
                                "free_formatted": self._format_size(free_bytes),
                                "used_formatted": self._format_size(total_bytes - free_bytes),
                                "percent_used": int((total_bytes - free_bytes) / total_bytes * 100) if total_bytes > 0 else 0
                            })
                    except Exception as e:
                        logging.error(f"Error getting information for mount point {mount_point}: {e}")
            except Exception as e:
                logging.error(f"Error getting drive information: {e}")
        
        return drives
    
    def _get_drive_space(self, path: str) -> Tuple[int, int]:
        """Get total and free space for a drive or mount point
        
        Args:
            path: Drive or mount point path
            
        Returns:
            Tuple of (total_bytes, free_bytes)
        """
        try:
            import shutil
            total_bytes, used_bytes, free_bytes = shutil.disk_usage(path)
            return total_bytes, free_bytes
        except:
            # Fallback
            stats = os.statvfs(path)
            free_bytes = stats.f_bavail * stats.f_frsize
            total_bytes = stats.f_blocks * stats.f_frsize
            return total_bytes, free_bytes
    
    def _get_drive_type_name(self, drive_type: int) -> str:
        """Convert Windows drive type to readable name
        
        Args:
            drive_type: Drive type code from win32file.GetDriveType
            
        Returns:
            Human-readable drive type
        """
        drive_types = {
            0: "Unknown",
            1: "No Root Directory",
            2: "Removable",
            3: "Fixed",
            4: "Network",
            5: "CD-ROM",
            6: "RAM Disk"
        }
        return drive_types.get(drive_type, "Unknown")
    
    def analyze_drive(self, drive_path: str, callback: Optional[Callable] = None, 
                     min_file_size: int = 1024 * 1024, # 1 MB
                     max_files: int = 1000) -> Dict[str, Any]:
        """Analyze disk space usage for a drive
        
        Args:
            drive_path: Drive path to analyze
            callback: Optional callback function to report progress
            min_file_size: Minimum file size to track individually
            max_files: Maximum number of large files to track
            
        Returns:
            Dictionary with analysis results
        """
        if not os.path.exists(drive_path):
            return {"success": False, "error": f"Drive path {drive_path} does not exist"}
        
        self.callback = callback
        self.scanning = True
        self.paused = False
        self.results = {
            "drive_path": drive_path,
            "scan_start_time": time.time(),
            "scan_end_time": None,
            "total_size": 0,
            "files_count": 0,
            "dirs_count": 0,
            "large_files": [],
            "large_dirs": [],
            "file_types": {},
            "age_categories": {},
            "errors": []
        }
        
        self.total_size = 0
        self.files_count = 0
        self.dirs_count = 0
        self.scan_start_time = time.time()
        self.large_files = []
        self.large_dirs = []
        self.file_types = {}
        self.age_categories = {}
        
        # Create empty queue
        self.queue = queue.Queue()
        
        # Start with the root path
        self.queue.put(drive_path)
        
        try:
            # Create and start worker threads
            threads = []
            for _ in range(self.max_threads):
                thread = threading.Thread(target=self._scan_worker, args=(min_file_size, max_files))
                thread.daemon = True
                thread.start()
                threads.append(thread)
            
            # Wait for all threads to finish
            for thread in threads:
                thread.join()
            
            # Update final results
            scan_end_time = time.time()
            self.results["scan_end_time"] = scan_end_time
            self.results["total_size"] = self.total_size
            self.results["files_count"] = self.files_count
            self.results["dirs_count"] = self.dirs_count
            self.results["scan_duration"] = scan_end_time - self.scan_start_time
            self.results["large_files"] = sorted(self.large_files, key=lambda x: x["size"], reverse=True)[:max_files]
            self.results["large_dirs"] = sorted(self.large_dirs, key=lambda x: x["size"], reverse=True)[:100]
            self.results["file_types"] = self._sort_dict_by_value(self.file_types, reverse=True)
            self.results["age_categories"] = self.age_categories
            self.results["formatted"] = {
                "total_size": self._format_size(self.total_size),
                "scan_duration": self._format_duration(scan_end_time - self.scan_start_time)
            }
            
            return {
                "success": True,
                "results": self.results
            }
        
        except Exception as e:
            self.scanning = False
            logging.error(f"Error analyzing drive {drive_path}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
        finally:
            self.scanning = False
    
    def _scan_worker(self, min_file_size: int, max_files: int):
        """Worker thread for scanning directories
        
        Args:
            min_file_size: Minimum file size to track individually
            max_files: Maximum number of large files to track
        """
        while self.scanning and not self.queue.empty():
            try:
                # Check if scanning is paused
                while self.paused and self.scanning:
                    time.sleep(0.1)
                
                # Check if scanning was stopped
                if not self.scanning:
                    break
                
                # Get next directory to scan
                current_dir = self.queue.get(timeout=1)
                
                # Skip excluded directories
                if self._should_exclude(current_dir):
                    self.queue.task_done()
                    continue
                
                try:
                    # Process the directory
                    self.dirs_count += 1
                    dir_size = 0
                    
                    # Get directory contents
                    for entry in os.scandir(current_dir):
                        # Check if scanning was stopped
                        if not self.scanning:
                            break
                        
                        try:
                            if entry.is_dir(follow_symlinks=False):
                                # Add directory to queue for processing
                                if not self._should_exclude(entry.path):
                                    self.queue.put(entry.path)
                            
                            elif entry.is_file(follow_symlinks=False):
                                # Get file information
                                try:
                                    file_stat = entry.stat(follow_symlinks=False)
                                    file_size = file_stat.st_size
                                    file_mtime = file_stat.st_mtime
                                    
                                    # Update counters
                                    self.files_count += 1
                                    self.total_size += file_size
                                    dir_size += file_size
                                    
                                    # Process file extension statistics
                                    self._update_file_type_stats(entry.path, file_size)
                                    
                                    # Process file age statistics
                                    self._update_age_stats(file_mtime, file_size)
                                    
                                    # Track large files
                                    if file_size >= min_file_size:
                                        self._add_large_file(entry.path, file_size, file_mtime, max_files)
                                    
                                except Exception as e:
                                    self.results["errors"].append(f"Error processing file {entry.path}: {e}")
                        
                        except Exception as e:
                            self.results["errors"].append(f"Error processing entry {entry.name}: {e}")
                    
                    # Add directory to large directories list
                    if dir_size > min_file_size * 10:  # Use a higher threshold for directories
                        self._add_large_dir(current_dir, dir_size)
                    
                    # Update progress callback
                    if self.callback:
                        self.callback({
                            "current_dir": current_dir,
                            "total_size": self.total_size,
                            "files_count": self.files_count,
                            "dirs_count": self.dirs_count,
                            "progress": {
                                "queue_size": self.queue.qsize(),
                                "elapsed_time": time.time() - self.scan_start_time
                            }
                        })
                
                except PermissionError:
                    self.results["errors"].append(f"Permission denied: {current_dir}")
                except FileNotFoundError:
                    self.results["errors"].append(f"File not found: {current_dir}")
                except Exception as e:
                    self.results["errors"].append(f"Error scanning directory {current_dir}: {e}")
                
                # Mark task as done
                self.queue.task_done()
            
            except queue.Empty:
                # Queue is empty, exit
                break
            except Exception as e:
                logging.error(f"Error in scan worker: {e}")
    
    def _should_exclude(self, path: str) -> bool:
        """Check if a path should be excluded
        
        Args:
            path: Path to check
            
        Returns:
            True if path should be excluded, False otherwise
        """
        # Check against excluded dirs
        if path in self.excluded_dirs:
            return True
        
        # Check against excluded patterns
        path_parts = path.split(os.sep)
        return any(part in self.excluded_patterns for part in path_parts)
    
    def _update_file_type_stats(self, file_path: str, file_size: int):
        """Update file type statistics
        
        Args:
            file_path: Path to file
            file_size: File size in bytes
        """
        # Extract file extension
        _, ext = os.path.splitext(file_path)
        ext = ext.lower()
        
        if not ext:
            ext = "[no extension]"
        
        # Update file type statistics
        if ext in self.file_types:
            self.file_types[ext]["count"] += 1
            self.file_types[ext]["size"] += file_size
        else:
            self.file_types[ext] = {
                "count": 1,
                "size": file_size
            }
    
    def _update_age_stats(self, file_mtime: float, file_size: int):
        """Update file age statistics
        
        Args:
            file_mtime: File modification time
            file_size: File size in bytes
        """
        # Calculate file age in days
        current_time = time.time()
        age_days = (current_time - file_mtime) / (60 * 60 * 24)
        
        # Categorize age
        if age_days < 7:
            category = "recent"
        elif age_days < 30:
            category = "month"
        elif age_days < 90:
            category = "quarter"
        elif age_days < 365:
            category = "year"
        else:
            category = "old"
        
        # Update age statistics
        if category in self.age_categories:
            self.age_categories[category]["count"] += 1
            self.age_categories[category]["size"] += file_size
        else:
            self.age_categories[category] = {
                "count": 1,
                "size": file_size
            }
    
    def _add_large_file(self, file_path: str, file_size: int, file_mtime: float, max_files: int):
        """Add a file to the large files list
        
        Args:
            file_path: Path to file
            file_size: File size in bytes
            file_mtime: File modification time
            max_files: Maximum number of files to track
        """
        # Create file info dictionary
        file_info = {
            "path": file_path,
            "name": os.path.basename(file_path),
            "directory": os.path.dirname(file_path),
            "size": file_size,
            "size_formatted": self._format_size(file_size),
            "modified": file_mtime,
            "modified_date": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(file_mtime)),
            "age_days": int((time.time() - file_mtime) / (60 * 60 * 24)),
            "extension": os.path.splitext(file_path)[1].lower()
        }
        
        # Add to large files list
        self.large_files.append(file_info)
        
        # Keep only the largest files
        if len(self.large_files) > max_files * 2:
            self.large_files = sorted(self.large_files, key=lambda x: x["size"], reverse=True)[:max_files]
    
    def _add_large_dir(self, dir_path: str, dir_size: int):
        """Add a directory to the large directories list
        
        Args:
            dir_path: Path to directory
            dir_size: Directory size in bytes
        """
        # Create directory info dictionary
        dir_info = {
            "path": dir_path,
            "name": os.path.basename(dir_path),
            "parent": os.path.dirname(dir_path),
            "size": dir_size,
            "size_formatted": self._format_size(dir_size)
        }
        
        # Add to large directories list
        self.large_dirs.append(dir_info)
    
    def pause_scan(self):
        """Pause the current scan"""
        self.paused = True
    
    def resume_scan(self):
        """Resume the current scan"""
        self.paused = False
    
    def stop_scan(self):
        """Stop the current scan"""
        self.scanning = False
    
    def get_scan_progress(self) -> Dict[str, Any]:
        """Get current scan progress
        
        Returns:
            Dictionary with scan progress information
        """
        if not self.scanning:
            return {
                "scanning": False,
                "paused": False
            }
        
        # Calculate progress indicators
        elapsed_time = time.time() - self.scan_start_time
        
        return {
            "scanning": self.scanning,
            "paused": self.paused,
            "elapsed_time": elapsed_time,
            "elapsed_formatted": self._format_duration(elapsed_time),
            "queue_size": self.queue.qsize(),
            "files_count": self.files_count,
            "dirs_count": self.dirs_count,
            "total_size": self.total_size,
            "total_size_formatted": self._format_size(self.total_size)
        }
    
    def get_file_type_summary(self) -> Dict[str, Any]:
        """Get summary of file types
        
        Returns:
            Dictionary with file type summary
        """
        results = {}
        
        # Sort file types by size
        sorted_types = self._sort_dict_by_value(self.file_types, reverse=True)
        
        # Calculate total size and count
        total_size = sum(item["size"] for item in sorted_types.values())
        total_count = sum(item["count"] for item in sorted_types.values())
        
        # Calculate percentages and add formatted sizes
        for ext, info in sorted_types.items():
            size_percent = (info["size"] / total_size * 100) if total_size > 0 else 0
            count_percent = (info["count"] / total_count * 100) if total_count > 0 else 0
            
            results[ext] = {
                "count": info["count"],
                "size": info["size"],
                "size_formatted": self._format_size(info["size"]),
                "size_percent": size_percent,
                "count_percent": count_percent
            }
        
        return {
            "file_types": results,
            "total_size": total_size,
            "total_size_formatted": self._format_size(total_size),
            "total_count": total_count
        }
    
    def _sort_dict_by_value(self, d: Dict, key: str = "size", reverse: bool = False) -> Dict:
        """Sort a dictionary by a value in the value dict
        
        Args:
            d: Dictionary to sort
            key: Key in the value dictionary to sort by
            reverse: Whether to sort in descending order
            
        Returns:
            Sorted dictionary
        """
        if not d:
            return {}
        
        # Check if values are dictionaries with the specified key
        if isinstance(next(iter(d.values())), dict) and key in next(iter(d.values())):
            # Sort by the specified key in the value dictionary
            return {k: d[k] for k in sorted(d.keys(), key=lambda x: d[x][key], reverse=reverse)}
        else:
            # Sort by the values directly
            return {k: d[k] for k in sorted(d.keys(), key=lambda x: d[x], reverse=reverse)}
    
    def _format_size(self, size_bytes: int) -> str:
        """Format file size in a human-readable format
        
        Args:
            size_bytes: Size in bytes
            
        Returns:
            Formatted size string
        """
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"
    
    def _format_duration(self, seconds: float) -> str:
        """Format duration in a human-readable format
        
        Args:
            seconds: Duration in seconds
            
        Returns:
            Formatted duration string
        """
        if seconds < 60:
            return f"{seconds:.1f} seconds"
        elif seconds < 3600:
            minutes = seconds / 60
            return f"{minutes:.1f} minutes"
        else:
            hours = seconds / 3600
            return f"{hours:.1f} hours"


# Singleton instance
disk_analyzer = DiskAnalyzer()

if __name__ == "__main__":
    # Test functionality
    logging.basicConfig(level=logging.INFO)
    
    print("Getting available drives...")
    drives = disk_analyzer.get_available_drives()
    
    print(f"Found {len(drives)} drives:")
    for drive in drives:
        print(f"- {drive['label']} ({drive['path']}): {drive['free_formatted']} free of {drive['total_formatted']} ({drive['percent_used']}% used)")
    
    # Uncomment to test drive analysis (USE WITH CAUTION as it can take a long time for large drives)
    # if drives:
    #     print(f"\nAnalyzing drive {drives[0]['path']}...")
    #     
    #     def progress_callback(progress):
    #         print(f"Scanning {progress['current_dir']}, found {progress['files_count']} files ({progress['total_size_formatted']})")
    #     
    #     result = disk_analyzer.analyze_drive(drives[0]['path'], callback=progress_callback)
    #     
    #     if result["success"]:
    #         print(f"\nScan complete:")
    #         print(f"- Total size: {result['results']['formatted']['total_size']}")
    #         print(f"- Files: {result['results']['files_count']}")
    #         print(f"- Directories: {result['results']['dirs_count']}")
    #         print(f"- Duration: {result['results']['formatted']['scan_duration']}")
    #         
    #         if result['results']['large_files']:
    #             print("\nLargest files:")
    #             for file in result['results']['large_files'][:5]:
    #                 print(f"- {file['name']} ({file['size_formatted']})")
    #     else:
    #         print(f"Error: {result['error']}") 