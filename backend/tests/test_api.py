from fastapi.testclient import TestClient
import pytest
from pathlib import Path
import os
import sys
from PIL import Image, ImageDraw
import logging
import json
import shutil
from unittest.mock import patch, MagicMock
import asyncio

# Add the parent directory to the path so we can import the app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app
from app.api.routes import router
from app.services.vector_store import VectorStore
from app.services.image_processor import ImageProcessor

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)

# Mock responses for image processing
MOCK_DESCRIPTION = "This is a test image with some text"
MOCK_TAGS = ["test", "image", "text"]
MOCK_TEXT = "API Test Image"

@pytest.fixture
def mock_image_processor():
    """Mock the image processor to avoid actual LLM calls."""
    with patch('app.api.routes.ImageProcessor') as mock:
        processor_instance = MagicMock()
        async def mock_process_image(image_path):
            # Simulate longer processing time to allow stop_processing to work
            await asyncio.sleep(1.0)  # Increased to 1 second
            return {
                "description": MOCK_DESCRIPTION,
                "tags": MOCK_TAGS,
                "text_content": MOCK_TEXT,
                "is_processed": True
            }
        processor_instance.process_image.side_effect = mock_process_image
        mock.return_value = processor_instance
        yield mock

@pytest.fixture(autouse=True)
def reset_app_state():
    """Reset app state before and after each test."""
    # Reset before test
    router.current_folder = None
    router.vector_store = None
    router.is_processing = False
    router.should_stop_processing = False
    
    yield
    
    # Reset after test
    router.current_folder = None
    router.vector_store = None
    router.is_processing = False
    router.should_stop_processing = False
    
    # Clean up again
    if hasattr(app, 'current_folder'):
        logger.debug(f"  current_folder value: {app.current_folder}")
        delattr(app, 'current_folder')
    if hasattr(app, 'vector_store'):
        delattr(app, 'vector_store')
    
    # Verify clean state again
    assert not hasattr(app, 'current_folder'), "Failed to clean current_folder"
    assert not hasattr(app, 'vector_store'), "Failed to clean vector_store"

@pytest.fixture
def client():
    """Create a fresh test client for each test."""
    from main import app
    # Create a new FastAPI app instance for each test
    if hasattr(app, 'current_folder'):
        delattr(app, 'current_folder')
    if hasattr(app, 'vector_store'):
        delattr(app, 'vector_store')
    return TestClient(app)

def test_read_root(client):
    """Test that the root endpoint returns the index.html file."""
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]

def test_folder_not_found(client):
    """Test that the images endpoint returns 404 for a non-existent folder."""
    response = client.post("/images", json={"folder_path": "/path/that/does/not/exist"})
    assert response.status_code == 404
    assert "Folder not found" in response.json()["detail"]

def test_search_no_folder(client):
    """Test that the search endpoint returns 400 when no folder is selected."""
    response = client.post("/search", json={"query": "test"})
    assert response.status_code == 400
    assert "No folder selected" in response.json()["detail"]

@pytest.fixture
def test_folder(tmp_path):
    """Create a test folder with a sample image."""
    # Create test image
    img = Image.new('RGB', (400, 100), color='white')
    d = ImageDraw.Draw(img)
    d.text((10,10), "API Test Image", fill='black')
    
    # Create folder structure
    image_folder = tmp_path / "test_images"
    image_folder.mkdir()
    image_path = image_folder / "test_image.png"
    img.save(image_path)
    
    return str(image_folder)

@pytest.fixture
def initialized_folder(test_folder, client):
    """Initialize the folder for testing."""
    from main import app
    logger.debug("INITIALIZED_FOLDER - Before post request:")
    logger.debug(f"  has current_folder: {hasattr(app, 'current_folder')}")
    response = client.post("/images", json={"folder_path": test_folder})
    assert response.status_code == 200
    logger.debug("INITIALIZED_FOLDER - After post request:")
    logger.debug(f"  has current_folder: {hasattr(app, 'current_folder')}")
    if hasattr(app, 'current_folder'):
        logger.debug(f"  current_folder value: {app.current_folder}")
    yield test_folder
    # Clean up after test
    logger.debug("INITIALIZED_FOLDER - Cleanup:")
    logger.debug(f"  has current_folder: {hasattr(app, 'current_folder')}")
    if hasattr(app, 'current_folder'):
        logger.debug(f"  current_folder value: {app.current_folder}")
        delattr(app, 'current_folder')
    if hasattr(app, 'vector_store'):
        delattr(app, 'vector_store')

def test_process_image_endpoint(initialized_folder, client):
    """Test the process-image endpoint."""
    image_path = str(Path(initialized_folder) / "test_image.png")
    response = client.post("/process-image", json={"image_path": image_path})
    assert response.status_code == 200
    
    data = response.json()
    assert "success" in data
    assert data["success"] == True
    assert "image" in data
    image_data = data["image"]
    assert "description" in image_data
    assert "tags" in image_data
    assert "text_content" in image_data
    assert isinstance(image_data["tags"], list)

def test_process_image_not_found(initialized_folder, client):
    """Test processing a non-existent image."""
    response = client.post("/process-image", json={"image_path": "/nonexistent/image.png"})
    assert response.status_code == 200  # API returns 200 with error in response
    data = response.json()
    assert "success" in data
    assert not data["success"]  # Should be False for error cases
    assert "message" in data
    assert "Image not found" in data["message"]

