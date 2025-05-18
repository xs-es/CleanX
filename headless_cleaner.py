#!/usr/bin/env python3
"""
Headless Temp File Cleaner
--------------------------
A command-line version of the Temp File Cleaner for scheduled operations
"""

import os
import sys
import time
import logging
import argparse
from typing import List, Dict, Any, Optional
from main import TempFileFinder

def setup_logging():
    """Setup logging configuration"""
    logging.basicConfig(
        filename='temp_file_finder.log',
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        force=True
    )
    
    # Add console logging
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    console.setFormatter(formatter)
    logging.getLogger().addHandler(console)

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Headless Temp File Cleaner")
    
    # Basic options
    parser.add_argument("--location", choices=["temp", "all"], default="temp",
                      help="Scan location: temp directories or all drives")
    parser.add_argument("--min-age", type=int, default=0,
                      help="Minimum file age in days to consider for deletion")
    parser.add_argument("--auto-delete", action="store_true",
                      help="Automatically delete found files")
    
    # Filter options
    parser.add_argument("--file-types", type=str, default="all",
                      help="File types to target (all, temp, cache, logs)")
    parser.add_argument("--size-filter", type=str, default="all",
                      help="Size filter (all, small, medium, large, huge)")
    parser.add_argument("--age-filter", type=str, default="all",
                      help="Age filter (all, recent, week, month, old)")
    
    # Additional options
    parser.add_argument("--exclude-dir", action="append", default=[],
                      help="Directories to exclude (can be used multiple times)")
    parser.add_argument("--report", action="store_true",
                      help="Generate a detailed report after scanning")
    parser.add_argument("--report-path", type=str, default="",
                      help="Path to save the report (default: current directory)")
    parser.add_argument("--max-delete-size", type=float, default=0,
                      help="Maximum total size to delete in MB (0 = unlimited)")
    
    return parser.parse_args()

def filter_files(files: List[Dict[str, Any]], args) -> List[Dict[str, Any]]:
    """Filter files based on command line arguments"""
    filtered_files = []
    
    for file_info in files:
        # Apply file type filter
        if args.file_types != "all":
            file_path = file_info["path"].lower()
            if args.file_types == "temp" and not any(pattern in file_path for pattern in [".tmp", ".temp"]):
                continue
            if args.file_types == "cache" and ".cache" not in file_path:
                continue
            if args.file_types == "logs" and ".log" not in file_path:
                continue
        
        # Apply age filter
        age_days = file_info["age_days"]
        if args.age_filter != "all":
            if args.age_filter == "recent" and age_days >= 7:
                continue
            if args.age_filter == "week" and (age_days < 7 or age_days >= 30):
                continue
            if args.age_filter == "month" and (age_days < 30 or age_days >= 90):
                continue
            if args.age_filter == "old" and age_days < 90:
                continue
        
        # Apply size filter
        file_size_mb = file_info["size"] / (1024 * 1024)
        if args.size_filter != "all":
            if args.size_filter == "small" and file_size_mb >= 1:
                continue
            if args.size_filter == "medium" and (file_size_mb < 1 or file_size_mb >= 10):
                continue
            if args.size_filter == "large" and (file_size_mb < 10 or file_size_mb >= 100):
                continue
            if args.size_filter == "huge" and file_size_mb < 100:
                continue
        
        filtered_files.append(file_info)
    
    return filtered_files

def delete_files(files: List[Dict[str, Any]], finder: TempFileFinder, 
                max_delete_size: float = 0) -> Dict[str, Any]:
    """Delete files and return statistics"""
    result = {
        "total_files": len(files),
        "deleted_files": 0,
        "failed_files": 0,
        "total_size": 0,
        "deleted_size": 0,
        "skipped_size": 0,
        "protected_files": 0,
        "failed_paths": []
    }
    
    # Calculate total size
    for file_info in files:
        result["total_size"] += file_info["size"]
    
    # Convert max_delete_size from MB to bytes
    max_delete_bytes = max_delete_size * 1024 * 1024 if max_delete_size > 0 else 0
    
    # Delete files
    current_deleted_size = 0
    for file_info in files:
        # Check if we've reached the maximum delete size
        if max_delete_bytes > 0 and current_deleted_size + file_info["size"] > max_delete_bytes:
            logging.info(f"Reached maximum delete size limit ({max_delete_size} MB)")
            result["skipped_size"] += file_info["size"]
            continue
        
        # Skip protected files
        if file_info.get("is_protected", False):
            logging.info(f"Skipping protected file: {file_info['path']}")
            result["protected_files"] += 1
            result["skipped_size"] += file_info["size"]
            continue
        
        # Delete the file
        if finder.delete_file(file_info["path"]):
            result["deleted_files"] += 1
            result["deleted_size"] += file_info["size"]
            current_deleted_size += file_info["size"]
        else:
            result["failed_files"] += 1
            result["skipped_size"] += file_info["size"]
            result["failed_paths"].append(file_info["path"])
    
    return result

