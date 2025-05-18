#!/usr/bin/env python3
"""
System Tray Integration for Ultra Temp Cleaner Pro
-------------------------------------------------
Allows the application to run in the background with system tray icon
"""

import os
import sys
import logging
import threading
import time
import platform
from typing import Optional, Dict, Any, Callable
import tempfile
import json

# Import GUI libraries based on platform
if platform.system() == "Windows":
    import pystray
    from PIL import Image, ImageDraw
    import win32api
    import win32con
    import win32gui
elif platform.system() == "Darwin":  # macOS
    import pystray
    from PIL import Image, ImageDraw
    import rumps
else:  # Linux and others
    import pystray
    from PIL import Image, ImageDraw
    import gi
    gi.require_version('Notify', '0.7')
    from gi.repository import Notify

# Import app modules
from main import TempFileFinder
from secure_delete import SecureDelete
from schedule import ScheduledCleaner
import languages

# Translation function
_ = languages.language_manager.get_text

class SystemTrayIcon:
    """System tray icon for Ultra Temp Cleaner Pro"""
    
    def __init__(self, app_instance=None):
        """Initialize the system tray icon
        
        Args:
            app_instance: The main application instance (if available)
        """
        self.app = app_instance
        self.icon = None
        self.scheduler = None
        self.finder = TempFileFinder()
        self.secure_delete = SecureDelete()
        
        # Status tracking
        self.is_running = False
        self.last_scan_time = None
        self.last_scan_results = None
        self.settings = self._load_settings()
        
        # Initialize notification system
        self._init_notifications()
        
        # Start scheduler if enabled
        if self.settings.get('auto_schedule_enabled', False):
            self._start_scheduler()
        
        # Create and start the icon
        self._create_icon()
    
    def _create_icon(self):
        """Create the system tray icon"""
        # Create icon image
        icon_image = self._create_icon_image()
        
        # Define menu
        menu_items = [
            pystray.MenuItem(_('scan_now'), self._on_scan),
            pystray.MenuItem(_('view_results'), self._on_view_results),
            pystray.MenuItem(_('find_duplicates'), self._on_find_duplicates),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(_('settings'), self._on_settings),
            pystray.MenuItem(_('auto_clean'), self._on_toggle_auto_clean, checked=lambda item: self.settings.get('auto_schedule_enabled', False)),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(_('open_app'), self._on_open_app),
            pystray.MenuItem(_('exit'), self._on_exit)
        ]
        
        # Create icon
        self.icon = pystray.Icon("UltraTempCleanerPro", icon_image, _('app_name'), menu=pystray.Menu(*menu_items))
    
    def _create_icon_image(self) -> Image.Image:
        """Create an icon image
        
        Returns:
            PIL Image object for the icon
        """
        # Try to load icon from file
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets', 'icon.png')
        if os.path.exists(icon_path):
            return Image.open(icon_path)
        
        # Create a default icon
        image = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
        dc = ImageDraw.Draw(image)
        
        # Draw a simple trash can icon
        dc.rectangle((16, 16, 48, 52), fill=(30, 144, 255, 255))  # Blue background
        dc.rectangle((18, 12, 46, 16), fill=(30, 144, 255, 255))  # Trash lid
        
        # Draw lines to make it look like a trash can
        for x in range(22, 46, 6):
            dc.line([(x, 22), (x, 46)], fill=(255, 255, 255, 200), width=2)
        
        return image
    
    def run(self):
        """Run the system tray icon"""
        self.is_running = True
        self.icon.run()
    
    def stop(self):
        """Stop the system tray icon"""
        self.is_running = False
        if self.icon:
            self.icon.stop()
    
    def _init_notifications(self):
        """Initialize the notification system based on the current platform"""
        if platform.system() == "Linux":
            Notify.init("UltraTempCleanerPro")
    
    def _show_notification(self, title: str, message: str, timeout: int = 5):
        """Show a notification
        
        Args:
            title: Notification title
            message: Notification message
            timeout: Notification timeout in seconds
        """
        if platform.system() == "Windows":
            # Windows native notification
            self.icon.notify(message, title)
        elif platform.system() == "Darwin":
            # macOS notification
            if 'rumps' in globals():
                rumps.notification(title, "", message, sound=True)
        else:
            # Linux notification
            notification = Notify.Notification.new(title, message, "dialog-information")
            notification.set_timeout(timeout * 1000)  # Milliseconds
            notification.show()
    
    def _on_scan(self, icon, item):
        """Handle scan button click"""
        threading.Thread(target=self._perform_scan, daemon=True).start()
    
    def _perform_scan(self):
        """Perform a scan in the background"""
        try:
            # Show notification
            self._show_notification(_('scanning'), _('scanning_temp_files'))
            
            # Scan temp directories
            self.finder.scanning = True
            self.finder.set_min_file_age(self.settings.get('min_age', 7))
            
            temp_dirs = self.finder.get_system_temp_dirs()
            files = []
            
            for temp_dir in temp_dirs:
                if self.finder.scanning:
                    dir_files = self.finder.scan_for_temp_files(temp_dir)
                    files.extend(dir_files)
            
            # Store results
            self.last_scan_time = time.time()
            self.last_scan_results = {
                'files': files,
                'total': len(files),
                'size': self.finder.total_size,
                'size_formatted': self.finder.format_size(self.finder.total_size)
            }
            
            # Show notification with results
            self._show_notification(
                _('scan_complete'),
                _('found_files').format(
                    count=len(files),
                    size=self.finder.format_size(self.finder.total_size)
                )
            )
            
            # Auto-clean if enabled
            if self.settings.get('auto_clean', False):
                self._perform_auto_clean()
        
        except Exception as e:
            logging.error(f"Error during background scan: {e}")
            self._show_notification(_('error'), f"{_('scan_failed')}: {str(e)}")
        finally:
            self.finder.scanning = False
    
    def _perform_auto_clean(self):
        """Perform automatic cleaning based on settings"""
        if not self.last_scan_results or not self.last_scan_results.get('files'):
            return
        
        try:
            # Filter files by age
            min_age = self.settings.get('auto_clean_min_age', 30)
            files_to_delete = [
                f for f in self.last_scan_results['files']
                if f['age_days'] >= min_age and not f.get('is_protected', False)
            ]
            
            if not files_to_delete:
                return
            
            # Show notification
            self._show_notification(
                _('auto_cleaning'),
                _('deleting_files').format(count=len(files_to_delete))
            )
            
            # Delete files
            deleted = 0
            deleted_size = 0
            
            for file_info in files_to_delete:
                if self.settings.get('secure_delete', False):
                    success = self.secure_delete.secure_delete_file(file_info['path'])
                else:
                    success = self.finder.delete_file(file_info['path'])
                
                if success:
                    deleted += 1
                    deleted_size += file_info['size']
            
            # Show notification with results
            self._show_notification(
                _('cleaning_complete'),
                _('deleted_files').format(
                    count=deleted,
                    size=self.finder.format_size(deleted_size)
                )
            )
        
        except Exception as e:
            logging.error(f"Error during auto-clean: {e}")
            self._show_notification(_('error'), f"{_('clean_failed')}: {str(e)}")
    
    def _on_view_results(self, icon, item):
        """Show the last scan results"""
        if not self.last_scan_results:
            self._show_notification(_('no_results'), _('no_scan_results'))
            return
        
        # Open the main app with results if available
        if self.app:
            self.app.show_results(self.last_scan_results['files'])
        else:
            self._on_open_app(icon, item)
    
    def _on_find_duplicates(self, icon, item):
        """Find duplicate files"""
        if not self.last_scan_results or not self.last_scan_results.get('files'):
            self._show_notification(_('no_results'), _('no_scan_results'))
            return
        
        threading.Thread(target=self._perform_duplicate_scan, daemon=True).start()
    
    def _perform_duplicate_scan(self):
        """Perform a duplicate file scan"""
        try:
            # Show notification
            self._show_notification(_('scanning'), _('scanning_for_duplicates'))
            
            # Find duplicates
            duplicates = self.finder.find_duplicate_files(self.last_scan_results['files'])
            
            # Show notification with results
            if duplicates['total_duplicates'] > 0:
                self._show_notification(
                    _('duplicates_found'),
                    _('duplicate_files_found').format(
                        count=duplicates['total_duplicates'],
                        size=duplicates['total_size_formatted']
                    )
                )
                
                # Open the main app with results if available
                if self.app:
                    self.app.show_duplicates(duplicates)
                else:
                    self._on_open_app(self.icon, None)
            else:
                self._show_notification(_('no_duplicates'), _('no_duplicate_files'))
        
        except Exception as e:
            logging.error(f"Error during duplicate scan: {e}")
            self._show_notification(_('error'), f"{_('duplicate_scan_failed')}: {str(e)}")
    
    def _on_settings(self, icon, item):
        """Open settings"""
        # Open the main app settings if available
        if self.app:
            self.app.show_settings()
        else:
            self._on_open_app(icon, item)
    
    def _on_toggle_auto_clean(self, icon, item):
        """Toggle auto clean setting"""
        self.settings['auto_schedule_enabled'] = not self.settings.get('auto_schedule_enabled', False)
        self._save_settings()
        
        if self.settings['auto_schedule_enabled']:
            self._start_scheduler()
            self._show_notification(_('auto_clean'), _('auto_clean_enabled'))
        else:
            self._stop_scheduler()
            self._show_notification(_('auto_clean'), _('auto_clean_disabled'))
    
    def _on_open_app(self, icon, item):
        """Open the main application"""
        if self.app:
            self.app.show()
        else:
            # Try to start the main app
            try:
                subprocess.Popen([sys.executable, 'ui.py'])
            except Exception as e:
                logging.error(f"Error opening main app: {e}")
                self._show_notification(_('error'), f"{_('open_app_failed')}: {str(e)}")
    
    def _on_exit(self, icon, item):
        """Exit the application"""
        self.stop()
        if self.app:
            self.app.exit()
    
    def _start_scheduler(self):
        """Start the scheduler"""
        if self.scheduler is not None:
            return
        
        try:
            self.scheduler = ScheduledCleaner()
            self.scheduler.start_scheduler()
            logging.info("Scheduler started from system tray")
        except Exception as e:
            logging.error(f"Error starting scheduler: {e}")
    
    def _stop_scheduler(self):
        """Stop the scheduler"""
        if self.scheduler is None:
            return
        
        try:
            self.scheduler.stop_scheduler()
            self.scheduler = None
            logging.info("Scheduler stopped from system tray")
        except Exception as e:
            logging.error(f"Error stopping scheduler: {e}")
    
    def _load_settings(self) -> Dict[str, Any]:
        """Load settings from file
        
        Returns:
            Dictionary of settings
        """
        settings_file = os.path.join(tempfile.gettempdir(), 'ultra_temp_cleaner_settings.json')
        
        try:
            if os.path.exists(settings_file):
                with open(settings_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logging.error(f"Error loading settings: {e}")
        
        # Default settings
        return {
            'min_age': 7,
            'auto_clean': False,
            'auto_clean_min_age': 30,
            'secure_delete': False,
            'auto_schedule_enabled': False
        }
    
    def _save_settings(self):
        """Save settings to file"""
        settings_file = os.path.join(tempfile.gettempdir(), 'ultra_temp_cleaner_settings.json')
        
        try:
            with open(settings_file, 'w') as f:
                json.dump(self.settings, f, indent=2)
        except Exception as e:
            logging.error(f"Error saving settings: {e}")


def get_system_tray(app_instance=None):
    """Get a system tray instance
    
    Args:
        app_instance: The main application instance (if available)
        
    Returns:
        SystemTrayIcon instance
    """
    return SystemTrayIcon(app_instance)


def run_in_system_tray():
    """Run the application in the system tray"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    try:
        tray = get_system_tray()
        tray.run()
    except Exception as e:
        logging.error(f"Error running in system tray: {e}")
        raise


if __name__ == "__main__":
    run_in_system_tray() 