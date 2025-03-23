import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from pathlib import Path
import json
import logging
import tempfile
import shutil
import os
import traceback

from backend.app.services.image_processor import ImageProcessor
from backend.app.models.schemas import ImageDescription, ImageTags, ImageText
from backend.app.services.vector_store import VectorStore
from .test_image_processor_progress import AsyncResponseGenerator

# Set up logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)

@pytest.fixture
def image_processor():
    """Create an ImageProcessor instance for testing."""
    logger.debug("Setting up image_processor fixture")
    try:
        with patch('backend.app.services.image_processor.ollama.AsyncClient') as mock_client_class:
            logger.debug("Mocking Ollama client")
            
            # Create the mock client first
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            
            # Setup mock responses for different query types
            async def mock_chat(**kwargs):
                format_props = kwargs.get('format', {}).get('properties', {})
                
                if 'description' in format_props:
                    response = {'message': {'content': {'description': 'A test description'}}}
                elif 'tags' in format_props:
                    response = {'message': {'content': {'tags': ['test', 'image']}}}
                elif 'has_text' in format_props:
                    response = {'message': {'content': {'has_text': False, 'text_content': ''}}}
                else:
                    response = {'message': {'content': {}}}
                
                return AsyncResponseGenerator([response])
            
            # Attach the mock chat method
            mock_client.chat = mock_chat
            
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

@pytest.mark.asyncio
async def test_vector_store_add_entry(vector_store):
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
        await vector_store.add_or_update_image(image_path, metadata)
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

@pytest.mark.asyncio
async def test_vector_store_update_entry(vector_store):
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
        await vector_store.add_or_update_image(image_path, initial_metadata)
        logger.debug(f"Added initial entry for {image_path}")
        
        # Update metadata
        updated_metadata = {
            "description": "Updated description",
            "tags": ["updated"],
            "text_content": "Updated text",
            "is_processed": True
        }
        await vector_store.add_or_update_image(image_path, updated_metadata)
        logger.debug(f"Updated entry for {image_path}")
        
        # Verify update
        stored_metadata = vector_store.get_metadata(image_path)
        assert stored_metadata["description"] == "Updated description"
        assert "updated" in stored_metadata["tags"]
        assert len(stored_metadata["tags"]) == 1
    except Exception as e:
        logger.error(f"Error in test_vector_store_update_entry: {str(e)}", exc_info=True)
        raise

