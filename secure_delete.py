"""
Secure Delete Module for Ultra Temp Cleaner Pro
----------------------------------------------
Provides secure file deletion with multiple overwrite passes
"""

import os
import random
import logging
import shutil
from typing import Optional, List, Tuple
import time

class SecureDelete:
    """
    Securely delete files by overwriting with multiple passes before deletion.
    
    Security levels:
    - 1: Single pass with zeros
    - 2: Two passes (random data + zeros)
    - 3: DoD 5220.22-M standard (3 passes)
    - 7: Gutmann method (simplified to 7 passes)
    """
    
    def __init__(self, passes: int = 3):
        """
        Initialize the secure delete utility
        
        Args:
            passes: Number of overwrite passes (1, 2, 3, or 7)
        """
        self.passes = min(max(passes, 1), 7)  # Limit between 1 and 7
        logging.info(f"Initialized SecureDelete with {self.passes} passes")
    
    def secure_delete_file(self, file_path: str) -> bool:
        """
        Securely delete a file with multiple overwrite passes
        
        Args:
            file_path: Path to the file to be deleted
            
        Returns:
            True if deletion was successful
        """
        try:
            # Check if file exists
            if not os.path.isfile(file_path):
                logging.warning(f"File not found: {file_path}")
                return False
            
            # Get file size
            file_size = os.path.getsize(file_path)
            if file_size == 0:
                # For empty files, just delete them
                os.remove(file_path)
                return True
            
            # Perform secure deletion
            success = self._perform_secure_deletion(file_path, file_size)
            
            # If successful, delete the file
            if success:
                os.remove(file_path)
                logging.info(f"Securely deleted file: {file_path}")
                return True
            
            return False
            
        except PermissionError as e:
            logging.error(f"Permission error deleting {file_path}: {e}")
            return False
        except FileNotFoundError:
            logging.warning(f"File not found during deletion: {file_path}")
            return False
        except Exception as e:
            logging.error(f"Error securely deleting {file_path}: {e}")
            return False
    
    def secure_delete_directory(self, dir_path: str) -> bool:
        """
        Securely delete a directory by securely deleting all files and then removing the directory
        
        Args:
            dir_path: Path to the directory to be deleted
            
        Returns:
            True if deletion was successful
        """
        try:
            # Check if directory exists
            if not os.path.isdir(dir_path):
                logging.warning(f"Directory not found: {dir_path}")
                return False
            
            # Walk through directory and delete all files securely
            success = True
            for root, dirs, files in os.walk(dir_path, topdown=False):
                # Delete files
                for file in files:
                    file_path = os.path.join(root, file)
                    if not self.secure_delete_file(file_path):
                        success = False
                
                # Delete empty directories
                for directory in dirs:
                    dir_path = os.path.join(root, directory)
                    try:
                        os.rmdir(dir_path)
                    except:
                        success = False
            
            # Finally delete the root directory
            try:
                os.rmdir(dir_path)
            except:
                success = False
            
            return success
            
        except PermissionError as e:
            logging.error(f"Permission error deleting directory {dir_path}: {e}")
            return False
        except Exception as e:
            logging.error(f"Error securely deleting directory {dir_path}: {e}")
            return False
    
    def _perform_secure_deletion(self, file_path: str, file_size: int) -> bool:
        """
        Perform the actual secure deletion with multiple passes
        
        Args:
            file_path: Path to the file to be deleted
            file_size: Size of the file in bytes
            
        Returns:
            True if overwriting was successful
        """
        try:
            # Open the file for writing in binary mode
            with open(file_path, "r+b") as f:
                # Different overwrite patterns based on number of passes
                if self.passes == 1:
                    # Single pass with zeros
                    patterns = [b"\x00"]
                elif self.passes == 2:
                    # Two passes: random + zeros
                    patterns = [self._random_bytes(file_size), b"\x00"]
                elif self.passes == 3:
                    # DoD 5220.22-M standard (3 passes)
                    patterns = [b"\x00", b"\xFF", self._random_bytes(file_size)]
                else:
                    # Gutmann method (simplified to 7 passes)
                    patterns = [
                        b"\x55", b"\xAA", b"\x92\x49\x24", b"\x49\x24\x92", 
                        b"\x24\x92\x49", self._random_bytes(file_size), b"\x00"
                    ]
                
                # Perform each overwrite pass
                for i, pattern in enumerate(patterns):
                    if len(pattern) == 1:
                        # Single byte pattern
                        self._overwrite_with_pattern(f, file_size, pattern)
                    elif len(pattern) == file_size:
                        # Random data pre-generated
                        f.seek(0)
                        f.write(pattern)
                    else:
                        # Multi-byte pattern
                        self._overwrite_with_pattern(f, file_size, pattern)
                    
                    # Flush after each pass
                    f.flush()
                    os.fsync(f.fileno())
                
                return True
                
        except Exception as e:
            logging.error(f"Error during secure overwrite: {e}")
            return False
    
    def _overwrite_with_pattern(self, file_obj, file_size: int, pattern: bytes) -> None:
        """
        Overwrite a file with a specific pattern
        
        Args:
            file_obj: Open file object in binary write mode
            file_size: Size of the file in bytes
            pattern: Byte pattern to write
        """
        # Go to the beginning of the file
        file_obj.seek(0)
        
        # Calculate buffer size (4KB chunks)
        buffer_size = 4096
        pattern_buffer = pattern * (buffer_size // len(pattern) + 1)
        pattern_buffer = pattern_buffer[:buffer_size]
        
        # Write in chunks
        bytes_remaining = file_size
        while bytes_remaining > 0:
            if bytes_remaining < buffer_size:
                file_obj.write(pattern_buffer[:bytes_remaining])
                bytes_remaining = 0
            else:
                file_obj.write(pattern_buffer)
                bytes_remaining -= buffer_size
    
    def _random_bytes(self, size: int) -> bytes:
        """
        Generate random bytes of specified size
        
        Args:
            size: Number of bytes to generate
            
        Returns:
            Random bytes
        """
        # For large files, generate in chunks to save memory
        if size > 1024 * 1024:  # 1MB
            return b"RANDOM"  # Placeholder to generate during overwrite
        
        # For smaller files, generate all at once
        return bytes(random.getrandbits(8) for _ in range(size))


def quick_secure_delete(file_path: str, passes: int = 1) -> bool:
    """
    Quick utility function to securely delete a file
    
    Args:
        file_path: Path to the file to be deleted
        passes: Number of overwrite passes (1, 2, 3, or 7)
        
    Returns:
        True if deletion was successful
    """
    secure_delete = SecureDelete(passes)
    return secure_delete.secure_delete_file(file_path)


if __name__ == "__main__":
    # Test the secure delete functionality
    import tempfile
    
    # Create a test file
    with tempfile.NamedTemporaryFile(delete=False) as f:
        f.write(b"This is a test file with sensitive data")
        test_file = f.name
    
    print(f"Created test file: {test_file}")
    
    # Securely delete the file
    secure_delete = SecureDelete(passes=3)
    result = secure_delete.secure_delete_file(test_file)
    
    print(f"Secure deletion {'successful' if result else 'failed'}")
    print(f"File exists after deletion: {os.path.exists(test_file)}") 