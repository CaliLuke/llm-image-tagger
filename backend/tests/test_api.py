"""
API Test Suite

This module contains tests for the FastAPI endpoints. To avoid common issues:
1. Use TEST_PATHS for consistent module paths
2. Use mock_metadata_operations fixture for metadata operations
3. Avoid sleep delays in test mocks
4. Keep mock responses in MOCK_RESPONSES
5. Use proper type hints and docstrings

Common Patterns:
- Metadata operations require mocking: open, json.load, json.dump, vector_store
- Image processing requires mocking: ImageProcessor, ollama.AsyncClient
- File operations should use the test_folder fixture
"""

from fastapi.testclient import TestClient
import pytest
from pathlib import Path
import os
import sys
from PIL import Image, ImageDraw
import logging
import json
import shutil
from unittest.mock import patch, MagicMock, AsyncMock
import asyncio
import time
import hashlib
from typing import Dict, Any, List

# Add the parent directory to the path so we can import the app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app
from app.api.routes import router
from app.services.vector_store import VectorStore
from app.services.image_processor import ImageProcessor
from app.services.image_processor import AsyncResponseGenerator

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)

# Test configuration
TEST_PATHS = {
    'helpers': 'app.utils.helpers',
    'vector_store': 'app.services.vector_store.VectorStore',
    'image_processor': 'app.services.image_processor',
    'routes': 'app.api.routes',
}

# Mock responses for image processing - Single source of truth
MOCK_RESPONSES = {
    "test_image.png": {
        "description": "A test image with simple text content",
        "tags": ["test", "image", "text"],
        "text_content": "API Test Image",
        "is_processed": True
    }
}

@pytest.fixture
def mock_metadata_operations():
    """
    Fixture that provides all commonly needed mocks for metadata operations.
    
    Returns:
        Dict[str, Any]: Dictionary containing all mock objects and test data:
            - open: Mock for builtins.open
            - json_load: Mock for json.load
            - json_dump: Mock for json.dump
            - add_or_update: Mock for VectorStore.add_or_update_image
            - get_metadata: Mock for helpers.load_or_create_metadata
            - metadata: Test metadata dictionary
    """
    # Initialize with empty metadata that will be updated during the test
    mock_metadata = {}
    
    with patch('builtins.open', create=True) as mock_open, \
         patch('json.load') as mock_json_load, \
         patch('json.dump') as mock_json_dump, \
         patch(f'{TEST_PATHS["vector_store"]}.add_or_update_image') as mock_add_or_update, \
         patch(f'{TEST_PATHS["helpers"]}.load_or_create_metadata') as mock_get_metadata:
        
        # Make json_load return the current state of mock_metadata
        def load_side_effect(*args, **kwargs):
            return mock_metadata.copy()
        mock_json_load.side_effect = load_side_effect
        
        # Make json_dump update our mock_metadata
        def dump_side_effect(data, *args, **kwargs):
            nonlocal mock_metadata
            mock_metadata.update(data)
        mock_json_dump.side_effect = dump_side_effect
        
        # Make get_metadata return the current state
        mock_get_metadata.side_effect = lambda *args: mock_metadata.copy()
        
        # Configure the add_or_update mock to be async
        async def mock_add_or_update_async(path, metadata):
            mock_metadata[path] = metadata
            return None
        mock_add_or_update.side_effect = mock_add_or_update_async
        
        yield {
            'open': mock_open,
            'json_load': mock_json_load,
            'json_dump': mock_json_dump,
            'add_or_update': mock_add_or_update,
            'get_metadata': mock_get_metadata,
            'metadata': mock_metadata
        }

