import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from pathlib import Path
import sys
import os
import tempfile
import shutil
import logging
from backend.app.services.processing_queue import ProcessingQueue
from backend.app.services.queue_processor import QueueProcessor
from backend.app.services.vector_store import VectorStore
from backend.app.api.routes import router
from backend.app.models.schemas import ImageDescription, ImageTags, ImageText

# Set up logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)

# Add the backend directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../backend')))

from main import app

@pytest.fixture(autouse=True)
def setup_test_environment():
    """Set up test environment before each test."""
    logger.info("Setting up test environment")
    
    # Create a temporary directory for vector store
    temp_dir = tempfile.mkdtemp()
    logger.debug(f"Created temporary directory at {temp_dir}")
    
    # Create data directory
    data_dir = Path(temp_dir) / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    logger.debug(f"Created data directory at {data_dir}")
    
    # Create vector store directory
    vector_dir = data_dir / "vectordb"
    vector_dir.mkdir(parents=True, exist_ok=True)
    logger.debug(f"Created vector store directory at {vector_dir}")
    
    # Initialize router state with test configuration
    logger.debug("Initializing router state")
    router.vector_store = VectorStore(persist_directory=str(vector_dir))
    router.processing_queue = ProcessingQueue()
    router.queue_persistence = None  # No persistence needed for tests
    
    yield
    
    # Clean up
    logger.info("Cleaning up test environment")
    shutil.rmtree(temp_dir)
    logger.debug(f"Removed temporary directory at {temp_dir}")
    
    # Reset router state
    logger.debug("Resetting router state")
    router.vector_store = None
    router.processing_queue = None
    router.queue_persistence = None
    router.current_folder = None
    logger.info("Test environment cleanup complete")

@pytest.fixture
def test_folder(tmp_path):
    """Create a temporary test folder with test images."""
    test_dir = tmp_path / "test_images"
    test_dir.mkdir()
    
    # Create test images
    test_images = ["test_image_1.png", "test_image_2.png"]
    for img_name in test_images:
        (test_dir / img_name).touch()
    
    return test_dir

@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)

@pytest.fixture
def test_images():
    """Return a list of test image names."""
    return ["test_image_1.png", "test_image_2.png"]

@pytest.fixture
def path_config(tmp_path):
    """Create a PathConfig instance for testing."""
    logger.info("Setting up PathConfig fixture")
    from backend.app.core.config import PathConfig
    
    # Create test directories
    project_root = tmp_path / "test_project"
    data_dir = project_root / "data"
    temp_dir = project_root / "temp"
    
    # Create directories
    project_root.mkdir(parents=True)
    data_dir.mkdir()
    temp_dir.mkdir()
    logger.debug(f"Created test directories: project_root={project_root}, data_dir={data_dir}, temp_dir={temp_dir}")
    
    # Initialize PathConfig with test directories
    config = PathConfig()
    config.project_root = project_root
    config.data_dir = data_dir
    config.temp_dir = temp_dir
    
    # Add test directories to safe_dirs
    config.safe_dirs = [
        project_root,
        data_dir,
        temp_dir,
        Path("/tmp"),
        Path("/private/tmp"),
        Path.home(),
        Path.cwd(),
        tmp_path  # Add the pytest temporary directory
    ]
    logger.debug("Configured safe directories")
    
    return config

@pytest.fixture
def mock_server(monkeypatch):
    """Create a mock server for testing."""
    # Mock the ImageProcessor
    mock_processor = MagicMock()
    mock_processor._get_description = AsyncMock(return_value=ImageDescription(description="Test description"))
    mock_processor._get_tags = AsyncMock(return_value=ImageTags(tags=["test", "image"]))
    mock_processor._get_text_content = AsyncMock(return_value=ImageText(has_text=True, text_content="Test text content"))
    mock_processor.process_image = AsyncMock(return_value={
        'description': 'Test description',
        'tags': ['test', 'image'],
        'text_content': 'Test text content',
        'is_processed': True
    })
    
    # Mock the QueueProcessor
    mock_queue_processor = MagicMock(spec=QueueProcessor)
    mock_queue_processor.process_queue = AsyncMock()
    mock_queue_processor.stop_processing = MagicMock()
    mock_queue_processor.is_processing = False
    
    # Create a mock app state
    mock_app = MagicMock()
    mock_app.state = MagicMock()
    mock_app.state.current_folder = None
    
    # Create the mock server object
    mock_server = MagicMock()
    mock_server.app = mock_app
    mock_server.processor = mock_processor
    mock_server.queue_processor = mock_queue_processor
    
    # Configure mock responses
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "description": "Test description",
        "tags": ["test", "image"],
        "has_text": True,
        "text_content": "Test text content"
    }
    mock_server.post.return_value = mock_response
    mock_server.get.return_value = mock_response
    
    # Patch the ImageProcessor and QueueProcessor
    monkeypatch.setattr('backend.app.services.image_processor.ImageProcessor', lambda *args, **kwargs: mock_processor)
    monkeypatch.setattr('backend.app.services.queue_processor.QueueProcessor', lambda *args, **kwargs: mock_queue_processor)
    
    return mock_server

@pytest.fixture
def test_dir(tmp_path):
    """Create a temporary test directory."""
    test_dir = tmp_path / "test_dir"
    test_dir.mkdir()
    return test_dir 
