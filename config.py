#!/usr/bin/env python3
"""
Configuration Module for Ultra Temp Cleaner Pro
----------------------------------------------
Centralizes configuration and feature settings
"""

import os
import json
import logging
import tempfile
from typing import Dict, Any, List, Optional
import platform

# Default configuration
DEFAULT_CONFIG = {
    # Core settings
    "app_name": "Ultra Temp Cleaner Pro X",
    "version": "2.0.0",
    
    # Feature flags
    "features": {
        # Existing features
        "duplicate_detection": True,
        "secure_delete": True,
        "scheduling": True,
        "system_tray": True,
        "statistics": True,
        
        # New features
        "browser_cache_cleaning": True,
        "registry_cleaning": True,
        "startup_manager": True,
        "memory_optimization": True,
        "disk_analyzer": True,
        "cloud_backup": True,
        "smart_scan": True,
        "file_shredder": True,
        "privacy_cleaner": True,
        "app_uninstaller": True,
        "system_monitor": True,
        "file_recovery": True,
        "blockchain_verification": True,
        "ai_cleaning": True,
        "advanced_scheduler": True,
        "remote_management": True,
        "multi_device_sync": True,
        "smart_recommendations": True,
        "password_protected_folders": True,
        "multi_user_profiles": True
    },
    
    # Visual settings
    "ui": {
        "theme": "dark",
        "accent_color": "#7B68EE",
        "animations": True,
        "compact_mode": False,
        "show_tooltips": True,
        "sidebar_visible": True,
        "statistics_on_dashboard": True,
        "show_welcome_screen": True
    },
    
    # Scanning settings
    "scanning": {
        "default_min_age": 7,
        "scan_browser_cache": True,
        "deep_scan_enabled": True,
        "auto_scan_on_startup": False,
        "excluded_dirs": [],
        "protected_patterns": [
            "important", "essential", "critical",
            "backup", "save", "document"
        ],
        "thread_count": 4,
        "skip_system_dirs": True,
        "follow_symlinks": False,
        "recursive_scan": True,
        "max_scan_depth": 10
    },
    
    # Cleaning settings
    "cleaning": {
        "auto_clean": False,
        "safe_clean_only": True,
        "backup_before_clean": True,
        "secure_deletion_passes": 3,
        "clean_browser_data": True,
        "clean_registry": False,
        "clean_system_logs": False,
        "clean_thumbnails": True,
        "clean_recycle_bin": False,
        "verify_after_clean": True
    },
    
    # Scheduling settings
    "scheduling": {
        "enabled": False,
        "frequency": "daily",
        "auto_clean": False,
        "time": "00:00",
        "days": ["Monday", "Wednesday", "Friday"],
        "notify_before_clean": True,
        "idle_required": True,
        "idle_timeout": 10,
        "run_missed_tasks": True
    },
    
    # Notification settings
    "notifications": {
        "enabled": True,
        "show_scan_complete": True,
        "show_clean_complete": True,
        "show_scheduled_tasks": True,
        "show_update_available": True,
        "sound_effects": True,
        "email_reports": False,
        "email_address": "",
        "desktop_notifications": True
    },
    
    # Advanced settings
    "advanced": {
        "logging_level": "INFO",
        "debug_mode": False,
        "experimental_features": False,
        "api_enabled": False,
        "api_port": 8080,
        "api_key": "",
        "telemetry": False,
        "auto_update": True,
        "update_channel": "stable",
        "proxy_enabled": False,
        "proxy_url": "",
        "startup_with_system": False
    }
}

