#!/usr/bin/env python3
"""
Run script for the Image Tagger application.
This script starts the backend server and opens the web interface.
"""

import os
import sys
import argparse
import subprocess
import time
import signal
import psutil
import atexit
import logging
import datetime
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import webbrowser
import socket

# Add the backend directory to the Python path
backend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend")
sys.path.insert(0, backend_dir)

# Try to import from backend, but handle case where it's run directly
try:
    from backend.app.core.logging import cleanup_old_logs
except ImportError:
    # Define cleanup function here if import fails
    def cleanup_old_logs(log_file_path):
        """
        Remove log entries from previous days, keeping only the current day's logs.
        
        Args:
            log_file_path: Path to the log file
        """
        today = datetime.datetime.now().strftime('%Y-%m-%d')
        
        if not os.path.exists(log_file_path):
            return  # No log file exists yet
            
        try:
            with open(log_file_path, 'r') as f:
                log_content = f.readlines()
            
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
                
            print(f"Log cleanup complete. Removed entries older than {today}")
        except Exception as e:
            print(f"Error during log cleanup: {str(e)}")

# Setup logging
logs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
os.makedirs(logs_dir, exist_ok=True)

# Clean up the app.log file
app_log_path = os.path.join(logs_dir, 'app.log')
cleanup_old_logs(app_log_path)

# Configure logging to stdout only - all file logging should go through the central logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def check_existing_instance(host, port):
    """Check if another instance is already running on the specified host and port."""
    try:
        # Try to create a socket with the same host and port
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)  # Set a timeout for the connection attempt
            try:
                s.connect((host, port))
                # Port is in use, try to find the process
                for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                    try:
                        if proc.info['cmdline'] and 'uvicorn' in ' '.join(proc.info['cmdline']) and f"--port {port}" in ' '.join(proc.info['cmdline']):
                            return proc.info['pid']
                    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                        continue
                # Port is in use but not by our application
                return False
            except ConnectionRefusedError:
                # Port is not in use
                return None
            except socket.timeout:
                # Connection attempt timed out, port might be in a weird state
                return False
    except socket.error as e:
        if e.errno == 48:  # Address already in use
            # Try to find the process using the port
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    if proc.info['cmdline'] and 'uvicorn' in ' '.join(proc.info['cmdline']) and f"--port {port}" in ' '.join(proc.info['cmdline']):
                        return proc.info['pid']
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
            # Port is in use but not by our application
            return False
        logger.error(f"Socket error: {e}")
        return False

def run_tests():
    """Run tests to verify the application is working."""
    print("Running tests...")
    result = subprocess.run([sys.executable, "-m", "pytest", "-v"])
    return result.returncode == 0

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Run the Image Tagger application")
    parser.add_argument("--host", default="127.0.0.1", help="Host to run the server on")
    parser.add_argument("--port", type=int, default=8000, help="Port to run the server on")
    parser.add_argument("--no-browser", action="store_true", help="Don't open the browser automatically")
    parser.add_argument("--debug", action="store_true", help="Run in debug mode with tests")
    parser.add_argument("--skip-tests", action="store_true", help="Skip running tests even in debug mode")
    parser.add_argument("--force", action="store_true", help="Force start even if port appears to be in use")
    return parser.parse_args()

def main():
    """Main function to run the application."""
    args = parse_args()
    
    # Change to the project root directory
    project_root = os.path.dirname(os.path.abspath(__file__))
    os.chdir(project_root)
    
    # Check for existing instance
    if not args.force:
        existing_pid = check_existing_instance(args.host, args.port)
        if existing_pid:
            if isinstance(existing_pid, int):
                print(f"Error: Another instance is already running (PID: {existing_pid})")
                print("Use one of the following options:")
                print("1. Stop the existing instance with: kill", existing_pid)
                print(f"2. Use a different port with: --port <port>")
                print("3. Use --force to try to start anyway")
            else:
                print(f"Error: Port {args.port} is already in use by another application.")
                print("Use one of the following options:")
                print(f"1. Use a different port with: --port <port>")
                print("2. Use --force to try to start anyway")
            sys.exit(1)
    else:
        print("Force flag set, skipping instance check.")
    
    # In debug mode, run tests first (unless --skip-tests is specified)
    if args.debug and not args.skip_tests:
        if not run_tests():
            sys.exit(1)
    
    # Set environment variables
    os.environ["API_HOST"] = args.host
    os.environ["API_PORT"] = str(args.port)
    
    # Start the server
    print(f"Starting server at http://{args.host}:{args.port}")
    cmd = [
        sys.executable, "-m", "uvicorn", "main:app", 
        "--host", args.host, 
        "--port", str(args.port)
    ]
    if args.debug:
        cmd.append("--reload")
    
    server_process = None
    try:
        server_process = subprocess.Popen(cmd)
        
        # Open the browser
        if not args.no_browser:
            time.sleep(2)  # Wait for the server to start
            webbrowser.open(f"http://{args.host}:{args.port}")
        
        # Keep the server running until Ctrl+C
        server_process.wait()
    except KeyboardInterrupt:
        print("\nShutting down server...")
    except Exception as e:
        print(f"\nError running server: {e}")
    finally:
        if server_process:
            try:
                server_process.terminate()
                server_process.wait(timeout=5)  # Wait up to 5 seconds for graceful shutdown
            except subprocess.TimeoutExpired:
                print("Server not responding to termination, forcing shutdown...")
                server_process.kill()  # Force kill if not responding
                server_process.wait()
            print("Server stopped.")

if __name__ == "__main__":
    main() 
