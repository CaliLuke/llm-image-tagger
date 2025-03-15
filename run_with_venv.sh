#!/bin/bash

# Script to run the Image Tagger application with the virtual environment

# Determine the script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Activate the virtual environment
echo "Activating virtual environment..."
source "$SCRIPT_DIR/venv/bin/activate" || {
    echo "Failed to activate virtual environment. Make sure it exists and is properly set up."
    echo "You can create it with: python -m venv venv && venv/bin/pip install -r backend/requirements.txt"
    exit 1
}

# Parse command line arguments
HOST="127.0.0.1"
PORT="8000"
NO_BROWSER=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --host=*)
            HOST="${1#*=}"
            shift
            ;;
        --port=*)
            PORT="${1#*=}"
            shift
            ;;
        --no-browser)
            NO_BROWSER=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--host=HOST] [--port=PORT] [--no-browser]"
            exit 1
            ;;
    esac
done

# Set environment variables
export API_HOST="$HOST"
export API_PORT="$PORT"

# Change to the backend directory
cd "$SCRIPT_DIR/backend" || {
    echo "Failed to change to backend directory."
    exit 1
}

# Run the application
echo "Starting server at http://$HOST:$PORT"
if [ "$NO_BROWSER" = true ]; then
    python main.py
else
    # Wait for the server to start before opening the browser
    python main.py &
    SERVER_PID=$!
    
    # Wait a moment for the server to start
    sleep 2
    
    # Open the browser
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        open "http://$HOST:$PORT"
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux
        xdg-open "http://$HOST:$PORT" || {
            echo "Failed to open browser. You can access the application at http://$HOST:$PORT"
        }
    else
        # Windows or other
        echo "Please open your browser and navigate to http://$HOST:$PORT"
    fi
    
    # Wait for the server process to finish
    wait $SERVER_PID
fi

# Deactivate the virtual environment when done
deactivate 
