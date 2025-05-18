import os
import json
import time
import logging
import threading
import datetime
from typing import Dict, List, Any, Optional, Tuple, Union
import subprocess
import sys

class ScheduledCleaner:
    """Handles scheduled cleaning operations"""
    
    def __init__(self, config_file: str = 'schedule_config.json'):
        self.config_file = config_file
        self.schedules = []
        self.running = False
        self.scheduler_thread = None
        
        # Initialize logging
        logging.basicConfig(
            filename='temp_file_finder.log',
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            force=True
        )
        
        # Load existing schedules if any
        self.load_schedules()
    
    def load_schedules(self) -> None:
        """Load schedules from the config file"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    self.schedules = json.load(f)
                logging.info(f"Loaded {len(self.schedules)} schedules from config")
            else:
                self.schedules = []
                logging.info("No schedule config found, starting with empty schedule")
        except Exception as e:
            logging.error(f"Error loading schedules: {e}")
            self.schedules = []
    
    def save_schedules(self) -> None:
        """Save schedules to the config file"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.schedules, f, indent=2)
            logging.info(f"Saved {len(self.schedules)} schedules to config")
        except Exception as e:
            logging.error(f"Error saving schedules: {e}")
    
    def add_schedule(self, name: str, frequency: str, time: str, options: Dict[str, Any]) -> bool:
        """Add a new cleaning schedule
        
        Args:
            name: Descriptive name for the schedule
            frequency: daily, weekly, monthly
            time: Time in 24h format HH:MM
            options: Dict with cleaning options (scan_location, min_age, auto_delete, etc)
        
        Returns:
            True if schedule was added successfully
        """
        try:
            # Validate inputs
            if not self._validate_schedule_inputs(frequency, time, options):
                return False
            
            # Create schedule object
            schedule = {
                'id': self._generate_id(),
                'name': name,
                'frequency': frequency,
                'time': time,
                'options': options,
                'enabled': True,
                'last_run': None,
                'next_run': self._calculate_next_run(frequency, time)
            }
            
            # Add to schedules list
            self.schedules.append(schedule)
            
            # Save schedules
            self.save_schedules()
            
            # If scheduler is running, no need to restart
            if not self.running and schedule['enabled']:
                self.start_scheduler()
                
            return True
            
        except Exception as e:
            logging.error(f"Error adding schedule: {e}")
            return False
    
    def remove_schedule(self, schedule_id: str) -> bool:
        """Remove a schedule by ID"""
        try:
            self.schedules = [s for s in self.schedules if s['id'] != schedule_id]
            self.save_schedules()
            return True
        except Exception as e:
            logging.error(f"Error removing schedule: {e}")
            return False
    
    def update_schedule(self, schedule_id: str, **kwargs) -> bool:
        """Update an existing schedule"""
        try:
            for i, schedule in enumerate(self.schedules):
                if schedule['id'] == schedule_id:
                    # Update provided fields
                    for key, value in kwargs.items():
                        if key in schedule:
                            schedule[key] = value
                    
                    # Recalculate next run if time or frequency changed
                    if 'time' in kwargs or 'frequency' in kwargs:
                        schedule['next_run'] = self._calculate_next_run(
                            schedule['frequency'], schedule['time']
                        )
                    
                    self.schedules[i] = schedule
                    self.save_schedules()
                    return True
            
            return False
        except Exception as e:
            logging.error(f"Error updating schedule: {e}")
            return False
    
    def enable_schedule(self, schedule_id: str, enabled: bool = True) -> bool:
        """Enable or disable a schedule"""
        return self.update_schedule(schedule_id, enabled=enabled)
    
    def get_schedule(self, schedule_id: str) -> Optional[Dict[str, Any]]:
        """Get a schedule by ID"""
        for schedule in self.schedules:
            if schedule['id'] == schedule_id:
                return schedule
        return None
    
    def get_all_schedules(self) -> List[Dict[str, Any]]:
        """Get all schedules"""
        return self.schedules
    
    def start_scheduler(self) -> bool:
        """Start the scheduler thread"""
        if self.running:
            return True
        
        try:
            self.running = True
            self.scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
            self.scheduler_thread.start()
            logging.info("Scheduler started")
            return True
        except Exception as e:
            logging.error(f"Error starting scheduler: {e}")
            self.running = False
            return False
    
    def stop_scheduler(self) -> bool:
        """Stop the scheduler thread"""
        if not self.running:
            return True
        
        try:
            self.running = False
            if self.scheduler_thread:
                self.scheduler_thread.join(timeout=1.0)
            logging.info("Scheduler stopped")
            return True
        except Exception as e:
            logging.error(f"Error stopping scheduler: {e}")
            return False
    
    def _scheduler_loop(self) -> None:
        """Main scheduler loop"""
        while self.running:
            try:
                now = datetime.datetime.now()
                
                # Check each schedule
                for i, schedule in enumerate(self.schedules):
                    if not schedule['enabled']:
                        continue
                    
                    # Parse next run time
                    next_run = datetime.datetime.fromisoformat(schedule['next_run'])
                    
                    # If it's time to run
                    if now >= next_run:
                        logging.info(f"Running scheduled clean: {schedule['name']}")
                        
                        # Run the clean operation
                        success = self._run_clean_operation(schedule)
                        
                        # Update last run and next run
                        self.schedules[i]['last_run'] = now.isoformat()
                        self.schedules[i]['next_run'] = self._calculate_next_run(
                            schedule['frequency'], schedule['time']
                        )
                        
                        # Save schedules
                        self.save_schedules()
                
                # Sleep for a minute before checking again
                time.sleep(60)
                
            except Exception as e:
                logging.error(f"Error in scheduler loop: {e}")
                time.sleep(60)  # Sleep on error to avoid tight loop
    
    def _run_clean_operation(self, schedule: Dict[str, Any]) -> bool:
        """Run a cleaning operation based on schedule"""
        try:
            options = schedule['options']
            
            # Determine how to run the clean operation
            if options.get('headless', True):
                # Run in headless mode via command line
                return self._run_headless_clean(options)
            else:
                # Launch UI with schedule parameters
                return self._run_ui_clean(options)
                
        except Exception as e:
            logging.error(f"Error running clean operation: {e}")
            return False
    
    def _run_headless_clean(self, options: Dict[str, Any]) -> bool:
        """Run a headless clean operation"""
        try:
            # Prepare command line arguments
            cmd = [sys.executable, 'headless_cleaner.py']
            
            # Add options
            if 'scan_location' in options:
                cmd.extend(['--location', options['scan_location']])
            
            if 'min_age' in options:
                cmd.extend(['--min-age', str(options['min_age'])])
            
            if 'auto_delete' in options and options['auto_delete']:
                cmd.append('--auto-delete')
            
            if 'file_types' in options:
                cmd.extend(['--file-types', options['file_types']])
            
            # Run the command
            logging.info(f"Running headless clean: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                logging.info(f"Headless clean completed: {result.stdout.strip()}")
                return True
            else:
                logging.error(f"Headless clean failed: {result.stderr.strip()}")
                return False
                
        except Exception as e:
            logging.error(f"Error running headless clean: {e}")
            return False
    
    def _run_ui_clean(self, options: Dict[str, Any]) -> bool:
        """Launch UI with schedule parameters"""
        try:
            # Prepare command line arguments
            cmd = [sys.executable, 'ui.py']
            
            # Add schedule flag
            cmd.append('--scheduled')
            
            # Add options
            for key, value in options.items():
                if isinstance(value, bool) and value:
                    cmd.append(f"--{key.replace('_', '-')}")
                else:
                    cmd.append(f"--{key.replace('_', '-')}={value}")
            
            # Run the command
            logging.info(f"Running UI clean: {' '.join(cmd)}")
            subprocess.Popen(cmd)  # Don't wait for completion
            return True
                
        except Exception as e:
            logging.error(f"Error running UI clean: {e}")
            return False
    
    def _validate_schedule_inputs(self, frequency: str, time: str, options: Dict[str, Any]) -> bool:
        """Validate schedule inputs"""
        # Validate frequency
        if frequency not in ['daily', 'weekly', 'monthly']:
            logging.error(f"Invalid frequency: {frequency}")
            return False
        
        # Validate time
        try:
            hour, minute = map(int, time.split(':'))
            if hour < 0 or hour > 23 or minute < 0 or minute > 59:
                logging.error(f"Invalid time: {time}")
                return False
        except:
            logging.error(f"Invalid time format: {time}")
            return False
        
        # Validate options
        required_options = ['scan_location']
        for option in required_options:
            if option not in options:
                logging.error(f"Missing required option: {option}")
                return False
        
        return True
    
    def _generate_id(self) -> str:
        """Generate a unique ID for a schedule"""
        return datetime.datetime.now().strftime('%Y%m%d%H%M%S')
    
    def _calculate_next_run(self, frequency: str, time_str: str) -> str:
        """Calculate the next run time based on frequency and time"""
        now = datetime.datetime.now()
        hour, minute = map(int, time_str.split(':'))
        
        # Start with today at the specified time
        next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        
        # If that time has already passed today, start from tomorrow
        if next_run <= now:
            next_run += datetime.timedelta(days=1)
        
        # Adjust based on frequency
        if frequency == 'weekly':
            # Run on the same day next week
            days_ahead = 7
            next_run += datetime.timedelta(days=days_ahead)
        elif frequency == 'monthly':
            # Run on the same day next month
            if next_run.month == 12:
                next_month = 1
                next_year = next_run.year + 1
            else:
                next_month = next_run.month + 1
                next_year = next_run.year
                
            # Handle month length differences
            day = min(next_run.day, [31, 29 if self._is_leap_year(next_year) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][next_month-1])
            next_run = next_run.replace(year=next_year, month=next_month, day=day)
        
        return next_run.isoformat()
    
    def _is_leap_year(self, year: int) -> bool:
        """Check if a year is a leap year"""
        return (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0)


if __name__ == "__main__":
    # Test the scheduler
    scheduler = ScheduledCleaner()
    
    # Add a test schedule
    scheduler.add_schedule(
        name="Daily Temp Clean",
        frequency="daily",
        time="03:00",
        options={
            "scan_location": "temp",
            "min_age": 7,
            "auto_delete": True,
            "headless": True
        }
    )
    
    # Start the scheduler
    scheduler.start_scheduler()
    
    # Keep running for testing
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        scheduler.stop_scheduler()
        print("Scheduler stopped") 