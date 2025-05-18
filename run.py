#!/usr/bin/env python3
"""
Ultra Temp Cleaner Pro X - Main Entry Point
-------------------------------------------
Cross-platform launcher for the enhanced temporary file cleaner
"""

import os
import sys
import logging
import platform
import argparse
import time
import threading
from typing import Dict, Any, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ultra_temp_cleaner.log'),
        logging.StreamHandler()
    ]
)

def check_dependencies() -> Dict[str, bool]:
    """Check if all required dependencies are installed
    
    Returns:
        Dictionary mapping module names to availability boolean
    """
    dependencies = {
        # Core dependencies
        "tkinter": False,
        "matplotlib": False,
        "psutil": False,
        "pystray": False,
        
        # Optional dependencies
        "numpy": False,
        "sklearn": False,
        "pandas": False,
        "cryptography": False,
        "requests": False
    }
    
    # Check each dependency
    for module in dependencies.keys():
        try:
            __import__(module)
            dependencies[module] = True
        except ImportError:
            logging.warning(f"Module {module} not found. Some features may be disabled.")
    
    return dependencies

def is_admin() -> bool:
    """Check if the script is running with administrator privileges
    
    Returns:
        True if running as admin/root, False otherwise
    """
    try:
        if platform.system() == "Windows":
            import ctypes
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        else:
            return os.geteuid() == 0
    except:
        return False

def restart_as_admin():
    """Restart the application with administrator privileges"""
    if platform.system() == "Windows":
        import ctypes
        import sys
        
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, " ".join(sys.argv), None, 1
        )
        sys.exit(0)
    else:
        # For Unix-like systems
        if os.path.exists('/usr/bin/sudo'):
            os.system(f'sudo "{sys.executable}" {" ".join(sys.argv)}')
        else:
            os.system(f'pkexec "{sys.executable}" {" ".join(sys.argv)}')
        sys.exit(0)

def show_splash_screen():
    """Show a splash screen while the application is loading"""
    try:
        import tkinter as tk
        from PIL import Image, ImageTk
        
        splash = tk.Tk()
        splash.overrideredirect(True)
        splash.title("Ultra Temp Cleaner Pro X")
        
        # Calculate position (center of screen)
        screen_width = splash.winfo_screenwidth()
        screen_height = splash.winfo_screenheight()
        
        width = 600
        height = 400
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        
        splash.geometry(f"{width}x{height}+{x}+{y}")
        
        # Try to load splash image
        try:
            splash_image = Image.open("assets/splash.png")
            photo = ImageTk.PhotoImage(splash_image)
            splash_label = tk.Label(splash, image=photo)
            splash_label.image = photo
            splash_label.pack()
        except:
            # Fallback if image is not found
            splash.configure(bg="#1E1E2E")
            
            # Add title text
            title_label = tk.Label(
                splash, 
                text="Ultra Temp Cleaner Pro X",
                font=("Arial", 24, "bold"),
                fg="#FFFFFF",
                bg="#1E1E2E"
            )
            title_label.place(relx=0.5, rely=0.3, anchor="center")
            
            # Add loading text
            loading_label = tk.Label(
                splash, 
                text="Loading...",
                font=("Arial", 14),
                fg="#CCCCCC",
                bg="#1E1E2E"
            )
            loading_label.place(relx=0.5, rely=0.4, anchor="center")
            
            # Add progress bar
            progress_frame = tk.Frame(
                splash, 
                width=400,
                height=20,
                bg="#333344"
            )
            progress_frame.place(relx=0.5, rely=0.5, anchor="center")
            
            progress_bar = tk.Frame(
                progress_frame, 
                width=10,
                height=20,
                bg="#7B68EE"
            )
            progress_bar.place(x=0, y=0)
            
            # Animate progress bar
            def update_progress_bar():
                width = progress_bar.winfo_width() + 4
                if width >= 400:
                    width = 0
                progress_bar.config(width=width)
                splash.after(20, update_progress_bar)
            
            splash.after(100, update_progress_bar)
        
        # Return the splash window to be closed later
        return splash
    
    except Exception as e:
        logging.error(f"Error showing splash screen: {e}")
        return None

