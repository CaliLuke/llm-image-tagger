import requests
import time
import sys
import os

# Add the parent directory to the path so we can import the backend modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Base URL for the API
BASE_URL = "http://localhost:8000"

def test_queue_processing():
    """Test the queue processing endpoint."""
    print("Testing queue processing...")
    
    # First, open a folder to initialize the queue
    folder_path = "/Volumes/screenshots/Datapad"  # Use the same folder path as in the logs
    response = requests.post(f"{BASE_URL}/images", json={"folder_path": folder_path})
    
    if response.status_code != 200:
        print(f"Error opening folder: {response.status_code} - {response.text}")
        return
    
    print("Folder opened successfully")
    
    # Add multiple images to the queue
    image_paths = ["2014-05-16_16-28-16.png", "2014-05-14_15-34-42.png"]
    
    for image_path in image_paths:
        response = requests.post(f"{BASE_URL}/queue/add", json={"image_path": image_path})
        
        if response.status_code != 200:
            print(f"Error adding image to queue: {response.status_code} - {response.text}")
            return
        
        print(f"Image {image_path} added to queue successfully")
    
    # Get queue status before processing
    response = requests.get(f"{BASE_URL}/queue/status?detailed=true")
    
    if response.status_code != 200:
        print(f"Error getting queue status: {response.status_code} - {response.text}")
        return
    
    print("Queue status before processing:")
    print(f"Response: {response.json()}")
    
    # Start processing the queue
    response = requests.post(f"{BASE_URL}/queue/process")
    
    if response.status_code != 200:
        print(f"Error processing queue: {response.status_code} - {response.text}")
        return
    
    print("Queue processing started successfully")
    print(f"Response: {response.json()}")
    
    # Wait for processing to start
    time.sleep(1)
    
    # Get queue status during processing
    response = requests.get(f"{BASE_URL}/queue/status?detailed=true")
    
    if response.status_code != 200:
        print(f"Error getting queue status: {response.status_code} - {response.text}")
        return
    
    print("Queue status during processing:")
    print(f"Response: {response.json()}")
    
    # Wait for processing to complete (or stop after 10 seconds)
    max_wait = 10
    wait_time = 0
    
    while wait_time < max_wait:
        response = requests.get(f"{BASE_URL}/queue/status")
        
        if response.status_code != 200:
            print(f"Error getting queue status: {response.status_code} - {response.text}")
            break
        
        status = response.json()
        
        if not status["is_processing"]:
            print("Queue processing completed")
            break
        
        print(f"Queue is still processing... (waited {wait_time}s)")
        time.sleep(1)
        wait_time += 1
    
    # Get final queue status
    response = requests.get(f"{BASE_URL}/queue/status?detailed=true")
    
    if response.status_code != 200:
        print(f"Error getting queue status: {response.status_code} - {response.text}")
        return
    
    print("Final queue status:")
    print(f"Response: {response.json()}")
    
    # Test stopping processing (add more images and stop)
    for image_path in image_paths:
        response = requests.post(f"{BASE_URL}/queue/add", json={"image_path": image_path})
        
        if response.status_code != 200:
            print(f"Error adding image to queue: {response.status_code} - {response.text}")
            return
        
        print(f"Image {image_path} added to queue successfully")
    
    # Start processing the queue
    response = requests.post(f"{BASE_URL}/queue/process")
    
    if response.status_code != 200:
        print(f"Error processing queue: {response.status_code} - {response.text}")
        return
    
    print("Queue processing started successfully")
    
    # Wait for processing to start
    time.sleep(1)
    
    # Stop processing
    response = requests.post(f"{BASE_URL}/queue/stop")
    
    if response.status_code != 200:
        print(f"Error stopping queue processing: {response.status_code} - {response.text}")
        return
    
    print("Queue processing stopped successfully")
    print(f"Response: {response.json()}")
    
    # Wait for processing to stop
    time.sleep(2)
    
    # Get final queue status
    response = requests.get(f"{BASE_URL}/queue/status?detailed=true")
    
    if response.status_code != 200:
        print(f"Error getting queue status: {response.status_code} - {response.text}")
        return
    
    print("Final queue status after stopping:")
    print(f"Response: {response.json()}")
    
    # Clear the queue
    response = requests.post(f"{BASE_URL}/queue/clear")
    
    if response.status_code != 200:
        print(f"Error clearing queue: {response.status_code} - {response.text}")
        return
    
    print("Queue cleared successfully")
    
    print("All queue processing tests passed!")

if __name__ == "__main__":
    test_queue_processing() 
