import pytest
from pathlib import Path

def test_process_image_paths(mock_server, test_dir, test_images):
    """Test both legacy and queue-based image processing paths."""
    print("Testing image processing paths...")
    
    # Set the current folder
    mock_server.app.state.current_folder = test_dir
    
    # First, open a folder to initialize the system
    response = mock_server.post("/images", json={"folder_path": str(test_dir)})
    assert response.status_code == 200
    print("Folder opened successfully")
    
    # Test legacy path
    print("\nTesting legacy path...")
    response = mock_server.post("/process-image", json={"image_path": test_images[0]})
    assert response.status_code == 200
    print("Legacy path response:", response.json())
    
    # Test queue-based path
    print("\nTesting queue-based path...")
    response = mock_server.post("/process-image", json={"image_path": test_images[0]}, params={"use_queue": "true"})
    assert response.status_code == 200
    print("Queue-based path response:", response.json())
    
    # Get queue status
    response = mock_server.get("/queue/status", params={"detailed": "true"})
    assert response.status_code == 200
    print("Queue status:", response.json())
    
    # Get final queue status
    response = mock_server.get("/queue/status", params={"detailed": "true"})
    assert response.status_code == 200
    print("Final queue status:", response.json())
    
    print("All process_image path tests passed!") 
