#!/usr/bin/env python3
"""
Run script for the Image Tagger application.
This script starts the backend server and opens the web interface.
"""

import os
import sys
import webbrowser
import time
import subprocess
import argparse
import socket
import psutil

def check_existing_instance(host, port):
    """Check if another instance is already running on the specified host and port."""
    try:
        # Try to create a socket with the same host and port
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((host, port))
            s.close()
            return None
    except socket.error as e:
        # Socket is in use, try to find the process
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if proc.info['cmdline'] and 'uvicorn' in ' '.join(proc.info['cmdline']):
                    return proc.info['pid']
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return True  # Port is in use but couldn't find the process

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Run the Image Tagger application")
    parser.add_argument("--host", default="127.0.0.1", help="Host to run the server on")
    parser.add_argument("--port", type=int, default=8000, help="Port to run the server on")
    parser.add_argument("--no-browser", action="store_true", help="Don't open the browser automatically")
    parser.add_argument("--debug", action="store_true", help="Run in debug mode with tests")
    parser.add_argument("--skip-tests", action="store_true", help="Skip running tests even in debug mode")
    return parser.parse_args()

def run_tests():
    """Run the test suite."""
    print("\nRunning test suite...")
    result = subprocess.run([sys.executable, "-m", "pytest", "-v"], text=True)
    if result.returncode != 0:
        print("Tests failed! Please fix the failing tests before continuing.")
        return False
    return True

def main():
    """Main function to run the application."""
    args = parse_args()
    
    # Change to the project root directory
    project_root = os.path.dirname(os.path.abspath(__file__))
    os.chdir(project_root)
    
    # Check for existing instance
    existing_pid = check_existing_instance(args.host, args.port)
    if existing_pid:
        if isinstance(existing_pid, int):
            print(f"Error: Another instance is already running (PID: {existing_pid})")
            print("Please stop the existing instance first.")
        else:
            print(f"Error: Port {args.port} is already in use.")
            print("Please stop the process using this port or specify a different port with --port.")
        sys.exit(1)
    
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
    
    server_process = subprocess.Popen(cmd)
    
    # Open the browser
    if not args.no_browser:
        time.sleep(2)  # Wait for the server to start
        webbrowser.open(f"http://{args.host}:{args.port}")
    
    try:
        # Keep the server running until Ctrl+C
        server_process.wait()
    except KeyboardInterrupt:
        print("Shutting down server...")
        server_process.terminate()
        server_process.wait()

if __name__ == "__main__":
    main() 
