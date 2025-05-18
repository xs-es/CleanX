"""
Language Support Module for Ultra Temp Cleaner Pro
-------------------------------------------------
Provides internationalization support for multiple languages
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional

# Available languages
AVAILABLE_LANGUAGES = {
    "en": "English",
    "es": "Español",
    "fr": "Français",
    "de": "Deutsch",
    "it": "Italiano",
    "pt": "Português",
    "ru": "Русский",
    "zh": "中文",
    "ja": "日本語",
    "ko": "한국어"
}

# Default language
DEFAULT_LANGUAGE = "en"

class LanguageManager:
    """Manages language settings and translations"""
    
    def __init__(self, languages_dir: str = "languages", default_lang: str = DEFAULT_LANGUAGE):
        self.languages_dir = languages_dir
        self.default_lang = default_lang
        self.current_lang = default_lang
        self.translations = {}
        
        # Create languages directory if it doesn't exist
        os.makedirs(self.languages_dir, exist_ok=True)
        
        # Initialize with default language
        self.load_language(default_lang)
        
        # Create missing language files if needed
        self._ensure_language_files()
    
    def get_available_languages(self) -> Dict[str, str]:
        """Get a dictionary of available languages"""
        return AVAILABLE_LANGUAGES
    
    def set_language(self, lang_code: str) -> bool:
        """Set the current language"""
        if lang_code in AVAILABLE_LANGUAGES:
            success = self.load_language(lang_code)
            if success:
                self.current_lang = lang_code
            return success
        return False
    
    def get_current_language(self) -> str:
        """Get the current language code"""
        return self.current_lang
    
    def get_text(self, key: str, default: Optional[str] = None) -> str:
        """Get translated text for a key"""
        if key in self.translations:
            return self.translations[key]
        
        # If not found, try default language
        if self.current_lang != self.default_lang:
            if key in self.default_translations:
                # Log missing translation
                logging.warning(f"Missing translation for '{key}' in {self.current_lang}")
                return self.default_translations[key]
        
        # If still not found, return the key or default value
        if default is not None:
            return default
        return key
    
    def load_language(self, lang_code: str) -> bool:
        """Load language translations from file"""
        lang_file = os.path.join(self.languages_dir, f"{lang_code}.json")
        
        try:
            if os.path.exists(lang_file):
                with open(lang_file, "r", encoding="utf-8") as f:
                    self.translations = json.load(f)
                
                # Keep default translations for fallback
                if lang_code == self.default_lang:
                    self.default_translations = self.translations.copy()
                
                logging.info(f"Loaded language: {lang_code}")
                return True
            else:
                # If file doesn't exist, create it with default English
                if lang_code != "en":
                    self._create_language_file(lang_code)
                    
                # Load English as fallback
                return self.load_language("en")
        except Exception as e:
            logging.error(f"Error loading language {lang_code}: {e}")
            
            # Fallback to English
            if lang_code != "en":
                return self.load_language("en")
            return False
    
    def _ensure_language_files(self) -> None:
        """Ensure all language files exist"""
        for lang_code in AVAILABLE_LANGUAGES:
            lang_file = os.path.join(self.languages_dir, f"{lang_code}.json")
            if not os.path.exists(lang_file):
                self._create_language_file(lang_code)
    
    def _create_language_file(self, lang_code: str) -> None:
        """Create a new language file with default English texts"""
        # If English file doesn't exist yet, create the default
        if lang_code == "en" or not os.path.exists(os.path.join(self.languages_dir, "en.json")):
            self._create_english_file()
        
        # For other languages, copy English file
        if lang_code != "en":
            try:
                # Load English translations
                with open(os.path.join(self.languages_dir, "en.json"), "r", encoding="utf-8") as f:
                    translations = json.load(f)
                
                # Save as new language file
                with open(os.path.join(self.languages_dir, f"{lang_code}.json"), "w", encoding="utf-8") as f:
                    json.dump(translations, f, indent=2, ensure_ascii=False)
                
                logging.info(f"Created language file: {lang_code}.json")
            except Exception as e:
                logging.error(f"Error creating language file {lang_code}.json: {e}")
    
    def _create_english_file(self) -> None:
        """Create the default English language file"""
        try:
            # Default English translations
            translations = {
                # Common
                "app_name": "Ultra Temp Cleaner Pro",
                "version": "Version",
                "ok": "OK",
                "cancel": "Cancel",
                "yes": "Yes",
                "no": "No",
                "apply": "Apply",
                "save": "Save",
                "delete": "Delete",
                "close": "Close",
                "error": "Error",
                "warning": "Warning",
                "info": "Information",
                "success": "Success",
                
                # Main UI
                "file_scanner_tab": "File Scanner",
                "statistics_tab": "Statistics",
                "settings_tab": "Settings",
                "scheduler_tab": "Scheduler",
                "about_tab": "About",
                
                # Scanner tab
                "scan_controls": "Scan Controls",
                "location": "Location:",
                "temp_dirs": "Temp Dirs",
                "all_drives": "All Drives",
                "scan_button": "⚡ Scan",
                "stop_button": "⏹ Stop",
                "filters": "Filters",
                "type": "Type:",
                "age": "Age:",
                "size": "Size:",
                "apply_filter": "Apply",
                "search": "Search:",
                "select_matching": "🔍 Select Matching",
                "select_all": "✓ Select All",
                "deselect_all": "✗ Deselect All",
                "scan_results": "Scan Results",
                "delete_selected": "🗑️ Delete Selected",
                "ready_to_scan": "Ready to scan",
                "scanning": "Scanning:",
                "scan_complete": "Scan complete",
                "scan_stopped": "Scan stopped",
                "found_files": "Found {count} files ({size})",
                "no_files_found": "No files found",
                "confirm_delete": "Are you sure you want to delete the selected files?",
                "delete_success": "Successfully deleted {count} files",
                "delete_partial": "Deleted {success} files, {failed} files could not be deleted",
                "delete_none": "No files were deleted",
                "delete_error": "Error deleting files",
                
                # Statistics tab
                "storage_dashboard": "Storage Dashboard",
                "total": "Total:",
                "data_analysis": "Data Analysis",
                "visual_analysis": "Visual Analysis",
                "by_type": "By Type",
                "by_age": "By Age",
                "by_size": "By Size",
                "category": "Category",
                "value": "Size",
                "percent": "%",
                "export_chart": "Export Chart",
                "no_data": "No data to display",
                
                # Settings tab
                "minimum_file_age": "Minimum File Age",
                "days": "Days:",
                "excluded_directories": "Excluded Directories",
                "add": "Add",
                "remove": "Remove",
                "appearance": "Appearance",
                "enable_dark_mode": "Enable Dark Mode",
                "auto_theme": "Auto-detect system theme",
                "performance": "Performance",
                "max_threads": "Maximum threads:",
                "security": "Security",
                "backup_files": "Create backups before deletion",
                "secure_delete": "Secure file deletion",
                "overwrite_passes": "Overwrite passes:",
                "language": "Language",
                "language_select": "Select language:",
                "restart_required": "Restart required to apply changes",
                
                # Scheduler tab
                "scheduled_cleaning": "Scheduled Cleaning",
                "add_schedule": "Add Schedule",
                "edit_schedule": "Edit Schedule",
                "delete_schedule": "Delete Schedule",
                "enable_schedule": "Enable",
                "disable_schedule": "Disable",
                "schedule_name": "Name:",
                "frequency": "Frequency:",
                "time": "Time:",
                "daily": "Daily",
                "weekly": "Weekly",
                "monthly": "Monthly",
                "options": "Options",
                "auto_delete": "Auto-delete files",
                "generate_report": "Generate report",
                "headless": "Run in background",
                "next_run": "Next run:",
                "last_run": "Last run:",
                "status": "Status:",
                "enabled": "Enabled",
                "disabled": "Disabled",
                "save_schedule": "Save Schedule",
                "confirm_delete_schedule": "Are you sure you want to delete this schedule?",
                
                # About tab
                "about": "About",
                "description": "A powerful application to scan, analyze, and clean temporary files from your system.",
                "features": "Features",
                "system_info": "System Information",
                "os": "Operating System:",
                "python": "Python Version:",
                "cpu": "CPU:",
                "memory": "Memory:",
                "check_updates": "Check for Updates",
                "up_to_date": "You have the latest version",
                "update_available": "Update available: {version}",
                "credits": "Credits",
                "license": "License",
                "website": "Website",
                
                # Dialogs
                "admin_required": "Administrator Rights Required",
                "admin_message": "Some files require administrator privileges to delete.",
                "restart_as_admin": "Restart as Administrator",
                "deleting_files": "Deleting Files",
                "processing_file": "Processing file {current} of {total}",
                "use_admin": "Use administrator privileges (for system files)",
                "completed": "Completed",
                "file_not_found": "File not found",
                "access_denied": "Access denied",
                "confirm_exit": "Are you sure you want to exit?",
                "unsaved_changes": "You have unsaved changes",
                
                # Context menu
                "open_file": "Open File",
                "open_folder": "Open Containing Folder",
                "copy_path": "Copy Path",
                "delete_file": "Delete File",
                "exclude_folder": "Exclude Folder",
                "exclude_type": "Exclude File Type",
                "file_properties": "Properties",
                
                # File types
                "temp_files": "Temporary Files",
                "cache_files": "Cache Files",
                "log_files": "Log Files",
                "backup_files": "Backup Files",
                
                # Age categories
                "recent_files": "Recent (< 7 days)",
                "week_old": "Week old (7-30 days)",
                "month_old": "Month old (30-90 days)",
                "old_files": "Old (> 90 days)",
                
                # Size categories
                "small_files": "Small (< 1 MB)",
                "medium_files": "Medium (1-10 MB)",
                "large_files": "Large (10-100 MB)",
                "huge_files": "Huge (> 100 MB)"
            }
            
            # Save translations
            with open(os.path.join(self.languages_dir, "en.json"), "w", encoding="utf-8") as f:
                json.dump(translations, f, indent=2, ensure_ascii=False)
            
            logging.info("Created default English language file")
        except Exception as e:
            logging.error(f"Error creating English language file: {e}")

# Global instance
language_manager = LanguageManager()

# Shorthand function for getting translated text
def _(key: str, default: Optional[str] = None) -> str:
    """Get translated text for a key"""
    return language_manager.get_text(key, default)


if __name__ == "__main__":
    # Test the language manager
    print(f"Available languages: {language_manager.get_available_languages()}")
    print(f"Current language: {language_manager.get_current_language()}")
    print(f"App name: {_('app_name')}")
    
    # Test changing language
    language_manager.set_language("es")
    print(f"Current language: {language_manager.get_current_language()}")
    print(f"App name: {_('app_name')}") 