def test_update_metadata(initialized_folder, client):
    """Test updating image metadata."""
    image_path = str(Path(initialized_folder) / "test_image.png")
    
    # First process the image
    process_response = client.post("/process-image", json={"image_path": image_path})
    assert process_response.status_code == 200
    
    # Then update its metadata
    response = client.post("/update-metadata", json={
        "path": image_path,
        "description": "Updated description",
        "tags": ["test", "updated"],
        "text_content": "Updated text"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["success"] == True
    assert "image" in data
    assert data["image"]["description"] == "Updated description"
    assert "test" in data["image"]["tags"]
    assert "updated" in data["image"]["tags"]
    assert data["image"]["text_content"] == "Updated text"

def test_search_with_results(initialized_folder, client):
    """Test search functionality with actual results."""
    # First process the image
    image_path = str(Path(initialized_folder) / "test_image.png")
    process_response = client.post("/process-image", json={"image_path": image_path})
    assert process_response.status_code == 200
    
    # Search with a relevant query
    response = client.post("/search", json={"query": "API Test Image"})
    assert response.status_code == 200
    
    data = response.json()
    assert "images" in data
    assert len(data["images"]) > 0
    
    # Search with an irrelevant query
    response = client.post("/search", json={"query": "something completely unrelated"})
    assert response.status_code == 200
    assert len(response.json()["images"]) == 0

def test_check_init_status(client):
    """Test the initialization status endpoint."""
    from main import app
    logger.debug("CHECK_INIT_STATUS - Before request:")
    logger.debug(f"  has current_folder: {hasattr(app, 'current_folder')}")
    if hasattr(app, 'current_folder'):
        logger.debug(f"  current_folder value: {app.current_folder}")
    
    response = client.get("/check-init-status")
    assert response.status_code == 200
    data = response.json()
    
    logger.debug("CHECK_INIT_STATUS - After request:")
    logger.debug(f"  has current_folder: {hasattr(app, 'current_folder')}")
    if hasattr(app, 'current_folder'):
        logger.debug(f"  current_folder value: {app.current_folder}")
    logger.debug(f"  response data: {data}")
    
    assert "initialized" in data
    assert isinstance(data["initialized"], bool)
    assert "message" in data
    # When no folder is selected, initialized should be False
    assert data["initialized"] is False
    assert data["message"] == "No folder selected"

@pytest.mark.asyncio
async def test_stop_processing(client, test_folder, mock_image_processor):
    """Test stopping the image processing operation."""
    # Import router to directly access state
    from app.api.routes import router
    
    # First check when no processing is happening
    response = client.post("/stop-processing")
    assert response.status_code == 200
    assert response.json()["message"] == "No processing operation in progress"

    # Start processing and then stop it
    response = client.post("/images", json={"folder_path": test_folder})
    assert response.status_code == 200

    # Reset processing state
    response = client.post("/reset-processing-state")
    assert response.status_code == 200
    assert response.json()["message"] == "Processing state reset"

    # Create multiple test images to process
    for i in range(3):
        img = Image.new('RGB', (100, 100), color='white')
        img_path = Path(test_folder) / f"test_image_{i}.png"
        img.save(img_path)

    # Directly set the is_processing flag to simulate processing
    router.is_processing = True

    # Stop processing
    response = client.post("/stop-processing")
    assert response.status_code == 200
    assert response.json()["message"] == "Processing will be stopped"
    
    # Verify the should_stop_processing flag was set
    assert router.should_stop_processing is True

@pytest.mark.asyncio
async def test_process_image_endpoint_mocked(initialized_folder, client, mock_image_processor):
    """Test the process-image endpoint with mocked processor."""
    image_path = str(Path(initialized_folder) / "test_image.png")
    response = client.post("/process-image", json={"image_path": "test_image.png"})
    assert response.status_code == 200
    
    # Initial response should indicate processing started
    data = response.json()
    assert data["success"] is True
    assert "image" in data
    assert data["message"] == "Image processing started"
    
    # Wait for processing to complete (mock sleeps for 1.0s)
    await asyncio.sleep(1.2)
    
    # Now check the metadata file to verify processing completed
    metadata_file = Path(initialized_folder) / "image_metadata.json"
    with open(metadata_file, 'r') as f:
        metadata = json.load(f)
    
    # Verify the metadata contains our mock data
    assert "test_image.png" in metadata
    assert metadata["test_image.png"]["description"] == MOCK_DESCRIPTION
    assert metadata["test_image.png"]["tags"] == MOCK_TAGS
    assert metadata["test_image.png"]["text_content"] == MOCK_TEXT

@pytest.mark.asyncio
async def test_search_with_results_mocked(initialized_folder, client, mock_image_processor):
    """Test search functionality with mocked processor."""
    # First process the image
    image_path = str(Path(initialized_folder) / "test_image.png")
    process_response = client.post("/process-image", json={"image_path": "test_image.png"})
    assert process_response.status_code == 200
    
    # Wait for processing to complete (mock sleeps for 1.0s)
    await asyncio.sleep(1.2)
    
    # Search with a relevant query
    response = client.post("/search", json={"query": "test image"})
    assert response.status_code == 200
    
    data = response.json()
    assert "images" in data
    assert len(data["images"]) > 0
    
    # Search with an irrelevant query
    response = client.post("/search", json={"query": "something completely unrelated"})
    assert response.status_code == 200
    assert len(response.json()["images"]) == 0
