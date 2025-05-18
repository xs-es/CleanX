#!/usr/bin/env python3
"""
Browser Cache Cleaner Module for Ultra Temp Cleaner Pro
-------------------------------------------------------
Detects and cleans browser caches across multiple browsers
"""

import os
import shutil
import logging
import platform
import json
from typing import Dict, List, Tuple, Any, Optional
from pathlib import Path
import time

# Import local modules
from config import config_manager

class BrowserCleaner:
    """Browser cache cleaner for multiple browsers"""
    
    def __init__(self):
        """Initialize browser cleaner"""
        self.browser_paths = {}
        self.detected_browsers = {}
        self.detected_profiles = {}
        self.total_cache_size = 0
        self.browsers_detected = False
        
        # Load configuration
        self.skip_browser_data = not config_manager.get("cleaning", "clean_browser_data", True)
        
        # Initialize browser paths based on OS
        self._init_browser_paths()
    
    def _init_browser_paths(self):
        """Initialize browser paths based on operating system"""
        system = platform.system()
        appdata = os.environ.get('APPDATA', '')
        localappdata = os.environ.get('LOCALAPPDATA', '')
        home = os.path.expanduser('~')
        
        if system == "Windows":
            self.browser_paths = {
                "chrome": {
                    "name": "Google Chrome",
                    "path": os.path.join(localappdata, 'Google', 'Chrome', 'User Data'),
                    "profiles_path": "Default",
                    "cache_paths": [
                        "Cache", "Code Cache", "GPUCache", "Media Cache", "Service Worker", "Application Cache"
                    ],
                    "cookie_paths": ["Cookies", "Cookies-journal"],
                    "history_paths": ["History", "History-journal"],
                    "profile_config": "Preferences"
                },
                "edge": {
                    "name": "Microsoft Edge",
                    "path": os.path.join(localappdata, 'Microsoft', 'Edge', 'User Data'),
                    "profiles_path": "Default",
                    "cache_paths": [
                        "Cache", "Code Cache", "GPUCache", "Media Cache", "Service Worker", "Application Cache"
                    ],
                    "cookie_paths": ["Cookies", "Cookies-journal"],
                    "history_paths": ["History", "History-journal"],
                    "profile_config": "Preferences"
                },
                "firefox": {
                    "name": "Mozilla Firefox",
                    "path": os.path.join(appdata, 'Mozilla', 'Firefox', 'Profiles'),
                    "profiles_path": "",  # Will scan for *.default profiles
                    "cache_paths": ["cache2", "startupCache", "thumbnails", "shader-cache"],
                    "cookie_paths": ["cookies.sqlite", "cookies.sqlite-journal"],
                    "history_paths": ["places.sqlite", "places.sqlite-journal"],
                    "profile_config": "prefs.js"
                },
                "opera": {
                    "name": "Opera",
                    "path": os.path.join(appdata, 'Opera Software', 'Opera Stable'),
                    "profiles_path": "",
                    "cache_paths": ["Cache", "GPUCache", "Media Cache", "Service Worker"],
                    "cookie_paths": ["Cookies", "Cookies-journal"],
                    "history_paths": ["History", "History-journal"],
                    "profile_config": "Preferences"
                },
                "brave": {
                    "name": "Brave",
                    "path": os.path.join(localappdata, 'BraveSoftware', 'Brave-Browser', 'User Data'),
                    "profiles_path": "Default",
                    "cache_paths": [
                        "Cache", "Code Cache", "GPUCache", "Media Cache", "Service Worker", "Application Cache"
                    ],
                    "cookie_paths": ["Cookies", "Cookies-journal"],
                    "history_paths": ["History", "History-journal"],
                    "profile_config": "Preferences"
                },
                "vivaldi": {
                    "name": "Vivaldi",
                    "path": os.path.join(localappdata, 'Vivaldi', 'User Data'),
                    "profiles_path": "Default",
                    "cache_paths": [
                        "Cache", "Code Cache", "GPUCache", "Media Cache", "Service Worker", "Application Cache"
                    ],
                    "cookie_paths": ["Cookies", "Cookies-journal"],
                    "history_paths": ["History", "History-journal"],
                    "profile_config": "Preferences"
                }
            }
        elif system == "Darwin":  # macOS
            self.browser_paths = {
                "chrome": {
                    "name": "Google Chrome",
                    "path": os.path.join(home, 'Library', 'Application Support', 'Google', 'Chrome'),
                    "profiles_path": "Default",
                    "cache_paths": [
                        "Cache", "Code Cache", "GPUCache", "Media Cache", "Service Worker", "Application Cache"
                    ],
                    "cookie_paths": ["Cookies", "Cookies-journal"],
                    "history_paths": ["History", "History-journal"],
                    "profile_config": "Preferences"
                },
                "safari": {
                    "name": "Safari",
                    "path": os.path.join(home, 'Library', 'Safari'),
                    "profiles_path": "",
                    "cache_paths": ["Cache.db", "WebKitCache"],
                    "cookie_paths": ["Cookies.binarycookies"],
                    "history_paths": ["History.db", "WebpageIcons.db"],
                    "profile_config": "Preferences.plist"
                },
                "firefox": {
                    "name": "Mozilla Firefox",
                    "path": os.path.join(home, 'Library', 'Application Support', 'Firefox', 'Profiles'),
                    "profiles_path": "",  # Will scan for *.default profiles
                    "cache_paths": ["cache2", "startupCache", "thumbnails", "shader-cache"],
                    "cookie_paths": ["cookies.sqlite", "cookies.sqlite-journal"],
                    "history_paths": ["places.sqlite", "places.sqlite-journal"],
                    "profile_config": "prefs.js"
                },
                "edge": {
                    "name": "Microsoft Edge",
                    "path": os.path.join(home, 'Library', 'Application Support', 'Microsoft Edge'),
                    "profiles_path": "Default",
                    "cache_paths": [
                        "Cache", "Code Cache", "GPUCache", "Media Cache", "Service Worker", "Application Cache"
                    ],
                    "cookie_paths": ["Cookies", "Cookies-journal"],
                    "history_paths": ["History", "History-journal"],
                    "profile_config": "Preferences"
                }
            }
        else:  # Linux
            self.browser_paths = {
                "chrome": {
                    "name": "Google Chrome",
                    "path": os.path.join(home, '.config', 'google-chrome'),
                    "profiles_path": "Default",
                    "cache_paths": [
                        "Cache", "Code Cache", "GPUCache", "Media Cache", "Service Worker", "Application Cache"
                    ],
                    "cookie_paths": ["Cookies", "Cookies-journal"],
                    "history_paths": ["History", "History-journal"],
                    "profile_config": "Preferences"
                },
                "firefox": {
                    "name": "Mozilla Firefox",
                    "path": os.path.join(home, '.mozilla', 'firefox'),
                    "profiles_path": "",  # Will scan for *.default profiles
                    "cache_paths": ["cache2", "startupCache", "thumbnails", "shader-cache"],
                    "cookie_paths": ["cookies.sqlite", "cookies.sqlite-journal"],
                    "history_paths": ["places.sqlite", "places.sqlite-journal"],
                    "profile_config": "prefs.js"
                },
                "chromium": {
                    "name": "Chromium",
                    "path": os.path.join(home, '.config', 'chromium'),
                    "profiles_path": "Default",
                    "cache_paths": [
                        "Cache", "Code Cache", "GPUCache", "Media Cache", "Service Worker", "Application Cache"
                    ],
                    "cookie_paths": ["Cookies", "Cookies-journal"],
                    "history_paths": ["History", "History-journal"],
                    "profile_config": "Preferences"
                }
            }
    
    def detect_browsers(self) -> Dict[str, Any]:
        """Detect installed browsers and their profiles
        
        Returns:
            Dictionary with detected browsers information
        """
        self.detected_browsers = {}
        self.detected_profiles = {}
        self.total_cache_size = 0
        
        for browser_id, browser_info in self.browser_paths.items():
            try:
                browser_path = browser_info["path"]
                if os.path.exists(browser_path):
                    # Browser found, detect profiles
                    profiles_data = self._detect_profiles(browser_id, browser_info)
                    
                    if profiles_data:
                        self.detected_browsers[browser_id] = {
                            "name": browser_info["name"],
                            "path": browser_path,
                            "profiles": profiles_data["profiles"],
                            "total_size": profiles_data["total_size"],
                            "total_size_formatted": self._format_size(profiles_data["total_size"])
                        }
                        self.total_cache_size += profiles_data["total_size"]
                        
                        # Store detailed profile information
                        self.detected_profiles[browser_id] = profiles_data["detailed_profiles"]
            except Exception as e:
                logging.error(f"Error detecting browser {browser_id}: {e}")
        
        self.browsers_detected = True
        
        # Return summary of detected browsers
        return {
            "browsers": self.detected_browsers,
            "total_size": self.total_cache_size,
            "total_size_formatted": self._format_size(self.total_cache_size),
            "browser_count": len(self.detected_browsers)
        }
    
    def _detect_profiles(self, browser_id: str, browser_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Detect browser profiles and calculate cache sizes
        
        Args:
            browser_id: Browser identifier
            browser_info: Browser information dictionary
            
        Returns:
            Dictionary with profile information or None if no profiles found
        """
        profiles = []
        total_size = 0
        detailed_profiles = {}
        
        try:
            browser_path = browser_info["path"]
            profiles_path = browser_info["profiles_path"]
            
            # Handle Firefox-style profiles (multiple directories with random names)
            if browser_id == "firefox":
                # Look for .default or .default-release profiles
                for item in os.listdir(browser_path):
                    if item.endswith('.default') or item.endswith('default-release'):
                        profile_path = os.path.join(browser_path, item)
                        if os.path.isdir(profile_path):
                            profile_size, cache_items = self._calculate_profile_size(browser_id, profile_path, browser_info)
                            if profile_size > 0:
                                profile_name = item.split('.')[0]
                                profiles.append({
                                    "name": profile_name,
                                    "path": profile_path,
                                    "size": profile_size,
                                    "size_formatted": self._format_size(profile_size)
                                })
                                total_size += profile_size
                                detailed_profiles[item] = {
                                    "path": profile_path,
                                    "items": cache_items
                                }
            
            # Handle Chrome-style profiles (Default + Profile N directories)
            else:
                # Check default profile
                if profiles_path:
                    default_profile_path = os.path.join(browser_path, profiles_path)
                    if os.path.isdir(default_profile_path):
                        profile_size, cache_items = self._calculate_profile_size(browser_id, default_profile_path, browser_info)
                        if profile_size > 0:
                            profiles.append({
                                "name": "Default",
                                "path": default_profile_path,
                                "size": profile_size,
                                "size_formatted": self._format_size(profile_size)
                            })
                            total_size += profile_size
                            detailed_profiles["Default"] = {
                                "path": default_profile_path,
                                "items": cache_items
                            }
                
                # Look for additional profiles (Profile 1, Profile 2, etc.)
                for item in os.listdir(browser_path):
                    if item.startswith('Profile '):
                        profile_path = os.path.join(browser_path, item)
                        if os.path.isdir(profile_path):
                            profile_size, cache_items = self._calculate_profile_size(browser_id, profile_path, browser_info)
                            if profile_size > 0:
                                profiles.append({
                                    "name": item,
                                    "path": profile_path,
                                    "size": profile_size,
                                    "size_formatted": self._format_size(profile_size)
                                })
                                total_size += profile_size
                                detailed_profiles[item] = {
                                    "path": profile_path,
                                    "items": cache_items
                                }
        except Exception as e:
            logging.error(f"Error detecting profiles for {browser_id}: {e}")
            return None
        
        if not profiles:
            return None
            
        return {
            "profiles": profiles,
            "total_size": total_size,
            "detailed_profiles": detailed_profiles
        }
    
    def _calculate_profile_size(self, browser_id: str, profile_path: str, browser_info: Dict[str, Any]) -> Tuple[int, List[Dict[str, Any]]]:
        """Calculate profile cache size
        
        Args:
            browser_id: Browser identifier
            profile_path: Path to profile directory
            browser_info: Browser information dictionary
            
        Returns:
            Tuple of (total_size, cache_items_list)
        """
        total_size = 0
        cache_items = []
        
        # Check cache directories
        for cache_path in browser_info["cache_paths"]:
            full_path = os.path.join(profile_path, cache_path)
            if os.path.exists(full_path):
                try:
                    dir_size = self._get_dir_size(full_path)
                    if dir_size > 0:
                        total_size += dir_size
                        cache_items.append({
                            "type": "cache",
                            "name": cache_path,
                            "path": full_path,
                            "size": dir_size,
                            "size_formatted": self._format_size(dir_size)
                        })
                except:
                    pass
        
        # Optional: calculate size of cookies, history, etc. if needed
        # This would follow the same pattern as the cache calculation above
        
        return total_size, cache_items
    
    def _get_dir_size(self, path: str) -> int:
        """Calculate directory size recursively
        
        Args:
            path: Directory path
            
        Returns:
            Directory size in bytes
        """
        total_size = 0
        
        try:
            if os.path.isfile(path):
                return os.path.getsize(path)
            
            for dirpath, dirnames, filenames in os.walk(path):
                for filename in filenames:
                    file_path = os.path.join(dirpath, filename)
                    try:
                        total_size += os.path.getsize(file_path)
                    except (FileNotFoundError, PermissionError):
                        # Skip files that can't be accessed
                        pass
        except Exception as e:
            logging.error(f"Error getting directory size for {path}: {e}")
        
        return total_size
    
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
    
    def clean_browser_cache(self, browser_id: str = None, profile_name: str = None, 
                           clean_cookies: bool = False, clean_history: bool = False) -> Dict[str, Any]:
        """Clean browser cache
        
        Args:
            browser_id: Optional browser ID to clean. If None, cleans all browsers.
            profile_name: Optional profile name to clean. If None, cleans all profiles.
            clean_cookies: Whether to clean cookies
            clean_history: Whether to clean browsing history
            
        Returns:
            Dictionary with cleaning results
        """
        if not self.browsers_detected:
            self.detect_browsers()
        
        cleaned_items = 0
        cleaned_size = 0
        cleaned_browsers = []
        
        # If browser_id is specified, clean only that browser
        if browser_id and browser_id in self.detected_browsers:
            result = self._clean_browser(browser_id, profile_name, clean_cookies, clean_history)
            cleaned_items += result["cleaned_items"]
            cleaned_size += result["cleaned_size"]
            if result["cleaned_items"] > 0:
                cleaned_browsers.append(result)
        
        # Otherwise clean all detected browsers
        else:
            for browser_id in self.detected_browsers:
                result = self._clean_browser(browser_id, profile_name, clean_cookies, clean_history)
                cleaned_items += result["cleaned_items"]
                cleaned_size += result["cleaned_size"]
                if result["cleaned_items"] > 0:
                    cleaned_browsers.append(result)
        
        # Return results
        return {
            "cleaned_browsers": cleaned_browsers,
            "total_cleaned_items": cleaned_items,
            "total_cleaned_size": cleaned_size,
            "total_cleaned_size_formatted": self._format_size(cleaned_size)
        }
    
    def _clean_browser(self, browser_id: str, profile_name: str = None, 
                      clean_cookies: bool = False, clean_history: bool = False) -> Dict[str, Any]:
        """Clean a specific browser's cache
        
        Args:
            browser_id: Browser ID to clean
            profile_name: Optional profile name to clean. If None, cleans all profiles.
            clean_cookies: Whether to clean cookies
            clean_history: Whether to clean browsing history
            
        Returns:
            Dictionary with cleaning results for this browser
        """
        if browser_id not in self.detected_browsers or browser_id not in self.detected_profiles:
            return {"browser_id": browser_id, "cleaned_items": 0, "cleaned_size": 0, "cleaned_profiles": []}
        
        cleaned_profiles = []
        total_cleaned_items = 0
        total_cleaned_size = 0
        
        browser_info = self.browser_paths[browser_id]
        profiles_info = self.detected_profiles[browser_id]
        
        # Clean specific profile or all profiles
        profile_keys = [profile_name] if profile_name and profile_name in profiles_info else profiles_info.keys()
        
        for profile_key in profile_keys:
            profile_info = profiles_info[profile_key]
            profile_path = profile_info["path"]
            cleaned_items = []
            cleaned_size = 0
            
            # Clean cache items
            for item in profile_info["items"]:
                item_path = item["path"]
                try:
                    if os.path.exists(item_path):
                        # Get size before cleaning
                        item_size = item["size"]
                        
                        # Clean the item
                        if os.path.isdir(item_path):
                            # Try to remove contents only, not the directory itself
                            for root, dirs, files in os.walk(item_path, topdown=False):
                                for name in files:
                                    try:
                                        file_path = os.path.join(root, name)
                                        os.remove(file_path)
                                    except:
                                        pass
                                        
                                # Try to remove empty subdirectories
                                for name in dirs:
                                    try:
                                        dir_path = os.path.join(root, name)
                                        if not os.listdir(dir_path):  # Check if empty
                                            os.rmdir(dir_path)
                                    except:
                                        pass
                        else:
                            # For files, simply delete them
                            os.remove(item_path)
                        
                        cleaned_items.append(item["name"])
                        cleaned_size += item_size
                        total_cleaned_items += 1
                        total_cleaned_size += item_size
                except Exception as e:
                    logging.error(f"Error cleaning {item_path}: {e}")
            
            # Clean cookies if requested
            if clean_cookies:
                for cookie_path in browser_info["cookie_paths"]:
                    full_path = os.path.join(profile_path, cookie_path)
                    try:
                        if os.path.exists(full_path):
                            cookie_size = os.path.getsize(full_path)
                            os.remove(full_path)
                            cleaned_items.append(f"Cookies: {cookie_path}")
                            cleaned_size += cookie_size
                            total_cleaned_items += 1
                            total_cleaned_size += cookie_size
                    except Exception as e:
                        logging.error(f"Error cleaning cookies {full_path}: {e}")
            
            # Clean history if requested
            if clean_history:
                for history_path in browser_info["history_paths"]:
                    full_path = os.path.join(profile_path, history_path)
                    try:
                        if os.path.exists(full_path):
                            history_size = os.path.getsize(full_path)
                            os.remove(full_path)
                            cleaned_items.append(f"History: {history_path}")
                            cleaned_size += history_size
                            total_cleaned_items += 1
                            total_cleaned_size += history_size
                    except Exception as e:
                        logging.error(f"Error cleaning history {full_path}: {e}")
            
            # Add profile results
            if cleaned_items:
                cleaned_profiles.append({
                    "profile_name": profile_key,
                    "cleaned_items": cleaned_items,
                    "cleaned_size": cleaned_size,
                    "cleaned_size_formatted": self._format_size(cleaned_size)
                })
        
        # Return browser results
        return {
            "browser_id": browser_id,
            "browser_name": self.browser_paths[browser_id]["name"],
            "cleaned_items": total_cleaned_items,
            "cleaned_size": total_cleaned_size,
            "cleaned_size_formatted": self._format_size(total_cleaned_size),
            "cleaned_profiles": cleaned_profiles
        }


# Singleton instance
browser_cleaner = BrowserCleaner()

if __name__ == "__main__":
    # Test functionality
    logging.basicConfig(level=logging.INFO)
    
    print("Detecting browsers...")
    browser_data = browser_cleaner.detect_browsers()
    
    print(f"Found {browser_data['browser_count']} browsers with a total cache size of {browser_data['total_size_formatted']}")
    
    for browser_id, browser in browser_data["browsers"].items():
        print(f"- {browser['name']}: {browser['total_size_formatted']}")
        for profile in browser['profiles']:
            print(f"  - {profile['name']}: {profile['size_formatted']}")
    
    # Uncomment to test cleaning (USE WITH CAUTION!)
    # clean_result = browser_cleaner.clean_browser_cache()
    # print(f"Cleaned {clean_result['total_cleaned_items']} items ({clean_result['total_cleaned_size_formatted']})") 