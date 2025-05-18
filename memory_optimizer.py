#!/usr/bin/env python3
"""
Memory Optimization Module for Ultra Temp Cleaner Pro
----------------------------------------------------
Analyzes and optimizes system memory usage
"""

import os
import sys
import time
import logging
import platform
import threading
import json
from typing import Dict, List, Any, Callable, Optional, Tuple
from datetime import datetime

# Try to import platform-specific modules
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    logging.warning("psutil not available. Memory optimization functions will be limited.")

# Windows-specific modules
if platform.system() == "Windows":
    try:
        import ctypes
        import win32com.client
        import win32api
        import win32process
        import win32con
        import pywintypes
        WINDOWS_MODULES_AVAILABLE = True
    except ImportError:
        WINDOWS_MODULES_AVAILABLE = False
        logging.warning("Windows-specific modules not available. Some features will be disabled.")

# Import local modules
from config import config_manager, is_admin


class MemoryOptimizer:
    """Memory optimization and monitoring for system performance"""
    
    def __init__(self):
        """Initialize memory optimizer"""
        self.monitoring = False
        self.monitoring_thread = None
        self.monitoring_interval = 1.0  # seconds
        self.monitoring_callback = None
        self.history = []
        self.history_max_entries = 60  # 1 minute of history at 1 second interval
        self.optimization_results = None
        
        # Check if required modules are available
        self.available = PSUTIL_AVAILABLE
    
    def is_available(self) -> bool:
        """Check if memory optimization is available
        
        Returns:
            True if memory optimization is available, False otherwise
        """
        return self.available
    
    def get_memory_info(self) -> Dict[str, Any]:
        """Get current memory information
        
        Returns:
            Dictionary with memory information
        """
        if not self.available:
            return {"error": "Memory optimization not available"}
        
        try:
            mem = psutil.virtual_memory()
            swap = psutil.swap_memory()
            
            # Get memory information
            memory_info = {
                "total": mem.total,
                "available": mem.available,
                "used": mem.used,
                "free": mem.free,
                "percent": mem.percent,
                "total_formatted": self._format_size(mem.total),
                "available_formatted": self._format_size(mem.available),
                "used_formatted": self._format_size(mem.used),
                "free_formatted": self._format_size(mem.free),
                "swap_total": swap.total,
                "swap_used": swap.used,
                "swap_free": swap.free,
                "swap_percent": swap.percent,
                "swap_total_formatted": self._format_size(swap.total),
                "swap_used_formatted": self._format_size(swap.used),
                "swap_free_formatted": self._format_size(swap.free),
                "timestamp": time.time(),
                "formatted_time": datetime.now().strftime("%H:%M:%S")
            }
            
            # Add CPU information
            memory_info["cpu_percent"] = psutil.cpu_percent(interval=0.1)
            memory_info["cpu_count"] = psutil.cpu_count()
            memory_info["cpu_count_logical"] = psutil.cpu_count(logical=True)
            
            return memory_info
        
        except Exception as e:
            logging.error(f"Error getting memory information: {e}")
            return {"error": str(e)}
    
    def get_process_memory_usage(self, include_system: bool = False) -> List[Dict[str, Any]]:
        """Get memory usage by process
        
        Args:
            include_system: Whether to include system processes
            
        Returns:
            List of process memory usage dictionaries
        """
        if not self.available:
            return [{"error": "Memory optimization not available"}]
        
        processes = []
        
        try:
            # Get process information
            for proc in psutil.process_iter(['pid', 'name', 'username', 'memory_info', 'cpu_percent']):
                try:
                    # Get process information
                    process_info = proc.info
                    mem_info = process_info['memory_info']
                    
                    # Skip system processes if requested
                    if not include_system:
                        username = process_info['username']
                        if username and username.lower().startswith('system'):
                            continue
                    
                    # Get memory usage
                    memory_usage = mem_info.rss if mem_info else 0
                    
                    # Add process to list
                    processes.append({
                        "pid": process_info['pid'],
                        "name": process_info['name'],
                        "username": process_info['username'],
                        "memory_usage": memory_usage,
                        "memory_usage_formatted": self._format_size(memory_usage),
                        "cpu_percent": process_info['cpu_percent']
                    })
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pass
            
            # Sort processes by memory usage (descending)
            processes.sort(key=lambda x: x['memory_usage'], reverse=True)
            
            return processes
        
        except Exception as e:
            logging.error(f"Error getting process memory usage: {e}")
            return [{"error": str(e)}]
    
    def start_monitoring(self, callback: Optional[Callable] = None, interval: float = 1.0):
        """Start monitoring memory usage
        
        Args:
            callback: Optional callback function for monitoring updates
            interval: Monitoring interval in seconds
        """
        if not self.available:
            raise RuntimeError("Memory optimization not available")
        
        if self.monitoring:
            return
        
        self.monitoring = True
        self.monitoring_interval = interval
        self.monitoring_callback = callback
        self.history = []
        
        # Start monitoring thread
        self.monitoring_thread = threading.Thread(target=self._monitoring_worker, daemon=True)
        self.monitoring_thread.start()
    
    def stop_monitoring(self):
        """Stop monitoring memory usage"""
        self.monitoring = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=2.0)
            self.monitoring_thread = None
    
    def _monitoring_worker(self):
        """Worker thread for monitoring memory usage"""
        while self.monitoring:
            try:
                # Get current memory information
                memory_info = self.get_memory_info()
                
                # Add to history
                self.history.append(memory_info)
                
                # Limit history size
                if len(self.history) > self.history_max_entries:
                    self.history.pop(0)
                
                # Call callback if provided
                if self.monitoring_callback:
                    self.monitoring_callback(memory_info)
                
                # Sleep for the specified interval
                time.sleep(self.monitoring_interval)
            
            except Exception as e:
                logging.error(f"Error in memory monitoring: {e}")
                time.sleep(self.monitoring_interval)
    
    def get_monitoring_history(self) -> Dict[str, Any]:
        """Get memory monitoring history
        
        Returns:
            Dictionary with monitoring history
        """
        if not self.available:
            return {"error": "Memory optimization not available"}
        
        # Calculate averages
        if not self.history:
            return {"history": [], "averages": {}}
        
        # Extract relevant data for charts
        memory_data = []
        cpu_data = []
        timestamps = []
        
        for entry in self.history:
            memory_data.append(entry["percent"])
            cpu_data.append(entry["cpu_percent"])
            timestamps.append(entry["formatted_time"])
        
        # Calculate averages
        averages = {
            "memory_percent": sum(memory_data) / len(memory_data) if memory_data else 0,
            "cpu_percent": sum(cpu_data) / len(cpu_data) if cpu_data else 0
        }
        
        # Get current and oldest memory info for comparison
        current = self.history[-1] if self.history else {}
        oldest = self.history[0] if self.history else {}
        
        return {
            "history": self.history,
            "chart_data": {
                "memory_data": memory_data,
                "cpu_data": cpu_data,
                "timestamps": timestamps
            },
            "averages": averages,
            "current": current,
            "oldest": oldest
        }
    
    def optimize_memory(self, target_processes: List[str] = None) -> Dict[str, Any]:
        """Optimize system memory
        
        Args:
            target_processes: Optional list of process names to target
            
        Returns:
            Dictionary with optimization results
        """
        if not self.available:
            return {"success": False, "error": "Memory optimization not available"}
        
        try:
            # Get initial memory information
            initial_memory = self.get_memory_info()
            
            # Perform different optimization techniques based on platform
            system = platform.system()
            
            optimizations = []
            
            # 1. Clear system file cache
            cache_result = self._clear_system_cache()
            optimizations.append(cache_result)
            
            # 2. Optimize specific processes
            process_result = self._optimize_processes(target_processes)
            optimizations.append(process_result)
            
            # 3. Perform garbage collection
            gc_result = self._run_garbage_collection()
            optimizations.append(gc_result)
            
            # 4. Platform-specific optimizations
            if system == "Windows":
                windows_result = self._optimize_windows_memory()
                optimizations.append(windows_result)
            elif system == "Linux":
                linux_result = self._optimize_linux_memory()
                optimizations.append(linux_result)
            elif system == "Darwin":  # macOS
                macos_result = self._optimize_macos_memory()
                optimizations.append(macos_result)
            
            # Get final memory information
            final_memory = self.get_memory_info()
            
            # Calculate improvements
            memory_freed = final_memory["available"] - initial_memory["available"]
            percent_improvement = (memory_freed / initial_memory["total"]) * 100
            
            # Store optimization results
            self.optimization_results = {
                "success": True,
                "initial_memory": initial_memory,
                "final_memory": final_memory,
                "memory_freed": memory_freed,
                "memory_freed_formatted": self._format_size(memory_freed),
                "percent_improvement": percent_improvement,
                "timestamp": time.time(),
                "formatted_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "optimizations": optimizations
            }
            
            return self.optimization_results
        
        except Exception as e:
            logging.error(f"Error optimizing memory: {e}")
            return {"success": False, "error": str(e)}
    
    def _clear_system_cache(self) -> Dict[str, Any]:
        """Clear system file cache
        
        Returns:
            Dictionary with optimization results
        """
        system = platform.system()
        success = False
        message = "Not implemented for this platform"
        
        try:
            if system == "Windows":
                if WINDOWS_MODULES_AVAILABLE and is_admin():
                    # Use Windows API to clear file cache
                    try:
                        # Clear file system cache
                        ctypes.windll.kernel32.SetSystemFileCacheSize(-1, -1, 0)
                        success = True
                        message = "Successfully cleared Windows file cache"
                    except Exception as e:
                        success = False
                        message = f"Failed to clear Windows file cache: {e}"
                else:
                    success = False
                    message = "Administrator privileges required to clear Windows file cache"
            
            elif system == "Linux":
                # On Linux, we can drop caches by writing to /proc/sys/vm/drop_caches
                if os.geteuid() == 0:  # Check if running as root
                    try:
                        os.system("sync")
                        with open("/proc/sys/vm/drop_caches", "w") as f:
                            f.write("3")
                        success = True
                        message = "Successfully cleared Linux file cache"
                    except Exception as e:
                        success = False
                        message = f"Failed to clear Linux file cache: {e}"
                else:
                    success = False
                    message = "Root privileges required to clear Linux file cache"
            
            elif system == "Darwin":  # macOS
                if os.geteuid() == 0:  # Check if running as root
                    try:
                        os.system("sync && purge")
                        success = True
                        message = "Successfully cleared macOS file cache"
                    except Exception as e:
                        success = False
                        message = f"Failed to clear macOS file cache: {e}"
                else:
                    success = False
                    message = "Root privileges required to clear macOS file cache"
            
            return {
                "type": "system_cache",
                "success": success,
                "message": message
            }
        
        except Exception as e:
            return {
                "type": "system_cache",
                "success": False,
                "message": f"Error clearing system cache: {e}"
            }
    
    def _optimize_processes(self, target_processes: List[str] = None) -> Dict[str, Any]:
        """Optimize memory usage of specific processes
        
        Args:
            target_processes: Optional list of process names to target
            
        Returns:
            Dictionary with optimization results
        """
        if not PSUTIL_AVAILABLE:
            return {
                "type": "process_optimization",
                "success": False,
                "message": "Process optimization not available (psutil required)"
            }
        
        try:
            optimized_processes = []
            total_memory_before = 0
            total_memory_after = 0
            
            # Get processes to optimize
            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'memory_info']):
                try:
                    # Skip if process doesn't match target processes
                    if target_processes and proc.info['name'] not in target_processes:
                        continue
                    
                    processes.append(proc)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            
            # Sort processes by memory usage (descending)
            processes.sort(key=lambda p: p.memory_info().rss if p.memory_info() else 0, reverse=True)
            
            # Take top processes by memory usage (limited to 10)
            top_processes = processes[:10]
            
            # Optimize each process
            system = platform.system()
            
            for proc in top_processes:
                try:
                    # Get memory before optimization
                    mem_before = proc.memory_info().rss if proc.memory_info() else 0
                    total_memory_before += mem_before
                    
                    if system == "Windows" and WINDOWS_MODULES_AVAILABLE:
                        # Windows process optimization
                        try:
                            # Try to reduce working set
                            handle = ctypes.windll.kernel32.OpenProcess(
                                win32con.PROCESS_ALL_ACCESS, False, proc.pid)
                            
                            if handle:
                                ctypes.windll.psapi.EmptyWorkingSet(handle)
                                ctypes.windll.kernel32.CloseHandle(handle)
                        except:
                            pass
                    else:
                        # Unix-based systems - call process optimization through psutil
                        # Unfortunately, there's no direct API for this, but the memory usage
                        # may decrease naturally after garbage collection
                        pass
                    
                    # Get memory after optimization
                    mem_after = proc.memory_info().rss if proc.memory_info() else 0
                    total_memory_after += mem_after
                    
                    # Calculate memory freed
                    memory_freed = mem_before - mem_after
                    
                    if memory_freed > 0:
                        optimized_processes.append({
                            "pid": proc.pid,
                            "name": proc.name(),
                            "memory_before": mem_before,
                            "memory_after": mem_after,
                            "memory_freed": memory_freed,
                            "memory_freed_formatted": self._format_size(memory_freed)
                        })
                
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            
            # Calculate total memory freed
            total_memory_freed = total_memory_before - total_memory_after
            
            return {
                "type": "process_optimization",
                "success": True,
                "message": f"Optimized {len(optimized_processes)} processes, freed {self._format_size(total_memory_freed)}",
                "optimized_processes": optimized_processes,
                "total_memory_freed": total_memory_freed,
                "total_memory_freed_formatted": self._format_size(total_memory_freed)
            }
        
        except Exception as e:
            return {
                "type": "process_optimization",
                "success": False,
                "message": f"Error optimizing processes: {e}"
            }
    
    def _run_garbage_collection(self) -> Dict[str, Any]:
        """Run Python garbage collection
        
        Returns:
            Dictionary with optimization results
        """
        try:
            import gc
            
            # Get memory before garbage collection
            memory_before = self.get_memory_info()["used"]
            
            # Run garbage collection
            collected = gc.collect()
            
            # Get memory after garbage collection
            memory_after = self.get_memory_info()["used"]
            
            # Calculate memory freed
            memory_freed = memory_before - memory_after
            
            return {
                "type": "garbage_collection",
                "success": True,
                "message": f"Garbage collection freed {self._format_size(memory_freed)} (collected {collected} objects)",
                "memory_freed": memory_freed,
                "memory_freed_formatted": self._format_size(memory_freed),
                "collected_objects": collected
            }
        
        except Exception as e:
            return {
                "type": "garbage_collection",
                "success": False,
                "message": f"Error running garbage collection: {e}"
            }
    
    def _optimize_windows_memory(self) -> Dict[str, Any]:
        """Optimize Windows memory
        
        Returns:
            Dictionary with optimization results
        """
        if not WINDOWS_MODULES_AVAILABLE:
            return {
                "type": "windows_optimization",
                "success": False,
                "message": "Windows optimization not available (missing modules)"
            }
        
        try:
            actions = []
            success = False
            
            # Check if running as administrator
            if is_admin():
                # 1. Clear system working set
                try:
                    ctypes.windll.psapi.EmptyWorkingSet(ctypes.c_int(-1))
                    actions.append("Cleared system working set")
                    success = True
                except Exception as e:
                    actions.append(f"Failed to clear system working set: {e}")
                
                # 2. Optimize Windows memory using native API
                try:
                    # Request trim of prefetch standby list
                    ntdll = ctypes.WinDLL('ntdll.dll')
                    
                    # Call NtSetSystemInformation function with MemoryListInformation
                    if hasattr(ntdll, "NtSetSystemInformation"):
                        # Define memory combine information structure
                        class MEMORY_COMBINE_INFORMATION_EX(ctypes.Structure):
                            _fields_ = [
                                ("CompressionRate", ctypes.c_size_t),
                                ("CompactionRate", ctypes.c_size_t),
                                ("Flags", ctypes.c_size_t)
                            ]
                        
                        # Call the function to compact memory
                        info = MEMORY_COMBINE_INFORMATION_EX(1, 1, 0)
                        buffer = ctypes.c_buffer(ctypes.sizeof(info))
                        ctypes.memmove(buffer, ctypes.addressof(info), ctypes.sizeof(info))
                        
                        # SystemMemoryListInformation = 80
                        status = ntdll.NtSetSystemInformation(80, buffer, ctypes.sizeof(info))
                        
                        if status == 0:  # STATUS_SUCCESS
                            actions.append("Optimized Windows memory using NtSetSystemInformation")
                            success = True
                        else:
                            actions.append(f"NtSetSystemInformation failed with status {status}")
                    
                except Exception as e:
                    actions.append(f"Error in memory compaction: {e}")
                
                # 3. Run custom Windows memory optimization
                try:
                    # Request full system garbage collection
                    if hasattr(ctypes.windll.kernel32, "SetProcessWorkingSetSize"):
                        process_handle = ctypes.windll.kernel32.GetCurrentProcess()
                        ctypes.windll.kernel32.SetProcessWorkingSetSize(process_handle, -1, -1)
                        actions.append("Optimized process working set")
                        success = True
                except Exception as e:
                    actions.append(f"Error optimizing process working set: {e}")
            else:
                actions.append("Administrator privileges required for Windows memory optimization")
            
            return {
                "type": "windows_optimization",
                "success": success,
                "message": "Windows memory optimization" + (" completed" if success else " failed"),
                "actions": actions
            }
        
        except Exception as e:
            return {
                "type": "windows_optimization",
                "success": False,
                "message": f"Error in Windows memory optimization: {e}"
            }
    
    def _optimize_linux_memory(self) -> Dict[str, Any]:
        """Optimize Linux memory
        
        Returns:
            Dictionary with optimization results
        """
        try:
            actions = []
            success = False
            
            # Check if running as root
            if os.geteuid() == 0:
                # 1. Clear page cache, dentries and inodes
                try:
                    os.system("sync")  # Sync disks with memory
                    with open("/proc/sys/vm/drop_caches", "w") as f:
                        f.write("3")
                    actions.append("Cleared page cache, dentries and inodes")
                    success = True
                except Exception as e:
                    actions.append(f"Failed to clear caches: {e}")
                
                # 2. Optimize swappiness
                try:
                    with open("/proc/sys/vm/swappiness", "w") as f:
                        f.write("10")  # Lower value to reduce swapping
                    actions.append("Set swappiness to 10")
                    success = True
                except Exception as e:
                    actions.append(f"Failed to set swappiness: {e}")
                
                # 3. Optimize virtual memory parameters
                try:
                    with open("/proc/sys/vm/vfs_cache_pressure", "w") as f:
                        f.write("50")  # Balanced cache pressure
                    actions.append("Set vfs_cache_pressure to 50")
                    success = True
                except Exception as e:
                    actions.append(f"Failed to set vfs_cache_pressure: {e}")
            else:
                actions.append("Root privileges required for Linux memory optimization")
            
            return {
                "type": "linux_optimization",
                "success": success,
                "message": "Linux memory optimization" + (" completed" if success else " failed"),
                "actions": actions
            }
        
        except Exception as e:
            return {
                "type": "linux_optimization",
                "success": False,
                "message": f"Error in Linux memory optimization: {e}"
            }
    
    def _optimize_macos_memory(self) -> Dict[str, Any]:
        """Optimize macOS memory
        
        Returns:
            Dictionary with optimization results
        """
        try:
            actions = []
            success = False
            
            # Check if running as root
            if os.geteuid() == 0:
                # 1. Purge memory
                try:
                    os.system("purge")
                    actions.append("Purged memory cache")
                    success = True
                except Exception as e:
                    actions.append(f"Failed to purge memory: {e}")
                
                # 2. Clear dns cache
                try:
                    os.system("killall -HUP mDNSResponder")
                    actions.append("Cleared DNS cache")
                    success = True
                except Exception as e:
                    actions.append(f"Failed to clear DNS cache: {e}")
            else:
                actions.append("Root privileges required for macOS memory optimization")
            
            return {
                "type": "macos_optimization",
                "success": success,
                "message": "macOS memory optimization" + (" completed" if success else " failed"),
                "actions": actions
            }
        
        except Exception as e:
            return {
                "type": "macos_optimization",
                "success": False,
                "message": f"Error in macOS memory optimization: {e}"
            }
    
    def terminate_process(self, pid: int) -> Dict[str, Any]:
        """Terminate a process by PID
        
        Args:
            pid: Process ID to terminate
            
        Returns:
            Dictionary with termination result
        """
        if not PSUTIL_AVAILABLE:
            return {"success": False, "error": "Process termination not available (psutil required)"}
        
        try:
            process = psutil.Process(pid)
            
            # Get process information before termination
            process_info = {
                "pid": process.pid,
                "name": process.name(),
                "memory_usage": process.memory_info().rss,
                "memory_usage_formatted": self._format_size(process.memory_info().rss)
            }
            
            # Terminate the process
            process.terminate()
            
            # Wait for process to terminate
            process.wait(timeout=3)
            
            return {
                "success": True,
                "message": f"Process {process_info['name']} (PID {process_info['pid']}) terminated",
                "process_info": process_info
            }
        
        except psutil.NoSuchProcess:
            return {"success": False, "error": f"Process with PID {pid} not found"}
        
        except psutil.AccessDenied:
            return {"success": False, "error": f"Access denied when terminating process with PID {pid}"}
        
        except Exception as e:
            logging.error(f"Error terminating process with PID {pid}: {e}")
            return {"success": False, "error": str(e)}
    
    def get_last_optimization_results(self) -> Optional[Dict[str, Any]]:
        """Get results of the last memory optimization
        
        Returns:
            Dictionary with optimization results or None if no optimization has been performed
        """
        return self.optimization_results
    
    def _format_size(self, size_bytes: int) -> str:
        """Format size in a human-readable format
        
        Args:
            size_bytes: Size in bytes
            
        Returns:
            Formatted size string
        """
        if size_bytes < 0:
            return "0 B"
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"


