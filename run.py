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
    return parser.parse_args()

def main():
    """Main function to run the application."""
    args = parse_args()
    
    # Change to the backend directory
    os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend"))
    
    # Set environment variables
    os.environ["API_HOST"] = args.host
    os.environ["API_PORT"] = str(args.port)
    
    # Start the server
    print(f"Starting server at http://{args.host}:{args.port}")
    server_process = subprocess.Popen([
        sys.executable, "-m", "uvicorn", "main:app", 
        "--host", args.host, 
        "--port", str(args.port)
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
