import pytest
from pathlib import Path

def test_queue_processing(mock_server, test_dir, test_images):
    """Test the queue processing endpoint."""
    print("Testing queue processing...")
    
    # Set the current folder
    mock_server.app.state.current_folder = test_dir
    
    # First, open a folder to initialize the queue
    response = mock_server.post("/images", json={"folder_path": str(test_dir)})
    assert response.status_code == 200
    
    print("Folder opened successfully")
    
    # Add multiple images to the queue
    for image_path in test_images:
        response = mock_server.post("/queue/add", json={"image_path": image_path})
        assert response.status_code == 200
        print(f"Image {image_path} added to queue successfully")
    
    # Get queue status before processing
    response = mock_server.get("/queue/status?detailed=true")
    assert response.status_code == 200
    print("Queue status before processing:", response.json())
    
    # Start processing the queue
    response = mock_server.post("/queue/process")
    assert response.status_code == 200
    print("Queue processing started successfully")
    
    # Get queue status during processing
    response = mock_server.get("/queue/status?detailed=true")
    assert response.status_code == 200
    print("Queue status during processing:", response.json())
    
    # Stop processing
    response = mock_server.post("/queue/stop")
    assert response.status_code == 200
    print("Queue processing stopped successfully")
    
    # Get final queue status
    response = mock_server.get("/queue/status?detailed=true")
    assert response.status_code == 200
    print("Final queue status:", response.json())
    
    # Clear the queue
    response = mock_server.post("/queue/clear")
    assert response.status_code == 200
    print("Queue cleared successfully")
    
    print("All queue processing tests passed!") 
