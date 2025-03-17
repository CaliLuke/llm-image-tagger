import requests
import time
import sys
import os
import json

# Add the parent directory to the path so we can import the backend modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Base URL for the API
BASE_URL = "http://localhost:8000"

def test_frontend_queue_manual():
    """Provide manual testing instructions for the frontend queue functionality."""
    print("Manual Testing Instructions for Frontend Queue Functionality")
    print("==========================================================")
    print("\n1. First, let's initialize the application with a folder:")
    
    folder_path = input("\nEnter folder path (or press Enter to use '/Volumes/screenshots/Datapad'): ")
    if not folder_path:
        folder_path = "/Volumes/screenshots/Datapad"
    
    print(f"\nOpening folder: {folder_path}")
    response = requests.post(f"{BASE_URL}/images", json={"folder_path": folder_path})
    
    if response.status_code != 200:
        print(f"Error opening folder: {response.status_code} - {response.text}")
        return
    
    print("Folder opened successfully")
    
    print("\n2. Manual Testing Steps:")
    print("   a. Open your browser and navigate to http://localhost:8000")
    print("   b. Enter the folder path and click 'Open Folder'")
    print("   c. Verify that images are loaded successfully")
    
    print("\n3. Test Legacy Processing:")
    print("   a. Click the 'Process All' button")
    print("   b. Verify that processing starts (progress bar appears)")
    print("   c. Click 'Stop Processing' after a few seconds")
    print("   d. Verify that processing stops")
    
    print("\n4. Test Queue-Based Processing:")
    print("   a. Check the 'Use Queue Processing (Experimental)' checkbox at the bottom of the page")
    print("   b. Verify that the Queue Status panel appears")
    print("   c. Click the 'Process All' button")
    print("   d. Verify that processing starts (progress bar appears and Queue Status updates)")
    print("   e. Click 'Stop Processing' after a few seconds")
    print("   f. Verify that processing stops")
    
    print("\n5. Test Direct Queue Controls:")
    print("   a. Click 'Clear Queue' in the Queue Status panel")
    print("   b. Verify that the queue is cleared (Queue Length should be 0)")
    print("   c. Click 'Refresh' in the Queue Status panel")
    print("   d. Verify that the Queue Status updates")
    
    print("\n6. Test Individual Image Processing:")
    print("   a. Click on an image to open the image details")
    print("   b. Click 'Process Image'")
    print("   c. Verify that the image is processed (with queue if checkbox is checked)")
    print("   d. Close the image details")
    
    print("\nCurrent Queue Status:")
    response = requests.get(f"{BASE_URL}/queue/status?detailed=true")
    if response.status_code == 200:
        queue_status = response.json()
        print(json.dumps(queue_status, indent=2))
    
    print("\nAfter completing all steps, please confirm that all functionality works as expected.")
    print("If any issues are found, please report them.")

if __name__ == "__main__":
    test_frontend_queue_manual() 