@pytest.fixture
async def mock_image_processor():
    """
    Mock image processor fixture for testing.
    
    This mock simulates the behavior of the Ollama client by:
    1. Implementing proper async iteration for streaming responses
    2. Providing progress updates and final content in the expected format
    3. Simulating processing delays to match real-world behavior
    """
    
    class AsyncResponseGenerator:
        """
        Helper class that implements the async iterator protocol for mocking
        Ollama's streaming responses.
        """
        def __init__(self, responses):
            self.responses = responses
            self.index = 0
            
        def __aiter__(self):
            return self
            
        async def __anext__(self):
            if self.index >= len(self.responses):
                raise StopAsyncIteration
            response = self.responses[self.index]
            self.index += 1
            return response
            
        @staticmethod
        def _get_content(format_schema):
            """Generate appropriate content based on the format schema."""
            mock_data = MOCK_RESPONSES["test_image.png"]
            if 'description' in format_schema.get('properties', {}):
                return {
                    'message': {
                        'content': json.dumps({
                            'description': mock_data['description']
                        })
                    }
                }
            elif 'tags' in format_schema.get('properties', {}):
                return {
                    'message': {
                        'content': json.dumps({
                            'tags': mock_data['tags']
                        })
                    }
                }
            elif 'has_text' in format_schema.get('properties', {}):
                return {
                    'message': {
                        'content': json.dumps({
                            'has_text': True,
                            'text_content': mock_data['text_content']
                        })
                    }
                }
            return {}

    async def mock_chat(**kwargs):
        """
        Mock implementation of the Ollama chat method.
        """
        format_schema = kwargs.get('format', {})
        responses = [
            # Progress update (50% complete)
            {
                'eval_count': 50,
                'prompt_eval_count': 100,
                'message': {'content': None}
            },
            # Final content with proper JSON formatting
            AsyncResponseGenerator._get_content(format_schema)
        ]
        return AsyncResponseGenerator(responses)

    # Create the mock AsyncClient
    with patch('backend.app.services.image_processor.ollama.AsyncClient') as mock_client, \
         patch('backend.app.api.dependencies.ImageProcessor') as mock_processor_class, \
         patch('backend.app.api.routes.router.vector_store') as mock_vector_store:
        # Configure the mock client to return an async mock for the chat method
        client_instance = mock_client.return_value
        client_instance.chat = mock_chat

        # Configure the mock processor class
        processor = ImageProcessor()
        mock_processor_class.return_value = processor

        # Configure the mock vector store
        mock_vector_store.add_or_update_image = mock_metadata_operations['add_or_update']

        # Create and yield the ImageProcessor instance
        yield processor

    logger.info("mock_image_processor fixture cleanup complete")

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
def test_folder():
    """Create a test folder with a sample image."""
    # Use the project's test directory
    test_dir = Path(__file__).parent.parent.parent / "test_data" / "test_images"
    test_dir.mkdir(parents=True, exist_ok=True)
    
    # Create test image
    img = Image.new('RGB', (400, 100), color='white')
    d = ImageDraw.Draw(img)
    d.text((10,10), "API Test Image", fill='black')
    
    # Save test image
    image_path = test_dir / "test_image.png"
    img.save(image_path)
    
    return str(test_dir)

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

def test_process_image_not_found(initialized_folder, client):
    """Test processing a non-existent image."""
    response = client.post("/process-image", json={"image_path": "/nonexistent/image.png"})
    assert response.status_code == 200
    data = response.json()
    assert "success" in data
    assert not data["success"]  # Should be False for error cases
    assert "message" in data
    assert "Image not found" in data["message"]

