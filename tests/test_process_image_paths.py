import requests
import time
import sys
import os

# Add the parent directory to the path so we can import the backend modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Base URL for the API
BASE_URL = "http://localhost:8000"

def test_process_image_paths():
    """Test both the legacy and queue-based processing paths."""
    print("Testing process_image paths...")
    
    # First, open a folder to initialize the queue
    folder_path = "/Volumes/screenshots/Datapad"  # Use the same folder path as in the logs
    response = requests.post(f"{BASE_URL}/images", json={"folder_path": folder_path})
    
    if response.status_code != 200:
        print(f"Error opening folder: {response.status_code} - {response.text}")
        return
    
    print("Folder opened successfully")
    
    # Test legacy path
    print("\nTesting legacy path...")
    image_path = "2014-05-16_16-28-16.png"  # Use an image from the logs
    
    response = requests.post(f"{BASE_URL}/process-image", json={"image_path": image_path})
    
    if response.status_code != 200:
        print(f"Error processing image with legacy path: {response.status_code} - {response.text}")
        return
    
    print("Legacy path response:")
    print(f"Response: {response.json()}")
    
    # Wait for processing to complete or stop
    time.sleep(2)
    
    # Test queue-based path
    print("\nTesting queue-based path...")
    
    response = requests.post(f"{BASE_URL}/process-image?use_queue=true", json={"image_path": image_path})
    
    if response.status_code != 200:
        print(f"Error processing image with queue-based path: {response.status_code} - {response.text}")
        return
    
    print("Queue-based path response:")
    print(f"Response: {response.json()}")
    
    # Get queue status
    response = requests.get(f"{BASE_URL}/queue/status?detailed=true")
    
    if response.status_code != 200:
        print(f"Error getting queue status: {response.status_code} - {response.text}")
        return
    
    print("Queue status:")
    print(f"Response: {response.json()}")
    
    # Wait for processing to complete or stop
    time.sleep(2)
    
    # Get final queue status
    response = requests.get(f"{BASE_URL}/queue/status?detailed=true")
    
    if response.status_code != 200:
        print(f"Error getting queue status: {response.status_code} - {response.text}")
        return
    
    print("Final queue status:")
    print(f"Response: {response.json()}")
    
    print("All process_image path tests passed!")

if __name__ == "__main__":
    test_process_image_paths() 