@pytest.mark.asyncio
async def test_vector_store_search(vector_store):
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
            await vector_store.add_or_update_image(path, metadata)
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

        # Collect all updates from the generator
        updates = []
        async for update in image_processor._get_text_content(str(test_image)):
            updates.append(update)
        
        # Get the final content from the last update
        result = next(update['content'] for update in reversed(updates) if 'content' in update)
        
        assert isinstance(result, ImageText)
        assert hasattr(result, 'has_text')
        assert hasattr(result, 'text_content')
        assert isinstance(result.has_text, bool)
        assert isinstance(result.text_content, str)
        logger.debug(f"Test successful with result: {result}")
    except Exception as e:
        logger.error(f"Error in test_get_text_content: {str(e)}")
        logger.error(f"Exception type: {type(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
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

        # Collect all updates from the generator
        updates = []
        async for update in image_processor._get_description(str(test_image)):
            updates.append(update)
        
        # Get the final content from the last update
        result = next(update['content'] for update in reversed(updates) if 'content' in update)

        assert isinstance(result, ImageDescription)
        assert hasattr(result, 'description')
        assert isinstance(result.description, str)
        assert len(result.description) > 0
        logger.debug(f"Test successful with result: {result}")
    except Exception as e:
        logger.error(f"Error in test_get_description: {str(e)}")
        logger.error(f"Exception type: {type(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
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

        # Collect all updates from the generator
        updates = []
        async for update in image_processor._get_tags(str(test_image)):
            updates.append(update)
        
        # Get the final content from the last update
        result = next(update['content'] for update in reversed(updates) if 'content' in update)

        assert isinstance(result, ImageTags)
        assert hasattr(result, 'tags')
        assert isinstance(result.tags, list)
        assert len(result.tags) > 0
        assert all(isinstance(tag, str) for tag in result.tags)
        logger.debug(f"Test successful with result: {result}")
    except Exception as e:
        logger.error(f"Error in test_get_tags: {str(e)}")
        logger.error(f"Exception type: {type(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
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

        # Collect all updates from the generator
        updates = []
        async for update in image_processor.process_image(test_image):
            updates.append(update)
        
        # Get the final metadata from the last update
        final_update = updates[-1]
        assert 'progress' in final_update
        assert final_update['progress'] == 1.0
        assert 'image' in final_update
        
        metadata = final_update['image']
        assert isinstance(metadata, dict)
        assert 'description' in metadata
        assert 'tags' in metadata
        assert 'text_content' in metadata
        assert 'is_processed' in metadata
        assert metadata['is_processed'] is True
        logger.debug(f"Test successful with metadata: {metadata}")
    except Exception as e:
        logger.error(f"Error in test_process_image_full: {str(e)}")
        logger.error(f"Exception type: {type(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
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

        # Collect all updates from the generator
        updates = []
        async for update in image_processor.process_image(test_image):
            updates.append(update)
        
        # Get the final metadata from the last update
        final_update = updates[-1]
        assert 'progress' in final_update
        assert final_update['progress'] == 1.0
        assert 'image' in final_update
        
        metadata = final_update['image']
        assert isinstance(metadata, dict)
        assert 'description' in metadata
        assert 'tags' in metadata
        assert 'text_content' in metadata
        assert 'is_processed' in metadata
        assert metadata['is_processed'] is True
        assert metadata['text_content'] == ""  # No text content expected
        logger.debug(f"Test successful with metadata: {metadata}")
    except Exception as e:
        logger.error(f"Error in test_process_image_no_text: {str(e)}")
        logger.error(f"Exception type: {type(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise

@pytest.mark.asyncio
async def test_vector_store_sync_and_consistency(vector_store):
    """Test vector store synchronization and state consistency.
    
    This test verifies:
    1. Metadata synchronization between JSON and vector store
    2. Consistency of stored data across operations
    3. Proper cleanup of removed entries
    4. Search functionality after sync
    """
    logger.debug("Testing vector store sync and consistency")
    try:
        # Initial metadata state
        metadata = {
            "image1.jpg": {
                "description": "A sunny beach",
                "tags": ["beach", "sunny", "vacation"],
                "text_content": "Beach text",
                "is_processed": True
            },
            "image2.jpg": {
                "description": "A mountain peak",
                "tags": ["mountain", "nature", "peak"],
                "text_content": "Mountain text",
                "is_processed": True
            }
        }
        
        # Test initial sync
        logger.debug("Testing initial sync")
        await vector_store.sync_with_metadata(Path("test_folder"), metadata)
        
        # Verify all entries were added
        for image_path, expected_meta in metadata.items():
            stored_meta = vector_store.get_metadata(image_path)
            assert stored_meta is not None, f"Missing metadata for {image_path}"
            assert stored_meta["description"] == expected_meta["description"]
            assert stored_meta["tags"] == expected_meta["tags"]
            assert stored_meta["text_content"] == expected_meta["text_content"]
        
        # Test search functionality after sync
        beach_results = vector_store.search_images("beach sunny")
        assert "image1.jpg" in beach_results
        mountain_results = vector_store.search_images("mountain nature")
        assert "image2.jpg" in mountain_results
        
        # Test metadata updates
        logger.debug("Testing metadata updates")
        metadata["image1.jpg"]["description"] = "A cloudy beach"
        metadata["image1.jpg"]["tags"] = ["beach", "cloudy", "vacation"]
        await vector_store.sync_with_metadata(Path("test_folder"), metadata)
        
        # Verify updates were applied
        updated_meta = vector_store.get_metadata("image1.jpg")
        assert updated_meta["description"] == "A cloudy beach"
        assert "cloudy" in updated_meta["tags"]
        
        # Test deletion handling
        logger.debug("Testing deletion handling")
        del metadata["image2.jpg"]
        await vector_store.sync_with_metadata(Path("test_folder"), metadata)
        
        # Verify deleted entry is removed
        assert vector_store.get_metadata("image2.jpg") is None
        mountain_results = vector_store.search_images("mountain")
        assert "image2.jpg" not in mountain_results
        
        # Verify remaining entry is still intact
        beach_meta = vector_store.get_metadata("image1.jpg")
        assert beach_meta is not None
        assert beach_meta["description"] == "A cloudy beach"
        
        logger.info("Vector store sync and consistency test completed successfully")
        
    except Exception as e:
        logger.error(f"Error in test_vector_store_sync_and_consistency: {str(e)}")
        logger.error(f"Error type: {type(e)}")
        logger.error(f"Full traceback: {traceback.format_exc()}")
        raise

@pytest.mark.asyncio
async def test_vector_store_error_handling(vector_store):
    """Test vector store error handling.
    
    This test verifies:
    1. Handling of invalid metadata
    2. Handling of missing files
    3. Handling of invalid search queries
    4. Error logging
    """
    logger.debug("Testing vector store error handling")
    try:
        # Test handling of invalid metadata
        logger.debug("Testing invalid metadata handling")
        invalid_metadata = {
            "description": "",  # Empty string instead of None
            "tags": [],  # Empty list instead of string
            "text_content": "",  # Empty string instead of int
            "is_processed": False  # Boolean instead of string
        }
        
        # Should handle minimal metadata gracefully
        await vector_store.add_or_update_image("minimal.jpg", invalid_metadata)
        stored_meta = vector_store.get_metadata("minimal.jpg")
        assert stored_meta is not None
        assert isinstance(stored_meta["description"], str)
        assert isinstance(stored_meta["tags"], list)
        assert isinstance(stored_meta["text_content"], str)
        assert isinstance(stored_meta["is_processed"], bool)
        
        # Test handling of missing files
        logger.debug("Testing missing file handling")
        nonexistent_meta = vector_store.get_metadata("nonexistent.jpg")
        assert nonexistent_meta is None
        
        # Test handling of invalid search queries
        logger.debug("Testing invalid search query handling")
        empty_query_results = vector_store.search_images("")
        assert isinstance(empty_query_results, list)
        assert len(empty_query_results) == 0
        
        # Test handling of very long queries
        long_query = "a" * 1000
        long_query_results = vector_store.search_images(long_query)
        assert isinstance(long_query_results, list)
        
        # Test handling of special characters
        special_chars_query = "!@#$%^&*()"
        special_chars_results = vector_store.search_images(special_chars_query)
        assert isinstance(special_chars_results, list)
        
        logger.info("Vector store error handling test completed successfully")
        
    except Exception as e:
        logger.error(f"Error in test_vector_store_error_handling: {str(e)}")
        logger.error(f"Error type: {type(e)}")
        logger.error(f"Full traceback: {traceback.format_exc()}")
        raise 
