import pytest
from pathlib import Path

@pytest.mark.skip(reason="Manual frontend tests require user interaction")
def test_frontend_queue_manual(mock_server, test_dir, test_images):
    """Test the frontend queue functionality with manual input."""
    print("Testing frontend queue functionality (manual mode)...")
    
    # Set the current folder
    mock_server.app.state.current_folder = test_dir
    
    # First, open a folder to initialize the queue
    response = mock_server.post("/images", json={"folder_path": str(test_dir)})
    assert response.status_code == 200
    print("Folder opened successfully")
    
    print("\nManual Testing Steps:")
    print("1. Open your browser and navigate to http://localhost:8000")
    print("2. Enter the folder path:", test_dir)
    print("3. Click 'Open Folder' and verify images load")
    print("4. Test legacy processing:")
    print("   - Click 'Process All'")
    print("   - Verify processing starts")
    print("   - Click 'Stop Processing'")
    print("5. Test queue processing:")
    print("   - Enable 'Use Queue Processing'")
    print("   - Click 'Process All'")
    print("   - Verify queue status updates")
    print("   - Click 'Stop Processing'")
    print("6. Test queue controls:")
    print("   - Click 'Clear Queue'")
    print("   - Verify queue is empty")
    
    # Get queue status
    response = mock_server.get("/queue/status", params={"detailed": "true"})
    assert response.status_code == 200
    print("\nCurrent Queue Status:", response.json())
    
    print("\nPlease follow the steps above and verify functionality manually.") 
