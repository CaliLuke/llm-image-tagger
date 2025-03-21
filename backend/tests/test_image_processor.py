import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from pathlib import Path
import json
import logging
import tempfile
import shutil
import os

from backend.app.services.image_processor import ImageProcessor
from backend.app.models.schemas import ImageDescription, ImageTags, ImageText
from backend.app.services.vector_store import VectorStore

# Set up logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)

@pytest.fixture
def image_processor():
    """Create an ImageProcessor instance for testing."""
    logger.debug("Setting up image_processor fixture")
    try:
        with patch('backend.app.services.image_processor.ollama') as mock_ollama:
            logger.debug("Mocking Ollama client")
            
            # Setup mock responses for different query types
            async def mock_chat(**kwargs):
                format_props = kwargs.get('format', {}).get('properties', {})
                
                if 'description' in format_props:
                    return {'message': {'content': {'description': 'A test description'}}}
                elif 'tags' in format_props:
                    return {'message': {'content': {'tags': ['test', 'image']}}}
                elif 'has_text' in format_props:
                    return {'message': {'content': {'has_text': False, 'text_content': ''}}}
                else:
                    return {'message': {'content': {}}}
            
            # Create the mock client
            mock_ollama.chat = AsyncMock(side_effect=mock_chat)
            
            processor = ImageProcessor()
            processor.model_name = 'test-model'
            logger.debug(f"Created ImageProcessor with model_name={processor.model_name}")
            yield processor
    except Exception as e:
        logger.error(f"Error in image_processor fixture: {str(e)}", exc_info=True)
        raise

@pytest.fixture
def vector_store():
    """Create a temporary vector store for testing."""
    logger.debug("Setting up vector_store fixture")
    try:
        # Create a temporary directory
        temp_dir = tempfile.mkdtemp()
        store = VectorStore(persist_directory=temp_dir)
        logger.debug(f"Created VectorStore at {temp_dir}")
        yield store
        # Cleanup after tests
        shutil.rmtree(temp_dir)
        logger.debug(f"Cleaned up VectorStore at {temp_dir}")
    except Exception as e:
        logger.error(f"Error in vector_store fixture: {str(e)}", exc_info=True)
        raise

def test_image_description_model():
    """Test ImageDescription Pydantic model."""
    description = "A test description"
    model = ImageDescription(description=description)
    assert model.description == description

def test_image_tags_model():
    """Test ImageTags Pydantic model."""
    tags = ["tag1", "tag2", "tag3"]
    model = ImageTags(tags=tags)
    assert model.tags == tags

def test_image_text_model():
    """Test ImageText Pydantic model."""
    model = ImageText(has_text=True, text_content="Some text")
    assert model.has_text == True
    assert model.text_content == "Some text"

    model = ImageText(has_text=False, text_content="")
    assert model.has_text == False
    assert model.text_content == ""

def test_vector_store_add_entry(vector_store):
    """Test adding an entry to the vector store."""
    logger.debug("Testing vector store add entry")
    try:
        # Test data
        image_path = "test_image.png"
        metadata = {
            "description": "A test image",
            "tags": ["test", "image"],
            "text_content": "Some text in the image",
            "is_processed": True
        }
        
        # Add entry
        vector_store.add_or_update_image(image_path, metadata)
        logger.debug(f"Added entry for {image_path}")
        
        # Verify entry was added
        results = vector_store.search_images("test image")
        assert len(results) > 0
        stored_metadata = vector_store.get_metadata(image_path)
        assert stored_metadata["description"] == "A test image"
        assert "test" in stored_metadata["tags"]
        assert "image" in stored_metadata["tags"]
    except Exception as e:
        logger.error(f"Error in test_vector_store_add_entry: {str(e)}", exc_info=True)
        raise

def test_vector_store_update_entry(vector_store):
    """Test updating an existing entry in the vector store."""
    logger.debug("Testing vector store update entry")
    try:
        # Initial data
        image_path = "test_image.png"
        initial_metadata = {
            "description": "Initial description",
            "tags": ["initial"],
            "text_content": "Initial text",
            "is_processed": True
        }
        
        # Add initial entry
        vector_store.add_or_update_image(image_path, initial_metadata)
        logger.debug(f"Added initial entry for {image_path}")
        
        # Update metadata
        updated_metadata = {
            "description": "Updated description",
            "tags": ["updated"],
            "text_content": "Updated text",
            "is_processed": True
        }
        vector_store.add_or_update_image(image_path, updated_metadata)
        logger.debug(f"Updated entry for {image_path}")
        
        # Verify update
        stored_metadata = vector_store.get_metadata(image_path)
        assert stored_metadata["description"] == "Updated description"
        assert "updated" in stored_metadata["tags"]
        assert len(stored_metadata["tags"]) == 1
    except Exception as e:
        logger.error(f"Error in test_vector_store_update_entry: {str(e)}", exc_info=True)
        raise

