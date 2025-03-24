#!/usr/bin/env python3
"""
Utility script to clean up the app.log file.

This script removes log entries from previous days, keeping only the current day's logs.
It can be run manually to clean up the app.log file if it has grown too large.

Usage:
    python clean_logs.py

Note:
    This application only uses app.log for logging. No other log files should be created.
"""

import os
import sys
import datetime
import argparse

def cleanup_old_logs(log_file_path):
    """
    Remove log entries from previous days, keeping only the current day's logs.
    
    Args:
        log_file_path: Path to the log file
    """
    today = datetime.datetime.now().strftime('%Y-%m-%d')
    
    if not os.path.exists(log_file_path):
        print(f"Log file not found: {log_file_path}")
        return False
        
    try:
        print(f"Cleaning up logs in: {log_file_path}")
        with open(log_file_path, 'r') as f:
            log_content = f.readlines()
        
        original_size = len(log_content)
        
        # Filter logs to keep only current day's entries
        current_day_logs = []
        for line in log_content:
            # Only check lines that might contain a timestamp
            if len(line) > 10 and '-' in line[:10]:
                try:
                    # Extract the date part (YYYY-MM-DD)
                    log_date = line[:10]
                    if log_date == today:
                        current_day_logs.append(line)
                except (ValueError, IndexError):
                    # If the line doesn't have a proper date format, keep it for safety
                    current_day_logs.append(line)
            else:
                # Keep lines without timestamps (could be stack traces, etc.)
                current_day_logs.append(line)
        
        # Write back only today's logs
        with open(log_file_path, 'w') as f:
            f.writelines(current_day_logs)
            
        new_size = len(current_day_logs)
        lines_removed = original_size - new_size
        
        print(f"Log cleanup complete: {lines_removed} lines removed from {log_file_path}")
        return True
    except Exception as e:
        print(f"Error during log cleanup: {str(e)}")
        return False

def main():
    # Get the project root directory
    project_root = os.path.dirname(os.path.abspath(__file__))
    
    # Create logs directory if it doesn't exist
    logs_dir = os.path.join(project_root, 'logs')
    os.makedirs(logs_dir, exist_ok=True)
    
    # The only log file used by the application
    app_log_path = os.path.join(logs_dir, 'app.log')
    
    if cleanup_old_logs(app_log_path):
        print("Successfully cleaned app.log")
    else:
        print("Failed to clean app.log")

if __name__ == "__main__":
    main() 
