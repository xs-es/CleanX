"""
Auto-Updater Module for Ultra Temp Cleaner Pro
---------------------------------------------
Checks for and applies updates to the application
"""

import os
import sys
import json
import logging
import tempfile
import shutil
import hashlib
import time
import platform
from typing import Dict, Any, Tuple, Optional, List
import subprocess
import urllib.request
import ssl
import zipfile
import threading

# Current version
VERSION = "1.1.0"

# Update server
UPDATE_SERVER = "https://example.com/updates"
UPDATE_CHECK_URL = f"{UPDATE_SERVER}/check.json"
UPDATE_DOWNLOAD_URL = f"{UPDATE_SERVER}/download"

class AutoUpdater:
    """Handles checking for and applying updates"""
    
    def __init__(self, current_version: str = VERSION, 
                app_dir: Optional[str] = None, 
                update_url: str = UPDATE_CHECK_URL):
        """
        Initialize the updater
        
        Args:
            current_version: Current version of the application
            app_dir: Application directory (defaults to current directory)
            update_url: URL to check for updates
        """
        self.current_version = current_version
        self.app_dir = app_dir or os.path.dirname(os.path.abspath(__file__))
        self.update_url = update_url
        self.latest_version = None
        self.update_info = None
        self.last_check_time = 0
        self.check_interval = 86400  # 24 hours
        
        # Status
        self.checking = False
        self.downloading = False
        self.update_available = False
        self.download_progress = 0
        self.status_message = "Ready"
        
        # Setup logging
        logging.basicConfig(
            filename='temp_file_finder.log',
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            force=True
        )
    
    def check_for_updates(self, force: bool = False) -> bool:
        """
        Check if updates are available
        
        Args:
            force: Force check even if already checked recently
            
        Returns:
            True if updates are available
        """
        # Don't check if already checking
        if self.checking:
            return self.update_available
        
        # Don't check too frequently unless forced
        current_time = time.time()
        if not force and current_time - self.last_check_time < self.check_interval:
            return self.update_available
        
        self.checking = True
        self.status_message = "Checking for updates..."
        
        try:
            # Create SSL context
            ctx = ssl.create_default_context()
            
            # Make request
            with urllib.request.urlopen(self.update_url, context=ctx, timeout=10) as response:
                data = response.read().decode('utf-8')
                update_info = json.loads(data)
                
                # Store update info
                self.update_info = update_info
                self.latest_version = update_info.get('version')
                
                # Check if update is available
                self.update_available = self._compare_versions(
                    self.latest_version, 
                    self.current_version
                )
                
                self.last_check_time = current_time
                
                if self.update_available:
                    self.status_message = f"Update available: {self.latest_version}"
                    logging.info(f"Update available: {self.latest_version}")
                else:
                    self.status_message = "No updates available"
                    logging.info("No updates available")
                
                return self.update_available
                
        except Exception as e:
            self.status_message = f"Update check failed: {str(e)}"
            logging.error(f"Error checking for updates: {e}")
            return False
        finally:
            self.checking = False
    
    def download_update(self, callback: Optional[callable] = None) -> bool:
        """
        Download the update
        
        Args:
            callback: Progress callback function(progress, status)
            
        Returns:
            True if download was successful
        """
        if not self.update_available or not self.update_info:
            self.status_message = "No update available to download"
            return False
        
        if self.downloading:
            self.status_message = "Download already in progress"
            return False
        
        self.downloading = True
        self.download_progress = 0
        self.status_message = "Preparing download..."
        
        if callback:
            callback(self.download_progress, self.status_message)
        
        try:
            # Get download URL and file info
            download_url = self.update_info.get('download_url')
            if not download_url:
                download_url = f"{UPDATE_DOWNLOAD_URL}/{self.latest_version}/ultratempcleanerpro-{self.latest_version}.zip"
            
            expected_size = self.update_info.get('size', 0)
            expected_hash = self.update_info.get('hash')
            
            # Create temporary directory
            temp_dir = tempfile.mkdtemp(prefix="utcp_update_")
            download_path = os.path.join(temp_dir, f"update-{self.latest_version}.zip")
            
            self.status_message = "Downloading update..."
            if callback:
                callback(5, self.status_message)
            
            # Download the file with progress updates
            self._download_file(download_url, download_path, expected_size, callback)
            
            # Verify hash if provided
            if expected_hash:
                self.status_message = "Verifying download..."
                if callback:
                    callback(95, self.status_message)
                
                file_hash = self._calculate_file_hash(download_path)
                if file_hash != expected_hash:
                    raise ValueError("Download verification failed: hash mismatch")
            
            self.status_message = "Download complete"
            if callback:
                callback(100, self.status_message)
            
            # Store download path for installation
            self.update_path = download_path
            logging.info(f"Update downloaded to {download_path}")
            
            return True
            
        except Exception as e:
            self.status_message = f"Download failed: {str(e)}"
            logging.error(f"Error downloading update: {e}")
            return False
        finally:
            self.downloading = False
    
    def install_update(self, restart: bool = True) -> bool:
        """
        Install the downloaded update
        
        Args:
            restart: Whether to restart the application after update
            
        Returns:
            True if installation was successful
        """
        if not hasattr(self, 'update_path') or not os.path.exists(self.update_path):
            self.status_message = "No update downloaded"
            return False
        
        self.status_message = "Installing update..."
        
        try:
            # Extract update
            temp_dir = os.path.dirname(self.update_path)
            extract_dir = os.path.join(temp_dir, "extract")
            os.makedirs(extract_dir, exist_ok=True)
            
            with zipfile.ZipFile(self.update_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
            
            # Find the updater script
            updater_script = os.path.join(extract_dir, "update_installer.py")
            if not os.path.exists(updater_script):
                # If no installer script, look for a default one
                default_installer = os.path.join(self.app_dir, "update_installer.py")
                if os.path.exists(default_installer):
                    shutil.copy(default_installer, updater_script)
                else:
                    # Create a basic installer script
                    self._create_installer_script(updater_script)
            
            # Run the updater script in a separate process
            update_cmd = [
                sys.executable,
                updater_script,
                "--source", extract_dir,
                "--target", self.app_dir,
                "--version", self.latest_version,
                "--current-version", self.current_version
            ]
            
            if restart:
                update_cmd.append("--restart")
                update_cmd.append(sys.executable)
                update_cmd.append(os.path.join(self.app_dir, "ui.py"))
            
            logging.info(f"Running updater: {' '.join(update_cmd)}")
            
            # Run the updater
            if platform.system() == "Windows":
                subprocess.Popen(update_cmd, creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
            else:
                subprocess.Popen(update_cmd)
            
            self.status_message = "Update installer launched"
            
            # If restart requested, exit this process
            if restart:
                logging.info("Exiting for update installation")
                time.sleep(1)  # Give time for the installer to start
                os._exit(0)
            
            return True
            
        except Exception as e:
            self.status_message = f"Installation failed: {str(e)}"
            logging.error(f"Error installing update: {e}")
            return False
    
    def check_and_download_in_background(self, callback: Optional[callable] = None) -> None:
        """
        Check for updates and download in background
        
        Args:
            callback: Progress callback function(progress, status, available)
        """
        thread = threading.Thread(
            target=self._background_update_check,
            args=(callback,),
            daemon=True
        )
        thread.start()
    
    def _background_update_check(self, callback: Optional[callable]) -> None:
        """
        Background thread for update checking and downloading
        
        Args:
            callback: Progress callback function
        """
        try:
            # Check for updates
            update_available = self.check_for_updates(force=True)
            
            if callback:
                callback(0, self.status_message, update_available)
            
            # If update available, download it
            if update_available:
                success = self.download_update(
                    lambda progress, status: callback(progress, status, update_available)
                    if callback else None
                )
                
                if callback:
                    callback(100, self.status_message, update_available)
            
        except Exception as e:
            logging.error(f"Error in background update check: {e}")
            self.status_message = f"Update check failed: {str(e)}"
            if callback:
                callback(0, self.status_message, False)
    
    def _download_file(self, url: str, destination: str, expected_size: int, 
                      callback: Optional[callable] = None) -> None:
        """
        Download a file with progress updates
        
        Args:
            url: URL to download from
            destination: Local file path to save to
            expected_size: Expected file size in bytes (for progress)
            callback: Progress callback function
        """
        try:
            # Create SSL context
            ctx = ssl.create_default_context()
            
            # Open request
            with urllib.request.urlopen(url, context=ctx, timeout=30) as response:
                # Get file size if not provided
                file_size = expected_size or int(response.info().get('Content-Length', 0))
                
                # Download with progress updates
                downloaded = 0
                block_size = 8192
                
                with open(destination, 'wb') as f:
                    while True:
                        buffer = response.read(block_size)
                        if not buffer:
                            break
                        
                        downloaded += len(buffer)
                        f.write(buffer)
                        
                        # Update progress
                        if file_size > 0:
                            progress = int(20 + (downloaded / file_size) * 70)  # Scale to 20-90%
                            self.download_progress = progress
                            
                            if callback:
                                callback(progress, f"Downloading: {downloaded/1024/1024:.1f} MB / {file_size/1024/1024:.1f} MB")
        
        except Exception as e:
            raise Exception(f"Download failed: {str(e)}")
    
    def _calculate_file_hash(self, file_path: str) -> str:
        """
        Calculate SHA-256 hash of a file
        
        Args:
            file_path: Path to the file
            
        Returns:
            SHA-256 hash as hex string
        """
        sha256_hash = hashlib.sha256()
        
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        
        return sha256_hash.hexdigest()
    
    def _compare_versions(self, version1: str, version2: str) -> bool:
        """
        Compare version strings
        
        Args:
            version1: First version string
            version2: Second version string
            
        Returns:
            True if version1 > version2
        """
        if not version1 or not version2:
            return False
            
        v1_parts = version1.split('.')
        v2_parts = version2.split('.')
        
        # Pad with zeros
        while len(v1_parts) < len(v2_parts):
            v1_parts.append('0')
        while len(v2_parts) < len(v1_parts):
            v2_parts.append('0')
        
        # Compare parts
        for i in range(len(v1_parts)):
            try:
                if int(v1_parts[i]) > int(v2_parts[i]):
                    return True
                elif int(v1_parts[i]) < int(v2_parts[i]):
                    return False
            except ValueError:
                # Handle non-numeric version parts
                if v1_parts[i] > v2_parts[i]:
                    return True
                elif v1_parts[i] < v2_parts[i]:
                    return False
        
        # Versions are equal
        return False
    
    def _create_installer_script(self, script_path: str) -> None:
        """
        Create a basic installer script
        
        Args:
            script_path: Path to write the script
        """
        script_content = """#!/usr/bin/env python3
import os
import sys
import shutil
import time
import argparse
import subprocess

def main():
    # Parse arguments
    parser = argparse.ArgumentParser(description="Update Installer")
    parser.add_argument("--source", required=True, help="Source directory")
    parser.add_argument("--target", required=True, help="Target directory")
    parser.add_argument("--version", required=True, help="New version")
    parser.add_argument("--current-version", required=True, help="Current version")
    parser.add_argument("--restart", action="store_true", help="Restart after update")
    parser.add_argument("--python", default=sys.executable, help="Python executable path")
    parser.add_argument("--script", default="ui.py", help="Script to run after update")
    
    args = parser.parse_args()
    
    print(f"Installing update {args.version} from {args.source} to {args.target}")
    
    # Wait for original process to exit
    time.sleep(2)
    
    try:
        # Copy files
        for item in os.listdir(args.source):
            source_item = os.path.join(args.source, item)
            target_item = os.path.join(args.target, item)
            
            if os.path.isdir(source_item):
                # Copy directory
                if os.path.exists(target_item):
                    shutil.rmtree(target_item)
                shutil.copytree(source_item, target_item)
            else:
                # Copy file
                shutil.copy2(source_item, target_item)
        
        print("Update installed successfully")
        
        # Restart application if requested
        if args.restart:
            script_path = os.path.join(args.target, args.script)
            print(f"Restarting application: {args.python} {script_path}")
            subprocess.Popen([args.python, script_path])
    
    except Exception as e:
        print(f"Error installing update: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
"""
        
        with open(script_path, "w") as f:
            f.write(script_content)
        
        # Make executable on Unix
        if platform.system() != "Windows":
            os.chmod(script_path, 0o755)


def check_for_updates_in_background(callback: Optional[callable] = None) -> None:
    """
    Utility function to check for updates in the background
    
    Args:
        callback: Progress callback function(progress, status, available)
    """
    updater = AutoUpdater()
    updater.check_and_download_in_background(callback)


if __name__ == "__main__":
    # Test the updater
    updater = AutoUpdater()
    print(f"Current version: {updater.current_version}")
    
    # Mock update check
    updater.update_info = {
        'version': '1.2.0',
        'download_url': 'https://example.com/download/ultratempcleanerpro-1.2.0.zip',
        'size': 1024 * 1024,  # 1MB
        'hash': 'a' * 64,  # fake hash
        'release_notes': 'Test update'
    }
    updater.latest_version = '1.2.0'
    updater.update_available = True
    
    print(f"Update available: {updater.update_available}")
    print(f"Latest version: {updater.latest_version}")
    print(f"Status: {updater.status_message}") 