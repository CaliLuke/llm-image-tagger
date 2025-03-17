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
    
    # In debug mode, run tests first (unless --skip-tests is specified)
    if args.debug and not args.skip_tests:
        if not run_tests():
            sys.exit(1)
    
    # Set environment variables
    os.environ["API_HOST"] = args.host
    os.environ["API_PORT"] = str(args.port)
    
    # Start the server
    print(f"Starting server at http://{args.host}:{args.port}")
    server_process = subprocess.Popen([
        sys.executable, "-m", "uvicorn", "main:app", 
        "--host", args.host, 
        "--port", str(args.port),
        "--reload" if args.debug else ""
    ])
    
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