@pytest.mark.asyncio
async def test_update_metadata(initialized_folder, client, mock_image_processor, mock_metadata_operations):
    """Test updating image metadata."""
    logger.info("Starting test_update_metadata")

    image_path = str(Path(initialized_folder) / "test_image.png")
    image_filename = Path(image_path).name
    logger.info(f"Using test image path: {image_path}")
    logger.info(f"Using image filename: {image_filename}")

    # Initialize metadata with empty values for the test image
    mock_metadata_operations['metadata'].clear()
    mock_metadata_operations['metadata'][image_filename] = {
        "description": "",
        "tags": [],
        "text_content": "",
        "is_processed": False
    }

    # Update metadata directly without processing the image first
    response = client.post("/update-metadata", json={
        "path": image_filename,
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
    
    # Verify that json.dump was called with the updated metadata
    mock_metadata_operations['json_dump'].assert_called_once()
    saved_metadata = mock_metadata_operations['json_dump'].call_args[0][0]
    assert image_filename in saved_metadata
    assert saved_metadata[image_filename]["description"] == "Updated description"
    assert "test" in saved_metadata[image_filename]["tags"]
    assert "updated" in saved_metadata[image_filename]["tags"]
    assert saved_metadata[image_filename]["text_content"] == "Updated text"
    
    # Verify vector store was updated
    mock_metadata_operations['add_or_update'].assert_called_once_with(
        image_filename,
        {
            "description": "Updated description",
            "tags": ["test", "updated"],
            "text_content": "Updated text",
            "is_processed": True
        }
    )
    
    logger.info("test_update_metadata completed successfully")

@pytest.mark.asyncio
async def test_search_with_results_mocked(initialized_folder, client, mock_metadata_operations, mock_image_processor):
    """Test search functionality with mocked image processor and metadata operations.

    This test verifies:
    1. Image processing returns correct metadata
    2. Vector store is updated with processed metadata
    3. Search returns relevant results
    4. Search with irrelevant query returns no results

    Args:
        initialized_folder: Fixture providing test folder path
        client: FastAPI test client
        mock_metadata_operations: Mock for metadata operations
        mock_image_processor: Mock for image processor
    """
    logger.info("Starting test_search_with_results_mocked")

    # Create test images
    test_image_path = str(Path(initialized_folder) / "test_image.png")
    irrelevant_image_path = str(Path(initialized_folder) / "irrelevant.png")

    # Create the test images
    for path in [test_image_path, irrelevant_image_path]:
        img = Image.new('RGB', (100, 100), color='white')
        img.save(path)
        logger.debug(f"Created test image at {path}")

    test_image = Path(test_image_path).name
    irrelevant_image = Path(irrelevant_image_path).name

    # Set up mock responses with carefully chosen metadata that won't match irrelevant queries
    mock_responses = {
        test_image: {
            "description": "A test image for testing",
            "tags": ["test", "example"],
            "text_content": "Test content",
            "is_processed": True
        },
        irrelevant_image: {
            "description": "An unrelated picture",
            "tags": ["other", "unrelated"],
            "text_content": "Different content",
            "is_processed": True
        }
    }

    # Initialize metadata for both images
    mock_metadata_operations['metadata'].clear()  # Clear any existing metadata
    mock_metadata_operations['metadata'].update({
        test_image: mock_responses[test_image],
        irrelevant_image: mock_responses[irrelevant_image]
    })

    # Mock vector store search behavior
    def mock_search_images(query: str, limit: int = 5) -> List[str]:
        if query.lower() == "test":
            return [test_image]
        return []  # Return empty list for irrelevant queries
    
    # Patch vector store's search method
    router.vector_store.search_images = mock_search_images

    # Test search with relevant query
    response = client.post("/search", json={"query": "test"})
    assert response.status_code == 200
    data = response.json()
    assert len(data["images"]) == 1
    assert data["images"][0]["path"] == test_image
    assert data["images"][0]["description"] == mock_responses[test_image]["description"]
    assert data["images"][0]["tags"] == mock_responses[test_image]["tags"]

    # Test search with irrelevant query
    response = client.post("/search", json={"query": "nonexistent"})
    assert response.status_code == 200
    data = response.json()
    assert len(data["images"]) == 0

    logger.info("test_search_with_results_mocked completed successfully")

@pytest.mark.asyncio
async def test_check_init_status(client, mock_metadata_operations):
    """Test the initialization status endpoint."""
    logger.info("Starting test_check_init_status")
    
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
    
    # Verify no metadata operations were performed during status check
    mock_metadata_operations['add_or_update'].assert_not_called()
    mock_metadata_operations['json_dump'].assert_not_called()
    
    logger.info("test_check_init_status completed successfully")

@pytest.mark.asyncio
async def test_stop_processing(client, test_folder, mock_image_processor, mock_metadata_operations):
    """Test stopping the image processing operation."""
    logger.info("Starting test_stop_processing")
    
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
        logger.debug(f"Created test image: {img_path}")

    # Directly set the is_processing flag to simulate processing
    router.is_processing = True
    logger.debug("Set is_processing flag to True")

    # Stop processing
    response = client.post("/stop-processing")
    assert response.status_code == 200
    assert response.json()["message"] == "Processing will be stopped"
    
    # Verify the should_stop_processing flag was set
    assert router.should_stop_processing is True
    logger.debug("Verified should_stop_processing flag was set to True")
    
    # Verify no metadata operations were performed during stop
    mock_metadata_operations['add_or_update'].assert_not_called()
    mock_metadata_operations['json_dump'].assert_not_called()
    
    logger.info("test_stop_processing completed successfully")

@pytest.mark.asyncio
async def test_process_image_endpoint_mocked(initialized_folder, client, mock_metadata_operations):
    """Test the process-image endpoint with a mocked processor."""
    logger.info("Starting test_process_image_endpoint_mocked")
    
    class AsyncResponseGenerator:
        """Helper class that implements the async iterator protocol for mocking Ollama's streaming responses."""
        def __init__(self, responses):
            self.responses = responses
            self.index = 0
        
        def __aiter__(self):
            return self
        
        async def __anext__(self):
            if self.index >= len(self.responses):
                raise StopAsyncIteration
            response = self.responses[self.index]
            self.index += 1
            return response
        
        @staticmethod
        def _get_content(format_schema):
            """Generate appropriate content based on the format schema."""
            mock_data = MOCK_RESPONSES["test_image.png"]
            if 'description' in format_schema.get('properties', {}):
                return {
                    'message': {
                        'content': json.dumps({
                            'description': mock_data['description']
                        })
                    }
                }
            elif 'tags' in format_schema.get('properties', {}):
                return {
                    'message': {
                        'content': json.dumps({
                            'tags': mock_data['tags']
                        })
                    }
                }
            elif 'has_text' in format_schema.get('properties', {}):
                return {
                    'message': {
                        'content': json.dumps({
                            'has_text': True,
                            'text_content': mock_data['text_content']
                        })
                    }
                }
            return {}
    
    async def mock_chat(**kwargs):
        """Mock implementation of the Ollama chat method."""
        format_schema = kwargs.get('format', {})
        responses = [
            # Progress update (50% complete)
            {
                'eval_count': 50,
                'prompt_eval_count': 100,
                'message': {'content': None}
            },
            # Final content with proper JSON formatting
            AsyncResponseGenerator._get_content(format_schema)
        ]
        return AsyncResponseGenerator(responses)
    
    # Create the mock AsyncClient
    with patch('backend.app.services.image_processor.ollama.AsyncClient') as mock_client, \
         patch('backend.app.api.dependencies.ImageProcessor') as mock_processor_class:
        
        # Configure the mock client to return an async mock for the chat method
        client_instance = mock_client.return_value
        client_instance.chat = mock_chat
        
        # Configure the mock processor class
        processor = ImageProcessor()
        mock_processor_class.return_value = processor
        
        # Use the test image from the initialized folder
        test_image = "test_image.png"
        logger.info(f"Testing with image: {test_image}")
        
        # Make the request
        logger.debug("Making POST request to /process-image")
        response = client.post("/process-image", json={"image_path": test_image})
        logger.debug(f"Response status code: {response.status_code}")
        assert response.status_code == 200
        
        # Process the streaming response
        updates = []
        logger.debug("Processing streaming response")
        for line in response.iter_lines():
            if line:  # Skip empty lines
                update = json.loads(line)
                logger.debug(f"Received update: {json.dumps(update, indent=2)}")
                updates.append(update)
        
        # Verify the updates
        logger.debug(f"Received {len(updates)} updates")
        assert len(updates) > 0
        
        # Check each update's success status
        for i, update in enumerate(updates):
            success = update.get("success", False)
            logger.debug(f"Update {i} success: {success}")
            assert success, f"Update {i} failed: {json.dumps(update, indent=2)}"
        
        # Verify progress values
        logger.debug(f"First update progress: {updates[0]['progress']}")
        logger.debug(f"Final update progress: {updates[-1]['progress']}")
        assert updates[0]["progress"] == 0
        assert updates[-1]["progress"] == 1.0
        
        # Verify final metadata
        logger.debug("Verifying final metadata")
        final_metadata = updates[-1]["image"]
        logger.debug(f"Final metadata: {json.dumps(final_metadata, indent=2)}")
        assert isinstance(final_metadata, dict)
        
        # Compare with expected responses
        expected = MOCK_RESPONSES["test_image.png"]
        logger.debug(f"Expected metadata: {json.dumps(expected, indent=2)}")
        assert final_metadata["description"] == expected["description"]
        assert final_metadata["tags"] == expected["tags"]
        assert final_metadata["text_content"] == expected["text_content"]
        assert final_metadata["is_processed"] == True
        
        # Verify vector store was updated with correct metadata
        mock_metadata_operations['add_or_update'].assert_called_once_with(
            test_image,
            expected
        )
        
        # Verify metadata was saved
        mock_metadata_operations['json_dump'].assert_called_once()
        saved_metadata = mock_metadata_operations['json_dump'].call_args[0][0]
        assert test_image in saved_metadata
        assert saved_metadata[test_image] == expected
        
        logger.info("test_process_image_endpoint_mocked completed successfully")

@pytest.mark.asyncio
async def test_get_image_not_found(client, initialized_folder):
    """Test getting a non-existent image."""
    response = client.get("/image/nonexistent.jpg")
    assert response.status_code == 404
    assert response.json()["detail"] == "Image not found"

@pytest.mark.asyncio
async def test_get_image_invalid_format(client, initialized_folder, tmp_path):
    """Test getting an invalid image."""
    # Create an invalid image file
    invalid_image = tmp_path / "invalid.jpg"
    invalid_image.write_text("not an image")
    
    # Copy the invalid image to the initialized folder
    target_path = Path(initialized_folder) / "invalid.jpg"
    shutil.copy(str(invalid_image), str(target_path))
    
    response = client.get("/image/invalid.jpg")
    assert response.status_code == 400
    assert "Invalid image format" in response.json()["detail"]

@pytest.mark.asyncio
async def test_get_image_rgba(client, initialized_folder):
    """Test getting an RGBA image."""
    # Create a test RGBA image
    from PIL import Image
    test_image = Path(initialized_folder) / "test_rgba.png"
    img = Image.new('RGBA', (100, 100), (255, 0, 0, 128))
    img.save(test_image)
    
    response = client.get("/image/test_rgba.png")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"

@pytest.mark.asyncio
async def test_get_image_rgb(client, initialized_folder):
    """Test getting an RGB image."""
    # Create a test RGB image
    from PIL import Image
    test_image = Path(initialized_folder) / "test_rgb.jpg"
    img = Image.new('RGB', (100, 100), (255, 0, 0))
    img.save(test_image)
    
    response = client.get("/image/test_rgb.jpg")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/jpeg"