# Singleton instance
memory_optimizer = MemoryOptimizer()

if __name__ == "__main__":
    # Test functionality
    logging.basicConfig(level=logging.INFO)
    
    if not memory_optimizer.is_available():
        print("Memory optimization not available (psutil required)")
        sys.exit(1)
    
    print("Getting memory information...")
    memory_info = memory_optimizer.get_memory_info()
    
    print(f"Total memory: {memory_info['total_formatted']}")
    print(f"Available memory: {memory_info['available_formatted']}")
    print(f"Used memory: {memory_info['used_formatted']} ({memory_info['percent']}%)")
    
    print("\nTop memory processes:")
    processes = memory_optimizer.get_process_memory_usage()
    for i, process in enumerate(processes[:5]):
        print(f"{i+1}. {process['name']} (PID {process['pid']}): {process['memory_usage_formatted']}")
    
    # Test memory optimization (uncomment to run)
    # print("\nOptimizing memory...")
    # result = memory_optimizer.optimize_memory()
    # 
    # if result["success"]:
    #     print(f"Memory optimization complete:")
    #     print(f"Memory freed: {result['memory_freed_formatted']} ({result['percent_improvement']:.2f}%)")
    #     print("\nOptimizations performed:")
    #     for opt in result["optimizations"]:
    #         print(f"- {opt['type']}: {opt['message']}")
    # else:
    #     print(f"Error optimizing memory: {result['error']}") 