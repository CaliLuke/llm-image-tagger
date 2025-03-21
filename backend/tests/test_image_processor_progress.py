import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from pathlib import Path
import json
import logging
from PIL import Image
import tempfile
import asyncio
import traceback

from backend.app.services.image_processor import ImageProcessor
from backend.app.models.schemas import ImageDescription, ImageTags, ImageText

# Set up logging
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

class AsyncResponseGenerator:
    """A class to simulate async iteration for streaming responses."""
    def __init__(self, response_data):
        self.response_data = response_data
        self._index = 0
        logger.debug(f"Initialized AsyncResponseGenerator with {len(response_data)} items")

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self._index >= len(self.response_data):
            logger.debug("AsyncResponseGenerator iteration complete")
            raise StopAsyncIteration
        item = self.response_data[self._index]
        self._index += 1
        logger.debug(f"Yielding item {self._index}/{len(self.response_data)}: {item}")
        return item

@pytest.fixture
def image_processor():
    """Create an ImageProcessor instance with mocked Ollama."""
    logger.info("Setting up image_processor fixture")
    try:
        with patch('backend.app.services.image_processor.ollama.AsyncClient') as mock_client_class:
            # Create a mock client instance
            mock_client = AsyncMock()
            logger.debug("Created mock Ollama client")
            
            # Create mock responses that simulate streaming
            description_response = [
                {'eval_count': 5, 'prompt_eval_count': 10},
                {'message': {'content': {'description': 'Test description'}}}
            ]
            
            tags_response = [
                {'eval_count': 5, 'prompt_eval_count': 10},
                {'message': {'content': {'tags': ['test', 'image', 'white']}}}
            ]
            
            text_response = [
                {'eval_count': 5, 'prompt_eval_count': 10},
                {'message': {'content': {'has_text': False, 'text_content': ''}}}
            ]
            
            logger.debug("Created mock responses for description, tags, and text")
            
            # Set up the mock client's chat method to return different responses based on the prompt
            async def mock_chat(*args, **kwargs):
                prompt = kwargs.get('messages', [{}])[0].get('content', '')
                logger.debug(f"Mock chat called with prompt: {prompt}")
                
                if 'visible text' in prompt:
                    logger.debug("Returning text response")
                    return AsyncResponseGenerator(text_response)
                elif 'tags' in prompt:
                    logger.debug("Returning tags response")
                    return AsyncResponseGenerator(tags_response)
                else:
                    logger.debug("Returning description response")
                    return AsyncResponseGenerator(description_response)
            
            mock_client.chat.side_effect = mock_chat
            logger.debug("Configured mock chat method")
            
            # Make the mock class return our mock client instance
            mock_client_class.return_value = mock_client
            
            processor = ImageProcessor()
            processor.model_name = 'test-model'
            logger.info(f"Created ImageProcessor with model {processor.model_name}")
            yield processor
            
    except Exception as e:
        logger.error(f"Error in image_processor fixture: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise

@pytest.mark.asyncio
async def test_query_ollama_progress_tracking(image_processor, tmp_path):
    """Test that _query_ollama correctly tracks and logs progress."""
    logger.info("Starting test_query_ollama_progress_tracking")
    try:
        # Create a test image
        test_image = tmp_path / "test.png"
        img = Image.new('RGB', (100, 100), color='white')
        img.save(test_image)
        logger.debug(f"Created test image at {test_image}")

        # Mock format schema
        format_schema = {
            'properties': {
                'description': {
                    'type': 'string'
                }
            }
        }
        logger.debug(f"Using format schema: {format_schema}")

        # Collect progress updates
        updates = []
        logger.debug("Starting to collect updates from _query_ollama")
        async for update in image_processor._query_ollama(
            "Test prompt",
            str(test_image),
            format_schema
        ):
            logger.debug(f"Received update: {update}")
            updates.append(update)

        # Verify progress updates
        logger.debug(f"Collected {len(updates)} updates")
        assert len(updates) == 2
        assert updates[0] == {'progress': 0.3333333333333333}
        assert updates[1] == {'content': {'description': 'Test description'}}
        logger.info("Progress tracking test completed successfully")
        
    except Exception as e:
        logger.error(f"Error in test_query_ollama_progress_tracking: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise

@pytest.mark.asyncio
async def test_process_image_progress_updates(image_processor, tmp_path):
    """Test that process_image yields progress updates for each step."""
    logger.info("Starting test_process_image_progress_updates")
    try:
        # Create a test image
        test_image = tmp_path / "test.png"
        img = Image.new('RGB', (100, 100), color='white')
        img.save(test_image)
        logger.debug(f"Created test image at {test_image}")

        # Collect all updates
        updates = []
        logger.debug("Starting to collect updates from process_image")
        async for update in image_processor.process_image(test_image):
            logger.debug(f"Received update: {update}")
            updates.append(update)

        # Verify progress updates
        logger.debug(f"Collected {len(updates)} updates")
        final_update = updates[-1]
        assert 'image' in final_update
        assert 'progress' in final_update
        assert final_update['progress'] == 1.0
        assert final_update['image']['description'] == 'Test description'
        assert final_update['image']['tags'] == ['test', 'image', 'white']
        assert final_update['image']['text_content'] == ''
        assert final_update['image']['is_processed'] is True
        logger.info("Process image progress test completed successfully")
        
    except Exception as e:
        logger.error(f"Error in test_process_image_progress_updates: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise

@pytest.mark.asyncio
async def test_process_image_error_handling(image_processor, tmp_path):
    """Test that process_image handles errors gracefully."""
    logger.info("Starting test_process_image_error_handling")
    try:
        # Create a test image that doesn't exist
        test_image = tmp_path / "nonexistent.png"
        logger.debug(f"Testing with non-existent image at {test_image}")

        # Verify it raises FileNotFoundError
        with pytest.raises(FileNotFoundError) as exc_info:
            async for _ in image_processor.process_image(test_image):
                pass
        logger.debug(f"Caught expected FileNotFoundError: {str(exc_info.value)}")
        logger.info("Error handling test completed successfully")
        
    except Exception as e:
        logger.error(f"Error in test_process_image_error_handling: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise

@pytest.mark.asyncio
async def test_ollama_streaming_error(image_processor, tmp_path):
    """Test handling of Ollama streaming errors."""
    logger.info("Starting test_ollama_streaming_error")
    try:
        # Create a test image
        test_image = tmp_path / "test.png"
        img = Image.new('RGB', (100, 100), color='white')
        img.save(test_image)
        logger.debug(f"Created test image at {test_image}")

        # Mock Ollama to raise an error
        with patch('backend.app.services.image_processor.ollama.AsyncClient') as mock_client_class:
            logger.debug("Setting up mock client to raise error")
            # Create a mock client instance that raises an error
            mock_client = AsyncMock()
            mock_client.chat.side_effect = Exception("Streaming error")
            mock_client_class.return_value = mock_client
            
            # Verify it raises the error
            with pytest.raises(Exception) as exc_info:
                async for _ in image_processor._query_ollama(
                    "Test prompt",
                    str(test_image),
                    {'properties': {'description': {'type': 'string'}}}
                ):
                    pass
            
            assert str(exc_info.value) == "Streaming error"
            logger.debug(f"Caught expected streaming error: {str(exc_info.value)}")
            logger.info("Streaming error test completed successfully")
            
    except Exception as e:
        logger.error(f"Error in test_ollama_streaming_error: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise 
