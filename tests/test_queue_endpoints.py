import requests
import time
import sys
import os

# Add the parent directory to the path so we can import the backend modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Base URL for the API
BASE_URL = "http://localhost:8000"

def test_queue_endpoints():
    """Test the queue endpoints."""
    print("Testing queue endpoints...")
    
    # First, open a folder to initialize the queue
    folder_path = "/Volumes/screenshots/Datapad"  # Use the same folder path as in the logs
    response = requests.post(f"{BASE_URL}/images", json={"folder_path": folder_path})
    
    if response.status_code != 200:
        print(f"Error opening folder: {response.status_code} - {response.text}")
        return
    
    print("Folder opened successfully")
    
    # Test adding an image to the queue
    image_path = "2014-05-16_16-28-16.png"  # Use an image from the logs
    response = requests.post(f"{BASE_URL}/queue/add", json={"image_path": image_path})
    
    if response.status_code != 200:
        print(f"Error adding image to queue: {response.status_code} - {response.text}")
        return
    
    print("Image added to queue successfully")
    print(f"Response: {response.json()}")
    
    # Test getting queue status
    response = requests.get(f"{BASE_URL}/queue/status")
    
    if response.status_code != 200:
        print(f"Error getting queue status: {response.status_code} - {response.text}")
        return
    
    print("Queue status retrieved successfully")
    print(f"Response: {response.json()}")
    
    # Test getting detailed queue status
    response = requests.get(f"{BASE_URL}/queue/status?detailed=true")
    
    if response.status_code != 200:
        print(f"Error getting detailed queue status: {response.status_code} - {response.text}")
        return
    
    print("Detailed queue status retrieved successfully")
    print(f"Response: {response.json()}")
    
    # Test starting queue processing
    response = requests.post(f"{BASE_URL}/queue/start")
    
    if response.status_code != 200:
        print(f"Error starting queue processing: {response.status_code} - {response.text}")
        return
    
    print("Queue processing started successfully")
    print(f"Response: {response.json()}")
    
    # Wait a moment to let processing start
    time.sleep(1)
    
    # Test stopping queue processing
    response = requests.post(f"{BASE_URL}/queue/stop")
    
    if response.status_code != 200:
        print(f"Error stopping queue processing: {response.status_code} - {response.text}")
        return
    
    print("Queue processing stopped successfully")
    print(f"Response: {response.json()}")
    
    # Test clearing the queue
    response = requests.post(f"{BASE_URL}/queue/clear")
    
    if response.status_code != 200:
        print(f"Error clearing queue: {response.status_code} - {response.text}")
        return
    
    print("Queue cleared successfully")
    print(f"Response: {response.json()}")
    
    print("All queue endpoint tests passed!")

if __name__ == "__main__":
    test_queue_endpoints() 