class ConfigManager:
    """Configuration manager for Ultra Temp Cleaner Pro"""
    
    def __init__(self):
        """Initialize configuration manager"""
        self.config = DEFAULT_CONFIG.copy()
        self.config_file = os.path.join(tempfile.gettempdir(), 'ultra_temp_cleaner_config.json')
        self.load_config()
    
    def load_config(self) -> None:
        """Load configuration from file"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    loaded_config = json.load(f)
                    # Deep merge to preserve defaults for new settings
                    self._deep_merge(self.config, loaded_config)
                    logging.info("Configuration loaded from file")
        except Exception as e:
            logging.error(f"Error loading configuration: {e}")
    
    def save_config(self) -> None:
        """Save configuration to file"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
                logging.info("Configuration saved to file")
        except Exception as e:
            logging.error(f"Error saving configuration: {e}")
    
    def _deep_merge(self, target: Dict[str, Any], source: Dict[str, Any]) -> None:
        """Deep merge source dictionary into target dictionary"""
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                self._deep_merge(target[key], value)
            else:
                target[key] = value
    
    def get(self, section: str, key: str, default: Any = None) -> Any:
        """Get a configuration value"""
        try:
            return self.config[section][key]
        except KeyError:
            return default
    
    def set(self, section: str, key: str, value: Any) -> None:
        """Set a configuration value"""
        if section not in self.config:
            self.config[section] = {}
        self.config[section][key] = value
        self.save_config()
    
    def is_feature_enabled(self, feature_name: str) -> bool:
        """Check if a feature is enabled"""
        return self.config["features"].get(feature_name, False)
    
    def enable_feature(self, feature_name: str) -> None:
        """Enable a feature"""
        self.config["features"][feature_name] = True
        self.save_config()
    
    def disable_feature(self, feature_name: str) -> None:
        """Disable a feature"""
        self.config["features"][feature_name] = False
        self.save_config()
    
    def get_all_features(self) -> Dict[str, bool]:
        """Get all feature flags"""
        return self.config["features"].copy()
    
    def reset_to_defaults(self) -> None:
        """Reset configuration to defaults"""
        self.config = DEFAULT_CONFIG.copy()
        self.save_config()
    
    def export_config(self, file_path: str) -> bool:
        """Export configuration to file"""
        try:
            with open(file_path, 'w') as f:
                json.dump(self.config, f, indent=2)
            return True
        except Exception as e:
            logging.error(f"Error exporting configuration: {e}")
            return False
    
    def import_config(self, file_path: str) -> bool:
        """Import configuration from file"""
        try:
            with open(file_path, 'r') as f:
                imported_config = json.load(f)
                # Validate imported config
                if not self._validate_config(imported_config):
                    return False
                # Deep merge to preserve defaults for new settings
                self.config = DEFAULT_CONFIG.copy()
                self._deep_merge(self.config, imported_config)
                self.save_config()
            return True
        except Exception as e:
            logging.error(f"Error importing configuration: {e}")
            return False
    
    def _validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate imported configuration"""
        # Basic validation - check if top-level sections exist
        required_sections = ["features", "ui", "scanning", "cleaning", "scheduling", "notifications", "advanced"]
        for section in required_sections:
            if section not in config:
                logging.error(f"Missing required section in config: {section}")
                return False
        return True


# Global configuration instance
config_manager = ConfigManager()

# Utility functions
def get_system_info() -> Dict[str, Any]:
    """Get system information"""
    return {
        "os": platform.system(),
        "os_version": platform.release(),
        "platform": platform.platform(),
        "processor": platform.processor(),
        "architecture": platform.architecture()[0],
        "python_version": platform.python_version(),
        "machine": platform.machine(),
        "node": platform.node(),
        "username": os.environ.get("USERNAME", os.environ.get("USER", "unknown"))
    }

def is_admin() -> bool:
    """Check if the application is running with administrator privileges"""
    try:
        if platform.system() == "Windows":
            import ctypes
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        else:
            return os.geteuid() == 0
    except:
        return False

# Initialize
if __name__ == "__main__":
    print(f"Configuration loaded. App name: {config_manager.get('app_name', 'name')}")
    print(f"Features enabled: {sum(1 for f, e in config_manager.get_all_features().items() if e)}") 