def generate_report(scan_result: Dict[str, Any], delete_result: Optional[Dict[str, Any]] = None, 
                   args = None, report_path: str = "") -> str:
    """Generate a detailed report of the operation"""
    from datetime import datetime
    
    # Create report path if specified
    if not report_path:
        report_path = os.getcwd()
    
    # Create filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = os.path.join(report_path, f"temp_cleaner_report_{timestamp}.txt")
    
    # Format bytes to readable format
    def format_size(size_bytes):
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.2f} PB"
    
    # Create report content
    with open(report_file, "w") as f:
        f.write("=== Ultra Temp Cleaner Report ===\n")
        f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        # Write arguments
        if args:
            f.write("=== Scan Parameters ===\n")
            f.write(f"Location: {args.location}\n")
            f.write(f"Minimum age: {args.min_age} days\n")
            f.write(f"File types: {args.file_types}\n")
            f.write(f"Size filter: {args.size_filter}\n")
            f.write(f"Age filter: {args.age_filter}\n")
            if args.exclude_dir:
                f.write(f"Excluded directories: {', '.join(args.exclude_dir)}\n")
            f.write("\n")
        
        # Write scan results
        f.write("=== Scan Results ===\n")
        f.write(f"Total files found: {scan_result.get('total_files', 0)}\n")
        f.write(f"Total size: {format_size(scan_result.get('total_size', 0))}\n")
        f.write(f"Scan duration: {scan_result.get('scan_duration', 0):.2f} seconds\n\n")
        
        # Write type statistics
        f.write("=== File Type Statistics ===\n")
        by_type = scan_result.get('file_stats', {}).get('by_type', {})
        for ext, stats in by_type.items():
            f.write(f"{ext}: {stats.get('size_formatted', '0 B')} ({stats.get('percent', 0):.1f}%)\n")
        f.write("\n")
        
        # Write delete results if available
        if delete_result:
            f.write("=== Deletion Results ===\n")
            f.write(f"Files targeted for deletion: {delete_result.get('total_files', 0)}\n")
            f.write(f"Files successfully deleted: {delete_result.get('deleted_files', 0)}\n")
            f.write(f"Files failed to delete: {delete_result.get('failed_files', 0)}\n")
            f.write(f"Protected files skipped: {delete_result.get('protected_files', 0)}\n")
            f.write(f"Total size deleted: {format_size(delete_result.get('deleted_size', 0))}\n")
            f.write(f"Total size skipped: {format_size(delete_result.get('skipped_size', 0))}\n\n")
            
            # Write failed files
            if delete_result.get('failed_paths', []):
                f.write("=== Failed Deletions ===\n")
                for path in delete_result.get('failed_paths', [])[:50]:  # Limit to 50 files
                    f.write(f"{path}\n")
                if len(delete_result.get('failed_paths', [])) > 50:
                    f.write(f"... and {len(delete_result.get('failed_paths', [])) - 50} more\n")
                f.write("\n")
    
    logging.info(f"Report generated: {report_file}")
    return report_file

def main():
    """Main function"""
    # Setup logging
    setup_logging()
    
    # Parse arguments
    args = parse_arguments()
    
    try:
        # Initialize the scanner
        finder = TempFileFinder()
        
        # Apply settings
        finder.set_min_file_age(args.min_age)
        
        # Add excluded directories
        for exclude_dir in args.exclude_dir:
            finder.add_excluded_dir(exclude_dir)
        
        # Start scanning
        logging.info(f"Starting headless scan: location={args.location}, min_age={args.min_age}")
        finder.scanning = True
        
        start_time = time.time()
        
        if args.location == "temp":
            # Scan temp directories
            temp_dirs = finder.get_system_temp_dirs()
            files = []
            for temp_dir in temp_dirs:
                if finder.scanning:
                    logging.info(f"Scanning temp directory: {temp_dir}")
                    dir_files = finder.scan_for_temp_files(temp_dir)
                    files.extend(dir_files)
        else:
            # Scan all drives
            logging.info("Scanning all drives")
            files = finder.scan_for_temp_files(None)
        
        # Get scan results
        scan_duration = time.time() - start_time
        scan_result = finder.get_stats_summary()
        scan_result['scan_duration'] = scan_duration
        
        # Filter files
        filtered_files = filter_files(files, args)
        
        # Log results
        logging.info(f"Scan completed in {scan_duration:.2f} seconds")
        logging.info(f"Total files found: {len(files)}")
        logging.info(f"Files after filtering: {len(filtered_files)}")
        logging.info(f"Total size: {finder.format_size(finder.total_size)}")
        
        # Delete files if auto-delete is enabled
        delete_result = None
        if args.auto_delete and filtered_files:
            logging.info(f"Auto-deleting {len(filtered_files)} files")
            delete_result = delete_files(filtered_files, finder, args.max_delete_size)
            
            # Log delete results
            logging.info(f"Deleted {delete_result['deleted_files']} of {delete_result['total_files']} files")
            logging.info(f"Deleted size: {finder.format_size(delete_result['deleted_size'])}")
            if delete_result['failed_files'] > 0:
                logging.warning(f"Failed to delete {delete_result['failed_files']} files")
        
        # Generate report if requested
        if args.report:
            report_path = args.report_path if args.report_path else os.getcwd()
            report_file = generate_report(scan_result, delete_result, args, report_path)
            print(f"Report generated: {report_file}")
        
        # Return success
        return 0
        
    except KeyboardInterrupt:
        logging.info("Operation interrupted by user")
        return 1
    except Exception as e:
        logging.error(f"Error in headless cleaner: {e}", exc_info=True)
        return 1
    finally:
        if 'finder' in locals():
            finder.scanning = False

if __name__ == "__main__":
    sys.exit(main()) 