def start_application(args):
    """Start the application based on command line arguments
    
    Args:
        args: Command line arguments
    """
    # Show splash screen in background thread
    splash = None
    if not args.headless and not args.minimized:
        splash = show_splash_screen()
    
    try:
        # Import config module
        from config import config_manager
        
        # Apply command line overrides to config
        if args.debug:
            config_manager.set("advanced", "debug_mode", True)
            logging.getLogger().setLevel(logging.DEBUG)
            logging.debug("Debug mode enabled")
        
        if args.headless:
            # Start in headless mode (no UI)
            logging.info("Starting in headless mode")
            import headless_cleaner
            headless_cleaner.run_headless(args)
        
        elif args.system_tray_only:
            # Start only the system tray icon
            logging.info("Starting in system tray only mode")
            from system_tray import run_in_system_tray
            run_in_system_tray()
        
        else:
            # Start the full UI application
            logging.info("Starting UI application")
            import tkinter as tk
            from ui import TempFileCleanerUI
            
            # Close splash screen if it was shown
            if splash:
                splash.destroy()
            
            # Create root window
            root = tk.Tk()
            
            # Start UI
            app = TempFileCleanerUI(root)
            
            # Minimize to tray if specified
            if args.minimized:
                if hasattr(app, 'hide') and callable(app.hide):
                    root.withdraw()
                    app.hide()
            
            # Start the main loop
            root.mainloop()
    
    except ImportError as e:
        if splash:
            splash.destroy()
        
        # Show error message
        logging.error(f"Missing dependency: {e}")
        show_error_message(f"Missing dependency: {e}\n\nPlease install the required dependencies using pip install -r requirements.txt")
        sys.exit(1)
    
    except Exception as e:
        if splash:
            splash.destroy()
        
        # Show error message
        logging.error(f"Error starting application: {e}")
        show_error_message(f"Error starting application: {e}")
        sys.exit(1)

def show_error_message(message: str):
    """Show error message in a platform-appropriate way
    
    Args:
        message: Error message to display
    """
    try:
        import tkinter as tk
        from tkinter import messagebox
        
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("Ultra Temp Cleaner Pro X - Error", message)
        root.destroy()
    
    except:
        # Fallback to console error
        print(f"ERROR: {message}")

def parse_arguments():
    """Parse command line arguments
    
    Returns:
        Parsed arguments
    """
    parser = argparse.ArgumentParser(description="Ultra Temp Cleaner Pro X - Advanced system cleaning utility")
    
    # Mode selection arguments
    mode_group = parser.add_argument_group("Mode Selection")
    mode_group.add_argument("--headless", action="store_true", help="Run in headless mode (no UI)")
    mode_group.add_argument("--system-tray-only", action="store_true", help="Start only the system tray icon")
    mode_group.add_argument("--minimized", action="store_true", help="Start minimized to system tray")
    
    # Action arguments
    action_group = parser.add_argument_group("Actions")
    action_group.add_argument("--clean", action="store_true", help="Clean temp files automatically")
    action_group.add_argument("--scan-only", action="store_true", help="Scan without cleaning")
    action_group.add_argument("--scan-dir", type=str, help="Scan a specific directory")
    action_group.add_argument("--analyze-drive", type=str, help="Analyze disk space for a specific drive")
    action_group.add_argument("--optimize-memory", action="store_true", help="Optimize system memory")
    
    # Configuration arguments
    config_group = parser.add_argument_group("Configuration")
    config_group.add_argument("--min-age", type=int, help="Minimum file age in days")
    config_group.add_argument("--threads", type=int, help="Number of concurrent threads for scanning")
    config_group.add_argument("--exclude-dir", type=str, action="append", help="Directory to exclude from scanning")
    
    # Misc arguments
    misc_group = parser.add_argument_group("Miscellaneous")
    misc_group.add_argument("--admin", action="store_true", help="Run with administrator privileges")
    misc_group.add_argument("--debug", action="store_true", help="Enable debug logging")
    misc_group.add_argument("--version", action="store_true", help="Show version information")
    
    return parser.parse_args()

def main():
    """Main entry point"""
    # Parse command line arguments
    args = parse_arguments()
    
    # Show version information if requested
    if args.version:
        version = "2.0.0"
        print(f"Ultra Temp Cleaner Pro X version {version}")
        print(f"Python version: {platform.python_version()}")
        print(f"Platform: {platform.platform()}")
        sys.exit(0)
    
    # Check for administrator privileges
    if args.admin and not is_admin():
        print("Restarting with administrator privileges...")
        restart_as_admin()
    
    # Check dependencies
    dependencies = check_dependencies()
    
    # Log dependency status
    missing_deps = [dep for dep, available in dependencies.items() if not available]
    if missing_deps:
        logging.warning(f"Missing optional dependencies: {', '.join(missing_deps)}")
    
    # Start the application
    start_application(args)

if __name__ == "__main__":
    main() 