def test_vector_store_search(vector_store):
    """Test searching entries in the vector store."""
    logger.debug("Testing vector store search")
    try:
        # Add multiple entries
        entries = [
            ("image1.png", {"description": "A cat playing with yarn", "tags": ["cat", "pet"], "text_content": "", "is_processed": True}),
            ("image2.png", {"description": "A dog in the park", "tags": ["dog", "pet"], "text_content": "", "is_processed": True}),
            ("image3.png", {"description": "A sunset over mountains", "tags": ["nature", "sunset"], "text_content": "", "is_processed": True})
        ]
        
        for path, metadata in entries:
            vector_store.add_or_update_image(path, metadata)
            logger.debug(f"Added entry for {path}")
        
        # Test search functionality
        results = vector_store.collection.query(
            query_texts=["dog"],
            n_results=3,
            include=['documents', 'metadatas', 'distances']
        )
        
        # Check if dog image is in raw results
        assert "image2.png" in results['ids'][0]
    except Exception as e:
        logger.error(f"Error in test_vector_store_search: {str(e)}", exc_info=True)
        raise

@pytest.mark.asyncio
async def test_image_processor_initialization():
    """Test ImageProcessor initialization."""
    processor = ImageProcessor(model_name='test-model')
    assert processor.model_name == 'test-model'
    assert processor.stop_check is None

@pytest.mark.asyncio
async def test_get_text_content(image_processor, tmp_path):
    """Test getting text content from an image."""
    logger.debug(f"Creating test image at {tmp_path}")
    # Create a test image
    test_image = tmp_path / "test.png"
    try:
        # Create a valid PNG image
        from PIL import Image
        img = Image.new('RGB', (100, 100), color='white')
        img.save(test_image)
        logger.debug(f"Created test image at {test_image}")
        
        result = await image_processor._get_text_content(str(test_image))
        logger.debug(f"Got result: {result}")
        assert isinstance(result, ImageText)
        assert result.has_text is False
        assert result.text_content == ''
    except Exception as e:
        logger.error(f"Error in test_get_text_content: {str(e)}", exc_info=True)
        raise

@pytest.mark.asyncio
async def test_get_description(image_processor, tmp_path):
    """Test getting description from an image."""
    logger.debug(f"Creating test image at {tmp_path}")
    test_image = tmp_path / "test.png"
    try:
        # Create a valid PNG image
        from PIL import Image
        img = Image.new('RGB', (100, 100), color='white')
        img.save(test_image)
        logger.debug(f"Created test image at {test_image}")
        
        result = await image_processor._get_description(str(test_image))
        logger.debug(f"Got result: {result}")
        assert isinstance(result, ImageDescription)
        assert result.description == 'A test description'
    except Exception as e:
        logger.error(f"Error in test_get_description: {str(e)}", exc_info=True)
        raise

@pytest.mark.asyncio
async def test_get_tags(image_processor, tmp_path):
    """Test getting tags from an image."""
    logger.debug(f"Creating test image at {tmp_path}")
    test_image = tmp_path / "test.png"
    try:
        # Create a valid PNG image
        from PIL import Image
        img = Image.new('RGB', (100, 100), color='white')
        img.save(test_image)
        logger.debug(f"Created test image at {test_image}")
        
        result = await image_processor._get_tags(str(test_image))
        logger.debug(f"Got result: {result}")
        assert isinstance(result, ImageTags)
        assert result.tags == ['test', 'image']
    except Exception as e:
        logger.error(f"Error in test_get_tags: {str(e)}", exc_info=True)
        raise

@pytest.mark.asyncio
async def test_process_image_full(image_processor, tmp_path):
    """Test full image processing."""
    logger.debug(f"Creating test image at {tmp_path}")
    test_image = tmp_path / "test.png"
    try:
        # Create a valid PNG image
        from PIL import Image
        img = Image.new('RGB', (100, 100), color='white')
        img.save(test_image)
        logger.debug(f"Created test image at {test_image}")
        
        result = await image_processor.process_image(test_image)
        logger.debug(f"Got result: {result}")
        assert isinstance(result, dict)
        assert result['description'] == 'A test description'
        assert result['tags'] == ['test', 'image']
        assert result['text_content'] == ''
        assert result['is_processed'] is True
    except Exception as e:
        logger.error(f"Error in test_process_image_full: {str(e)}", exc_info=True)
        raise

@pytest.mark.asyncio
async def test_process_image_no_text(image_processor, tmp_path):
    """Test image processing with no text content."""
    logger.debug(f"Creating test image at {tmp_path}")
    test_image = tmp_path / "test.png"
    try:
        # Create a valid PNG image
        from PIL import Image
        img = Image.new('RGB', (100, 100), color='white')
        img.save(test_image)
        logger.debug(f"Created test image at {test_image}")
        
        result = await image_processor.process_image(test_image)
        logger.debug(f"Got result: {result}")
        assert isinstance(result, dict)
        assert result['text_content'] == ''
    except Exception as e:
        logger.error(f"Error in test_process_image_no_text: {str(e)}", exc_info=True)
        raise 