import pytest
from pathlib import Path

def test_queue_endpoints(mock_server, test_dir, test_images):
    """Test the queue-related endpoints."""
    print("Testing queue endpoints...")
    
    # Set the current folder
    mock_server.app.state.current_folder = test_dir
    
    # First, open a folder to initialize the queue
    response = mock_server.post("/images", json={"folder_path": str(test_dir)})
    assert response.status_code == 200
    print("Folder opened successfully")
    
    # Test adding an image to the queue
    test_image = test_images[0]  # Use the first test image
    response = mock_server.post("/queue/add", json={"image_path": test_image})
    assert response.status_code == 200
    print("Image added to queue successfully")
    print(f"Response: {response.json()}")
    
    # Test getting queue status
    response = mock_server.get("/queue/status")
    assert response.status_code == 200
    print("Queue status retrieved successfully")
    print(f"Response: {response.json()}")
    
    # Test getting detailed queue status
    response = mock_server.get("/queue/status?detailed=true")
    assert response.status_code == 200
    print("Detailed queue status retrieved successfully")
    print(f"Response: {response.json()}")
    
    # Test starting queue processing
    response = mock_server.post("/queue/start")
    assert response.status_code == 200
    print("Queue processing started successfully")
    print(f"Response: {response.json()}")
    
    # Test stopping queue processing
    response = mock_server.post("/queue/stop")
    assert response.status_code == 200
    print("Queue processing stopped successfully")
    print(f"Response: {response.json()}")
    
    # Test clearing the queue
    response = mock_server.post("/queue/clear")
    assert response.status_code == 200
    print("Queue cleared successfully")
    print(f"Response: {response.json()}")
    
    print("All queue endpoint tests passed!") 
